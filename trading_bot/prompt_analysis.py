import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo

from .advisory import PROMPT_SHA256, PROMPT_VERSION, SYSTEM_PROMPT
from .config import load_env_file
from .feedback import build_evaluation_report
from .llm import LLMError, OpenAIResponsesClient
from .risk import CostConfig, calculate_round_trip_cost
from .storage import DuckDBStore

IST = ZoneInfo("Asia/Kolkata")

ANALYSIS_PROMPT_VERSION = "analysis-v1"
MIN_COSTED_RECORDS = 100
MAX_INPUT_BYTES = 200000
MAX_CASES = 200

_PROMPT_PATH = (
    Path(__file__).resolve().parent / "prompts" / "analysis_v1.txt"
)
ANALYSIS_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
ANALYSIS_PROMPT_SHA256 = hashlib.sha256(
    ANALYSIS_PROMPT.encode("utf-8")
).hexdigest()

PROPOSAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "recommendation": {"type": "string", "enum": ["KEEP", "REVISE"]},
        "summary": {"type": "string", "minLength": 1, "maxLength": 500},
        "patterns": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "pattern": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 300,
                    },
                    "evidence_count": {
                        "type": "integer",
                        "minimum": 2,
                    },
                    "evidence_advice_ids": {
                        "type": "array",
                        "minItems": 2,
                        "uniqueItems": True,
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "pattern",
                    "evidence_count",
                    "evidence_advice_ids",
                ],
            },
        },
        "changes": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "section": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 100,
                    },
                    "current_text": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 2000,
                    },
                    "replacement_text": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 2000,
                    },
                    "evidence_advice_ids": {
                        "type": "array",
                        "minItems": 2,
                        "uniqueItems": True,
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "section",
                    "current_text",
                    "replacement_text",
                    "evidence_advice_ids",
                ],
            },
        },
        "risks": {
            "type": "array",
            "maxItems": 10,
            "items": {"type": "string", "minLength": 1, "maxLength": 300},
        },
    },
    "required": ["recommendation", "summary", "patterns", "changes", "risks"],
}


class ProposalValidationError(Exception):
    def __init__(self, code: str, message: "str | None" = None) -> None:
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class ProposalResult:
    status: str
    proposal_id: "str | None"
    artifact_path: "str | None"
    proposal: "Mapping | None"
    fallback_reason: "str | None" = None


def _reject_constant(value):
    raise ValueError(value)


def _strict_loads(raw):
    try:
        parsed = json.loads(raw, parse_constant=_reject_constant)
    except (ValueError, TypeError):
        raise ProposalValidationError("INVALID_JSON", "output is not valid JSON")
    return parsed


def _is_str(value):
    return isinstance(value, str)


def _bounded_str(value, lo, hi):
    return _is_str(value) and lo <= len(value) <= hi


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


_PROHIBITED = re.compile(
    r"\b(guaranteed|guarantee|sure|certain|must\s+rise|must\s+fall"
    r"|execute\s+this\s+trade)\b",
    re.IGNORECASE,
)


def _check_text(value, lo, hi, code="SCHEMA"):
    if not _bounded_str(value, lo, hi):
        raise ProposalValidationError(code)
    if _PROHIBITED.search(value):
        raise ProposalValidationError("PROHIBITED_LANGUAGE")
    return value


def _check_ids(value, valid_ids, min_items=2):
    if (
        not isinstance(value, list)
        or len(value) < min_items
        or len(value) > 10
        or not all(_is_str(item) for item in value)
    ):
        raise ProposalValidationError("SCHEMA")
    if len(set(value)) != len(value):
        raise ProposalValidationError("DUPLICATE_EVIDENCE")
    unknown = [item for item in value if item not in valid_ids]
    if unknown:
        raise ProposalValidationError("UNKNOWN_ADVICE_ID")
    return value


