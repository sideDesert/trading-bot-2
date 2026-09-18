import argparse
import json
import os
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping

from .advisory import (
    ADVICE_SCHEMA,
    PROMPT_SHA256,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    TOLERATED_SHADOW_BLOCKERS,
    Advice,
    AdviceValidationError,
    SnapshotBuilder,
    SnapshotError,
    _aware,
    _fallback_advice,
    _parse_json_value,
    apply_engine_demotions,
    validate_advice,
)
from .collector import CollectorConfig, MarketDataCollector
from .config import load_env_file
from .features import IST
from .storage import DuckDBStore, ModelAdviceRow
from .upstox.client import UpstoxClient

REQUEST_MAX_AGE_SECONDS = 90
MAX_ATTEMPTS = 2
DEFAULT_REQUEST_DIR = Path("data/agent-requests")
SOURCE = "shadow-harness"
DEFAULT_AGENT_NAME = "harness-current-session"
MAX_RAW_ADVICE_BYTES = 20000
MAX_AGENT_NAME_LENGTH = 100
BOUNDARY = "SHADOW ONLY - DO NOT EXECUTE"


class AgentToolError(Exception):
    pass


@dataclass(frozen=True)
class AgentToolResult:
    status: str
    request_id: "str | None"
    advice_id: "str | None"
    advice: "Advice | None"
    reason: "str | None"
    request: "Mapping | None" = None
    now_ist: "str | None" = None


def _write_json_atomic(dir_path: Path, name: str, payload) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dir_path, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        target = dir_path / name
        os.replace(tmp, target)
        return target
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _strict_json(text):
    return json.loads(
        text,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(value)
        ),
    )


class AgentToolService:
    def __init__(
        self, store, request_dir=DEFAULT_REQUEST_DIR, now=None
    ) -> None:
        self._store = store
        self._dir = Path(request_dir)
        self._now = now or (lambda: datetime.now(IST))

    def _now_ist(self) -> datetime:
        value = self._now()
        if value.tzinfo is None:
            return value.replace(tzinfo=IST)
        return value.astimezone(IST)

    def prepare_latest(self) -> AgentToolResult:
        now = self._now_ist()
        now_ist = now.isoformat()
        current = self._store.latest_market_data()
        if current is None:
            return AgentToolResult(
                "SKIPPED", None, None, None, "NO_MARKET_DATA", now_ist=now_ist
            )
        candidate = _parse_json_value(current.get("shadow_candidate"))
        if not isinstance(candidate, dict):
            return AgentToolResult(
                "SKIPPED", None, None, None, "NO_SHADOW_CANDIDATE",
                now_ist=now_ist,
            )
        blockers = _parse_json_value(current.get("gate_reasons"))
        if not isinstance(blockers, (list, tuple)) or any(
            not isinstance(item, str) or not item.strip()
            for item in blockers
        ):
            return AgentToolResult(
                "NO_TRADE",
                None,
                None,
                None,
                "ENGINE_BLOCK:GATE_STATE_INVALID",
                now_ist=now_ist,
            )
        hard = set(blockers) - TOLERATED_SHADOW_BLOCKERS
        if current.get("data_is_stale"):
            hard.add("STALE_DATA")
        hard = sorted(hard)
        if hard:
            return AgentToolResult(
                "NO_TRADE",
                None,
                None,
                None,
                "ENGINE_BLOCK:" + ",".join(hard),
                now_ist=now_ist,
            )
        if self._store.model_advice_exists(current["time"], PROMPT_SHA256):
            return AgentToolResult(
                "SKIPPED", None, None, None, "ALREADY_ADVISED",
                now_ist=now_ist,
            )
        recent = self._store.recent_market_data(limit=15, through=current["time"])
        try:
            snapshot = SnapshotBuilder().build(current, recent, now)
        except SnapshotError as error:
            return AgentToolResult(
                "SKIPPED", None, None, None, f"SNAPSHOT:{error}",
                now_ist=now_ist,
            )
        request_id = str(uuid.uuid4())
        created_at = now
        expires_at = created_at + timedelta(seconds=REQUEST_MAX_AGE_SECONDS)
        exact_input = json.dumps(
            {"system_prompt": SYSTEM_PROMPT, "snapshot": snapshot},
            separators=(",", ":"),
            sort_keys=True,
        )
        times = [
            stamp
            for stamp in (_aware(row.get("time")) for row in recent)
            if stamp is not None
        ]
        context_to = _aware(current["time"])
        context_from = min(times) if times else context_to
        artifact = {
            "request_id": request_id,
            "status": "PENDING",
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "prompt_version": PROMPT_VERSION,
            "prompt_hash": PROMPT_SHA256,
            "system_prompt": SYSTEM_PROMPT,
            "output_schema": ADVICE_SCHEMA,
            "snapshot": snapshot,
            "context_from": context_from.isoformat(),
            "context_to": context_to.isoformat(),
            "exact_model_input": exact_input,
            "attempts": [],
        }
        _write_json_atomic(self._dir, f"{request_id}.json", artifact)
        return AgentToolResult(
            "READY", request_id, None, None, None, request=artifact,
            now_ist=now_ist,
        )

    def _load_request(self, request_id) -> "tuple[Path, Mapping]":
        try:
            parsed = uuid.UUID(str(request_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise AgentToolError("request_id must be a canonical UUID") from exc
        if str(parsed) != str(request_id):
            raise AgentToolError("request_id must be a canonical UUID")
        path = self._dir / f"{parsed}.json"
        if path.resolve().parent != self._dir.resolve():
            raise AgentToolError("request_id must be a canonical UUID")
        if not path.is_file():
            raise AgentToolError(f"unknown request_id: {request_id}")
        try:
            artifact = _strict_json(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise AgentToolError("request artifact is not valid JSON") from exc
        if not isinstance(artifact, dict) or artifact.get(
            "request_id"
        ) != str(parsed):
            raise AgentToolError("request artifact does not match request_id")
        return path, artifact

    def submit(
        self, request_id: str, raw_advice: str, agent_name=DEFAULT_AGENT_NAME
    ) -> AgentToolResult:
        path, artifact = self._load_request(request_id)
        if artifact.get("status") == "SUBMITTED":
            final = artifact.get("final_advice")
            advice = Advice(**final) if isinstance(final, dict) else None
            return AgentToolResult(
                "SKIPPED",
                request_id,
                artifact.get("advice_id"),
                advice,
                "ALREADY_SUBMITTED",
            )
        if artifact.get("status") != "PENDING":
            raise AgentToolError("request artifact is not pending")
        if artifact.get("prompt_hash") != PROMPT_SHA256 or artifact.get(
            "prompt_version"
        ) != PROMPT_VERSION:
            raise AgentToolError("PROMPT_CHANGED")
        existing = self._store.get_model_advice_for_context(
            datetime.fromisoformat(artifact["context_to"]), PROMPT_SHA256
        )
        if existing is not None:
            return self._recover_existing(artifact, request_id, existing)
        if (
            not isinstance(raw_advice, str)
            or not raw_advice.strip()
            or len(raw_advice.encode("utf-8")) > MAX_RAW_ADVICE_BYTES
        ):
            raise AgentToolError(
                "raw_advice must be a non-empty string <= 20000 bytes"
            )
        if (
            not isinstance(agent_name, str)
            or not agent_name.strip()
            or len(agent_name) > MAX_AGENT_NAME_LENGTH
        ):
            raise AgentToolError(
                "agent_name must be a non-empty string <= 100 characters"
            )
        now = self._now_ist()
        expires_at = datetime.fromisoformat(artifact["expires_at"])
        expired = now > expires_at
        attempts = list(artifact.get("attempts") or [])
        advice = None
        validation_code = None
        try:
            advice = validate_advice(raw_advice, artifact["snapshot"])
            attempts.append(
                {
                    "raw": raw_advice,
                    "error": None,
                    "hallucination_event": False,
                    "submitted_at": now.isoformat(),
                }
            )
        except AdviceValidationError as error:
            validation_code = error.code
            attempts.append(
                {
                    "raw": raw_advice,
                    "error": error.code,
                    "hallucination_event": error.hallucination_event,
                    "submitted_at": now.isoformat(),
                }
            )
        if validation_code is not None and len(attempts) < MAX_ATTEMPTS and not expired:
            artifact = {**artifact, "attempts": attempts}
            _write_json_atomic(self._dir, f"{request_id}.json", artifact)
            return AgentToolResult(
                "RETRY", request_id, None, None, validation_code
            )

        if expired:
            final_advice = _fallback_advice()
            fallback_reason = "HARNESS_RESPONSE_STALE"
            status = "FALLBACK"
        elif validation_code is not None:
            final_advice = _fallback_advice()
            fallback_reason = f"HARNESS_VALIDATION:{validation_code}"
            status = "FALLBACK"
        else:
            final_advice, demotion = apply_engine_demotions(advice)
            fallback_reason = demotion
            status = "ADVISED" if demotion is None else "FALLBACK"

        candidate = artifact["snapshot"].get("candidate") or {}
        created_at = datetime.fromisoformat(artifact["created_at"])
        advice_id = str(uuid.uuid4())
        row = ModelAdviceRow(
            advice_id=advice_id,
            advice_at=now,
            context_from=datetime.fromisoformat(artifact["context_from"]),
            context_to=datetime.fromisoformat(artifact["context_to"]),
            prompt_version=PROMPT_VERSION,
            model_name=agent_name,
            action=final_advice.action,
            confidence=final_advice.confidence,
            setup_quality=final_advice.setup_quality,
            entry_price=final_advice.entry_price,
            stop_price=final_advice.stop_price,
            target_price=final_advice.target_price,
            idea_fails_if=final_advice.idea_fails_if,
            data_conflict=final_advice.data_conflict,
            reason=final_advice.reason,
            exact_model_input=artifact["exact_model_input"],
            exact_model_output=raw_advice,
            exact_model_output_raw=raw_advice,
            source=SOURCE,
            instrument_key=candidate.get("instrument_key"),
            strike=candidate.get("strike"),
            prompt_hash=PROMPT_SHA256,
            latency_ms=max(
                0.0, (now - created_at).total_seconds() * 1000.0
            ),
            fallback_reason=fallback_reason,
            validation_events=json.dumps(
                [a["error"] for a in attempts if a.get("error")],
                separators=(",", ":"),
            ),
            reask_used=len(attempts) > 1,
            hallucination_event=any(
                a.get("hallucination_event") for a in attempts
            ),
            model_attempts=json.dumps(attempts, separators=(",", ":")),
        )
        try:
            self._store.insert_model_advice(row)
        except Exception as error:
            try:
                import duckdb
            except ImportError:
                raise
            if not isinstance(error, duckdb.ConstraintException):
                raise
            recovered = self._store.get_model_advice_for_context(
                row.context_to, PROMPT_SHA256
            )
            if recovered is None:
                raise
            return self._recover_existing(artifact, request_id, recovered)
        artifact = {
            **artifact,
            "status": "SUBMITTED",
            "submitted_at": now.isoformat(),
            "advice_id": advice_id,
            "final_advice": asdict(final_advice),
            "fallback_reason": fallback_reason,
            "attempts": attempts,
        }
        _write_json_atomic(self._dir, f"{request_id}.json", artifact)
        return AgentToolResult(
            status, request_id, advice_id, final_advice, fallback_reason
        )

    def _recover_existing(
        self, artifact, request_id: str, existing
    ) -> AgentToolResult:
        advice = Advice(
            action=existing["action"],
            confidence=existing["confidence"],
            setup_quality=existing["setup_quality"],
            entry_price=existing["entry_price"],
            stop_price=existing["stop_price"],
            target_price=existing["target_price"],
            idea_fails_if=existing["idea_fails_if"],
            data_conflict=existing["data_conflict"],
            reason=existing["reason"],
        )
        advice_at = existing.get("advice_at")
        artifact = {
            **artifact,
            "status": "SUBMITTED",
            "submitted_at": (
                advice_at.isoformat()
                if isinstance(advice_at, datetime)
                else str(advice_at)
            ),
            "advice_id": existing["advice_id"],
            "final_advice": asdict(advice),
            "fallback_reason": existing.get("fallback_reason"),
        }
        _write_json_atomic(self._dir, f"{request_id}.json", artifact)
        return AgentToolResult(
            "SKIPPED",
            request_id,
            existing["advice_id"],
            advice,
            "ALREADY_SUBMITTED",
        )


def _emit(stream, payload) -> None:
    print(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        file=stream,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot.agent_tool",
        description="Harness-native shadow advice request/submit tool",
    )
    parser.add_argument(
        "--db-path", type=Path, default=Path("data/trading_bot.duckdb")
    )
    parser.add_argument(
        "--request-dir", type=Path, default=DEFAULT_REQUEST_DIR
    )
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--env-file", type=Path, default=Path(".env"))
    submit = sub.add_parser("submit")
    submit.add_argument("--request-id", required=True)
    submit.add_argument("--advice-json", default=None)
    submit.add_argument("--agent-name", default=DEFAULT_AGENT_NAME)
    return parser


def _result_payload(result: AgentToolResult) -> Mapping:
    payload = {
        "ok": True,
        "status": result.status,
        "request_id": result.request_id,
        "advice_id": result.advice_id,
        "advice": (
            asdict(result.advice) if result.advice is not None else None
        ),
        "reason": result.reason,
        "now_ist": result.now_ist,
        "boundary": BOUNDARY,
    }
    if result.status == "READY":
        payload["request"] = result.request
        payload["submit_example"] = (
            ".venv/bin/python -m trading_bot.agent_tool submit "
            f"--request-id {result.request_id} "
            f"--agent-name {DEFAULT_AGENT_NAME} <<'ADVICE_JSON'\n"
            "<advice json object>\nADVICE_JSON"
        )
    return payload


def run(
    argv=None,
    *,
    upstox_client_factory=UpstoxClient.from_env,
    collector_factory=MarketDataCollector,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        with DuckDBStore(args.db_path) as store:
            if args.command == "prepare":
                load_env_file(args.env_file)
                client = upstox_client_factory()
                collector = collector_factory(
                    client, store, CollectorConfig(db_path=args.db_path)
                )
                collector.run_once()
                result = AgentToolService(
                    store, args.request_dir
                ).prepare_latest()
            else:
                raw = (
                    args.advice_json
                    if args.advice_json is not None
                    else sys.stdin.read()
                )
                result = AgentToolService(
                    store, args.request_dir
                ).submit(
                    args.request_id, raw, agent_name=args.agent_name
                )
            _emit(sys.stdout, _result_payload(result))
            return 0
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        _emit(
            sys.stderr,
            {
                "ok": False,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                },
            },
        )
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