def validate_proposal(
    raw, valid_advice_ids, production_prompt=SYSTEM_PROMPT
) -> Mapping:
    parsed = _strict_loads(raw)
    if not isinstance(parsed, dict):
        raise ProposalValidationError("SCHEMA")
    required = set(PROPOSAL_SCHEMA["required"])
    if set(parsed.keys()) != required:
        raise ProposalValidationError("SCHEMA")
    valid_ids = set(valid_advice_ids)
    recommendation = parsed["recommendation"]
    if recommendation not in ("KEEP", "REVISE"):
        raise ProposalValidationError("SCHEMA")
    _check_text(parsed["summary"], 1, 500)
    patterns = parsed["patterns"]
    changes = parsed["changes"]
    risks = parsed["risks"]
    if not isinstance(patterns, list) or len(patterns) > 10:
        raise ProposalValidationError("SCHEMA")
    if not isinstance(changes, list) or len(changes) > 10:
        raise ProposalValidationError("SCHEMA")
    if not isinstance(risks, list) or len(risks) > 10:
        raise ProposalValidationError("SCHEMA")
    pattern_ids = set()
    for pattern in patterns:
        if not isinstance(pattern, dict) or set(pattern.keys()) != {
            "pattern",
            "evidence_count",
            "evidence_advice_ids",
        }:
            raise ProposalValidationError("SCHEMA")
        _check_text(pattern["pattern"], 1, 300)
        if not _is_int(pattern["evidence_count"]) or pattern["evidence_count"] < 2:
            raise ProposalValidationError("SCHEMA")
        ids = _check_ids(pattern["evidence_advice_ids"], valid_ids)
        if pattern["evidence_count"] != len(set(ids)):
            raise ProposalValidationError("EVIDENCE_COUNT_MISMATCH")
        pattern_ids.update(ids)
    for change in changes:
        if not isinstance(change, dict) or set(change.keys()) != {
            "section",
            "current_text",
            "replacement_text",
            "evidence_advice_ids",
        }:
            raise ProposalValidationError("SCHEMA")
        _check_text(change["section"], 1, 100)
        _check_text(change["current_text"], 1, 2000)
        _check_text(change["replacement_text"], 1, 2000)
        if change["current_text"] not in production_prompt:
            raise ProposalValidationError("CURRENT_TEXT_NOT_FOUND")
        change_ids = _check_ids(change["evidence_advice_ids"], valid_ids)
        if not set(change_ids) <= pattern_ids:
            raise ProposalValidationError("EVIDENCE_NOT_IN_PATTERN")
    for risk in risks:
        _check_text(risk, 1, 300)
    if recommendation == "KEEP" and changes:
        raise ProposalValidationError("KEEP_WITH_CHANGES")
    if recommendation == "REVISE" and (not patterns or not changes):
        raise ProposalValidationError("REVISE_MISSING_CONTENT")
    return parsed


def _round4(value):
    return round(float(value), 4) if value is not None else None


def build_analysis_cases(rows, cost_config: CostConfig = CostConfig()):
    cases = []
    for row in rows:
        fields = (
            row.get("actual_entry_price"),
            row.get("actual_exit_price"),
            row.get("lots"),
            row.get("lot_size"),
            row.get("quoted_spread"),
        )
        if any(value is None for value in fields):
            continue
        entry = float(row["actual_entry_price"])
        exit_price = float(row["actual_exit_price"])
        lots = int(row["lots"])
        lot_size = int(row["lot_size"])
        if entry <= 0 or exit_price <= 0 or lots <= 0 or lot_size <= 0:
            continue
        spread = float(row["quoted_spread"])
        if spread < 0:
            continue
        gross = (exit_price - entry) * lots * lot_size
        cost = calculate_round_trip_cost(
            entry, exit_price, lots, lot_size, spread, config=cost_config
        ).total
        net = gross - cost
        cases.append(
            {
                "advice_id": row["advice_id"],
                "prompt_version": row.get("prompt_version"),
                "action": row.get("action"),
                "confidence": _round4(row.get("confidence")),
                "setup_quality": row.get("setup_quality"),
                "fallback_reason": row.get("fallback_reason"),
                "session_state": row.get("market_session_state"),
                "is_expiry_day": row.get("market_is_expiry_day"),
                "local_gex_sign": row.get("market_local_gex_sign"),
                "vwap_position": row.get("market_vwap_position"),
                "relative_volume": _round4(row.get("market_relative_volume")),
                "evaluation_mode": row.get("evaluation_mode"),
                "result_status": row.get("result_status"),
                "user_verdict": row.get("user_verdict"),
                "user_notes": row.get("user_notes"),
                "entry_price": round(entry, 4),
                "exit_price": round(exit_price, 4),
                "lots": lots,
                "lot_size": lot_size,
                "mae": _round4(row.get("mae")),
                "mfe": _round4(row.get("mfe")),
                "gross_pnl_inr": round(gross, 2),
                "costs_inr": round(cost, 2),
                "net_pnl_inr": round(net, 2),
                "objective_win": net > 0,
            }
        )
    return cases[-MAX_CASES:]


class PromptAnalysisService:
    def __init__(self, store, model_client, now=None) -> None:
        self._store = store
        self._client = model_client
        self._now = now or (lambda: datetime.now(IST))

    def run_once(
        self,
        min_records: int = MIN_COSTED_RECORDS,
        trial_count: int = 1,
        output_dir: Path = Path("data/prompt-proposals"),
        rows=None,
        report=None,
        cases=None,
    ) -> ProposalResult:
        if (
            not isinstance(min_records, int)
            or isinstance(min_records, bool)
            or not 100 <= min_records <= MAX_CASES
        ):
            raise ProposalValidationError(
                "MIN_RECORDS",
                f"min_records must be between 100 and {MAX_CASES}",
            )
        if (
            not isinstance(trial_count, int)
            or isinstance(trial_count, bool)
            or trial_count <= 0
        ):
            raise ProposalValidationError(
                "TRIAL_COUNT", "trial_count must be a positive integer"
            )
        if rows is None:
            rows = self._store.evaluation_rows()
        if report is None:
            report = build_evaluation_report(rows, trial_count=trial_count)
        if cases is None:
            cases = build_analysis_cases(rows)
        if len(cases) < min_records:
            return ProposalResult(
                status="SKIPPED",
                proposal_id=None,
                artifact_path=None,
                proposal=None,
                fallback_reason=f"SAMPLE_BELOW_{min_records}",
            )
        input_payload = {
            "analysis_prompt_version": ANALYSIS_PROMPT_VERSION,
            "production_prompt_version": PROMPT_VERSION,
            "production_prompt_hash": PROMPT_SHA256,
            "production_prompt_text": SYSTEM_PROMPT,
            "evaluation_report": report,
            "cases": cases,
        }
        input_json = json.dumps(
            input_payload, separators=(",", ":"), sort_keys=True
        )
        if len(input_json.encode("utf-8")) > MAX_INPUT_BYTES:
            return ProposalResult(
                status="SKIPPED",
                proposal_id=None,
                artifact_path=None,
                proposal=None,
                fallback_reason="INPUT_TOO_LARGE",
            )
        proposal_id = str(uuid.uuid4())
        valid_ids = {case["advice_id"] for case in cases}
        attempts = []
        raw = None
        proposal = None
        failure_status = None
        for attempt in range(2):
            raw = None
            started = time.monotonic()
            try:
                raw = self._client.generate(
                    ANALYSIS_PROMPT,
                    input_json,
                    PROPOSAL_SCHEMA,
                    repair_error=(
                        attempts[-1]["error"]["code"]
                        if attempt == 1
                        else None
                    ),
                    schema_name="prompt_optimization_proposal",
                )
                latency = (time.monotonic() - started) * 1000.0
                proposal = validate_proposal(raw, valid_ids)
                attempts.append(
                    {"raw": raw, "error": None, "latency_ms": latency}
                )
                break
            except ProposalValidationError as error:
                latency = (time.monotonic() - started) * 1000.0
                attempts.append(
                    {
                        "raw": raw,
                        "error": {
                            "type": type(error).__name__,
                            "code": error.code,
                        },
                        "latency_ms": latency,
                    }
                )
                if attempt == 1:
                    failure_status = "VALIDATION_FAILED"
            except LLMError as error:
                latency = (time.monotonic() - started) * 1000.0
                attempts.append(
                    {
                        "raw": raw,
                        "error": {
                            "type": type(error).__name__,
                            "code": None,
                        },
                        "latency_ms": latency,
                    }
                )
                failure_status = "MODEL_FAILED"
                break
        created_at = self._now()
        created_at = (
            created_at.replace(tzinfo=IST)
            if created_at.tzinfo is None
            else created_at.astimezone(IST)
        )
        artifact = {
            "proposal_id": proposal_id,
            "created_at": created_at.isoformat(),
            "analysis_prompt_version": ANALYSIS_PROMPT_VERSION,
            "production_prompt_version": PROMPT_VERSION,
            "production_prompt_hash": PROMPT_SHA256,
            "model": getattr(self._client, "model", "unknown"),
            "sample_count": len(cases),
            "trial_count": trial_count,
            "status": (
                "PENDING_HUMAN_REVIEW" if proposal is not None else failure_status
            ),
            "evaluation_report": report,
            "raw_attempts": attempts,
            "validated_proposal": proposal,
        }
        artifact_path = self._write_artifact(
            Path(output_dir), proposal_id, artifact
        )
        if proposal is None:
            return ProposalResult(
                status="FAILED",
                proposal_id=proposal_id,
                artifact_path=str(artifact_path),
                proposal=None,
                fallback_reason=failure_status,
            )
        return ProposalResult(
            status="VALIDATED",
            proposal_id=proposal_id,
            artifact_path=str(artifact_path),
            proposal=proposal,
            fallback_reason=None,
        )

    @staticmethod
    def _write_artifact(output_dir: Path, proposal_id: str, artifact) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            dir=str(output_dir), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    artifact,
                    handle,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
            final_path = output_dir / f"{proposal_id}.json"
            os.replace(temp_name, final_path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
        return final_path


def _emit(stream, payload) -> None:
    print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), file=stream)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot.prompt_analysis",
        description="Propose a prompt revision from shadow outcomes",
    )
    parser.add_argument(
        "--db-path", type=Path, default=Path("data/trading_bot.duckdb")
    )
    parser.add_argument("--min-records", type=int, default=MIN_COSTED_RECORDS)
    parser.add_argument("--trial-count", type=int, default=1)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/prompt-proposals")
    )
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    return parser


def run(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if (
        not isinstance(args.min_records, int)
        or not 100 <= args.min_records <= MAX_CASES
    ):
        _emit(
            sys.stderr,
            {
                "ok": False,
                "error": f"min-records must be between 100 and {MAX_CASES}",
            },
        )
        return 2
    if not isinstance(args.trial_count, int) or args.trial_count <= 0:
        _emit(
            sys.stderr,
            {"ok": False, "error": "trial-count must be a positive integer"},
        )
        return 2
    try:
        with DuckDBStore(args.db_path) as store:
            rows = store.evaluation_rows()
            report = build_evaluation_report(
                rows, trial_count=args.trial_count
            )
            cases = build_analysis_cases(rows)
            if len(cases) < args.min_records:
                _emit(
                    sys.stdout,
                    {
                        "ok": True,
                        "status": "SKIPPED",
                        "fallback_reason": f"SAMPLE_BELOW_{args.min_records}",
                    },
                )
                return 0
            load_env_file(
                args.env_file,
                names=("OPENAI_API_KEY", "TRADING_BOT_LLM_MODEL"),
            )
            client = OpenAIResponsesClient.from_env()
            service = PromptAnalysisService(store, client)
            result = service.run_once(
                min_records=args.min_records,
                trial_count=args.trial_count,
                output_dir=args.output_dir,
                rows=rows,
                report=report,
                cases=cases,
            )
            _emit(
                sys.stdout,
                {
                    "ok": True,
                    "status": result.status,
                    "proposal_id": result.proposal_id,
                    "artifact_path": result.artifact_path,
                    "proposal": result.proposal,
                    "fallback_reason": result.fallback_reason,
                },
            )
            return 0
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        _emit(
            sys.stderr,
            {
                "ok": False,
                "error": {"type": type(error).__name__, "message": str(error)},
            },
        )
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
