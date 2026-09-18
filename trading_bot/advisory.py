import argparse
import hashlib
import json
import math
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping, Sequence
from zoneinfo import ZoneInfo

from .config import load_env_file
from .llm import LLMError, OpenAIResponsesClient
from .storage import DuckDBStore, ModelAdviceRow

IST = ZoneInfo("Asia/Kolkata")

PROMPT_VERSION = "v1"
ENGINE_VERSION = "0.2.0"
TOLERATED_SHADOW_BLOCKERS = frozenset(
    {
        "SHADOW_MODE",
        "IVP_HISTORY_INSUFFICIENT",
        "EXPECTED_MFE_UNAVAILABLE",
        "CALIBRATION_HISTORY_INSUFFICIENT",
        "THETA_CLOCK_UNAVAILABLE",
    }
)
MAX_SNAPSHOT_BYTES = 12000
MAX_SNAPSHOT_AGE_MS = 2000.0
MAX_RECENT_ROWS = 15
MAX_CHAIN_ROWS = 9

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "system_v1.txt"
SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
PROMPT_SHA256 = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()

ADVICE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "action": {
            "type": "string",
            "enum": ["LONG_CALL", "LONG_PUT", "NO_TRADE"],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "setup_quality": {"type": "string", "enum": ["A", "B", "C"]},
        "entry_price": {"type": ["number", "null"]},
        "stop_price": {"type": ["number", "null"]},
        "target_price": {"type": ["number", "null"]},
        "idea_fails_if": {"type": "string", "minLength": 1, "maxLength": 200},
        "data_conflict": {"type": "boolean"},
        "reason": {"type": "string", "minLength": 1, "maxLength": 200},
    },
    "required": [
        "action",
        "confidence",
        "setup_quality",
        "entry_price",
        "stop_price",
        "target_price",
        "idea_fails_if",
        "data_conflict",
        "reason",
    ],
}

ADVICE_KEYS = frozenset(ADVICE_SCHEMA["required"])


@dataclass(frozen=True)
class Advice:
    action: str
    confidence: float
    setup_quality: str
    entry_price: "float | None"
    stop_price: "float | None"
    target_price: "float | None"
    idea_fails_if: str
    data_conflict: bool
    reason: str


@dataclass(frozen=True)
class AdviceRunResult:
    status: str
    advice_id: "str | None"
    advice: "Advice | None"
    fallback_reason: "str | None"
    snapshot: "Mapping | None" = None


class SnapshotError(Exception):
    pass


class AdviceValidationError(Exception):
    def __init__(self, code: str, hallucination_event: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.hallucination_event = hallucination_event


def _fallback_advice() -> Advice:
    return Advice(
        "NO_TRADE",
        0.0,
        "C",
        None,
        None,
        None,
        "No trade was authorized.",
        True,
        "Deterministic safety fallback.",
    )


def _parse_json_value(value, default=None):
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return default
    return value


def _aware(value) -> "datetime | None":
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed


def _round4(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, list):
        return [_round4(v) for v in value]
    if isinstance(value, tuple):
        return [_round4(v) for v in value]
    if isinstance(value, dict):
        return {k: _round4(v) for k, v in value.items()}
    return value


def _num(value, digits):
    if value is None or isinstance(value, bool):
        return "null"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "null"
    if number != number or number in (float("inf"), float("-inf")):
        return "null"
    return f"{number:.{digits}f}"


_FEATURE_KEYS = (
    "synthetic_fwd_basis",
    "atm_iv",
    "atm_expected_move",
    "expected_move_consumed_pct",
    "iv_percentile",
    "realized_vol_10d",
    "vrp_ratio",
    "opening_range_high",
    "opening_range_low",
    "opening_range_width",
    "opening_range_is_narrow",
    "opening_range_state",
    "relative_volume",
    "relative_volume_spike",
    "futures_vwap",
    "vwap_position",
    "vwap_sigma",
    "first_30m_return_pct",
    "pcr",
    "call_oi_walls",
    "put_oi_walls",
    "local_gex_sign",
    "momentum_reversion_selector",
    "spread",
    "tod_median_30m_range",
    "daily_net_pnl",
    "expected_mfe_per_unit",
    "calibration_sample_size",
    "calibrated_mae_p90",
)

_CANDIDATE_KEYS = (
    "action",
    "instrument_key",
    "strike",
    "entry_price",
    "stop_price",
    "provisional_target_price",
    "risk_per_unit",
    "provisional_reward_per_unit",
    "level_source",
    "calibration_sample_size",
    "theta_decay_per_unit",
    "theta_required_underlying_move",
)


class SnapshotBuilder:
    def build(
        self,
        current_row: Mapping,
        recent_rows: Sequence[Mapping],
        now: datetime,
    ) -> Mapping:
        captured_at = _aware(current_row.get("captured_at"))
        row_time = _aware(current_row.get("time"))
        if captured_at is None or row_time is None:
            raise SnapshotError("MISSING_TIMESTAMPS")
        if now.tzinfo is None:
            now = now.replace(tzinfo=IST)
        age_ms = max(0.0, (now - captured_at).total_seconds() * 1000.0)
        if age_ms > MAX_SNAPSHOT_AGE_MS:
            raise SnapshotError("SNAPSHOT_STALE")
        candidate = _parse_json_value(current_row.get("shadow_candidate"))
        chain_window = _parse_json_value(current_row.get("chain_window"))
        if not isinstance(candidate, dict):
            raise SnapshotError("MISSING_CANDIDATE")
        if not isinstance(chain_window, list):
            raise SnapshotError("MISSING_CHAIN_WINDOW")

        candidate_out = {
            key: candidate.get(key) for key in _CANDIDATE_KEYS
        }
        for name in ("cost_1_lot", "cost_5_lots"):
            cost = candidate.get(name)
            summary = None
            if isinstance(cost, dict):
                summary = {
                    "per_unit": cost.get("per_unit"),
                    "breakeven_ticks": cost.get("breakeven_ticks"),
                }
            candidate_out[name] = summary

        bar_rows = []
        seen = set()
        for row in recent_rows:
            bar_time = _aware(row.get("bar_time"))
            if bar_time is None or bar_time in seen:
                continue
            seen.add(bar_time)
            bar_rows.append((bar_time, row))
        bar_rows.sort(key=lambda item: item[0])
        bar_rows = bar_rows[-MAX_RECENT_ROWS:]
        csv_lines = ["ts,o,h,l,c"]
        for bar_time, row in bar_rows:
            values = [
                row.get("spot_bar_open"),
                row.get("spot_bar_high"),
                row.get("spot_bar_low"),
                row.get("spot_bar_close"),
            ]
            if any(v is None or isinstance(v, bool) for v in values):
                continue
            csv_lines.append(
                "{},{}".format(
                    bar_time.astimezone(IST).strftime("%H:%M"),
                    ",".join(_num(v, 1) for v in values),
                )
            )
        spot_csv = "\n".join(csv_lines)

        chain_lines = [
            "strike,ce_mid,pe_mid,ce_oi,pe_oi,ce_iv,pe_iv,ce_delta,pe_delta"
        ]
        for entry in chain_window[:MAX_CHAIN_ROWS]:
            if not isinstance(entry, dict):
                continue
            chain_lines.append(
                ",".join(
                    (
                        _num(entry.get("strike"), 1),
                        _num(entry.get("ce_mid"), 2),
                        _num(entry.get("pe_mid"), 2),
                        _num(entry.get("ce_oi"), 0),
                        _num(entry.get("pe_oi"), 0),
                        _num(entry.get("ce_iv"), 2),
                        _num(entry.get("pe_iv"), 2),
                        _num(entry.get("ce_delta"), 2),
                        _num(entry.get("pe_delta"), 2),
                    )
                )
            )
        chain_csv = "\n".join(chain_lines)

        features = {
            key: _round4(_parse_json_value(current_row.get(key)))
            for key in _FEATURE_KEYS
        }
        snapshot = {
            "meta": {
                "ts_ist": captured_at.astimezone(IST).isoformat(),
                "snapshot_age_ms": round(age_ms),
                "engine_version": ENGINE_VERSION,
                "trigger": "periodic",
                "shadow_mode": True,
            },
            "regime": {
                "session_state": current_row.get("session_state"),
                "is_expiry_day": current_row.get("is_expiry_day"),
                "minutes_to_derivatives_close": current_row.get(
                    "minutes_to_derivatives_close"
                ),
                "data_ok": not current_row.get("data_is_stale"),
            },
            "candidate": candidate_out,
            "features": features,
            "gates": {
                "blockers": _parse_json_value(
                    current_row.get("gate_reasons"), []
                )
                or [],
                "warnings": _parse_json_value(
                    current_row.get("gate_warnings"), []
                )
                or [],
            },
            "spot_1m_csv": spot_csv,
            "chain_csv": chain_csv,
        }
        serialized = json.dumps(
            snapshot, separators=(",", ":"), sort_keys=True
        )
        if len(serialized.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise SnapshotError("SNAPSHOT_TOO_LARGE")
        return snapshot


_NUMBER_TOKEN = re.compile(r"-?\d+(?:\.\d+)?")


def _collect_numbers(value, out):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        try:
            out.add(Decimal(str(value)))
        except InvalidOperation:
            pass
        return
    if isinstance(value, str):
        for token in _NUMBER_TOKEN.findall(value):
            try:
                out.add(Decimal(token))
            except InvalidOperation:
                continue
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _collect_numbers(item, out)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _collect_numbers(item, out)


def _is_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


_PROHIBITED_LANGUAGE = re.compile(
    r"\b(guaranteed|guarantee|sure|certain|must\s+rise|must\s+fall|"
    r"lots?|leverage|position\s+size)\b",
    re.IGNORECASE,
)


def _check_prohibited_language(text) -> None:
    if _PROHIBITED_LANGUAGE.search(text):
        raise AdviceValidationError("PROHIBITED_LANGUAGE")


def _check_numeric_provenance(text, snapshot_numbers) -> None:
    for token in _NUMBER_TOKEN.findall(text):
        try:
            value = Decimal(token)
        except InvalidOperation:
            continue
        if value not in snapshot_numbers:
            raise AdviceValidationError("NUMERIC_PROVENANCE", True)


def _strict_json(raw):
    return json.loads(
        raw,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(value)
        ),
    )


def validate_advice(raw: str, snapshot: Mapping) -> Advice:
    try:
        parsed = _strict_json(raw)
    except (ValueError, TypeError):
        raise AdviceValidationError("INVALID_JSON")
    if not isinstance(parsed, dict) or set(parsed) != ADVICE_KEYS:
        raise AdviceValidationError("SCHEMA")
    action = parsed["action"]
    if action not in ("LONG_CALL", "LONG_PUT", "NO_TRADE"):
        raise AdviceValidationError("SCHEMA")
    confidence = parsed["confidence"]
    if not _is_number(confidence) or not (0 <= confidence <= 1):
        raise AdviceValidationError("SCHEMA")
    if parsed["setup_quality"] not in ("A", "B", "C"):
        raise AdviceValidationError("SCHEMA")
    if not isinstance(parsed["data_conflict"], bool):
        raise AdviceValidationError("SCHEMA")
    for name in ("idea_fails_if", "reason"):
        value = parsed[name]
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > 200
        ):
            raise AdviceValidationError("SCHEMA")
    if len(parsed["reason"].split()) > 25:
        raise AdviceValidationError("REASON_TOO_LONG")
    _check_prohibited_language(parsed["idea_fails_if"])
    _check_prohibited_language(parsed["reason"])

    candidate = snapshot.get("candidate") or {}
    levels = (
        parsed["entry_price"],
        parsed["stop_price"],
        parsed["target_price"],
    )
    if action == "NO_TRADE":
        if any(level is not None for level in levels):
            raise AdviceValidationError("LEVEL_MISMATCH")
    else:
        if not candidate or action != candidate.get("action"):
            raise AdviceValidationError("ACTION_MISMATCH")
        expected = (
            candidate.get("entry_price"),
            candidate.get("stop_price"),
            candidate.get("provisional_target_price"),
        )
        for name, level, want in zip(
            ("entry_price", "stop_price", "target_price"), levels, expected
        ):
            if not _is_number(level):
                raise AdviceValidationError("LEVEL_MISMATCH")
            if want is None or Decimal(str(level)) != Decimal(str(want)):
                raise AdviceValidationError("LEVEL_MISMATCH")
        entry, stop, target = levels
        if not (stop < entry < target):
            raise AdviceValidationError("LEVEL_ORDER")

    snapshot_numbers = set()
    _collect_numbers(snapshot, snapshot_numbers)
    _check_numeric_provenance(parsed["idea_fails_if"], snapshot_numbers)
    _check_numeric_provenance(parsed["reason"], snapshot_numbers)

    return Advice(
        action=action,
        confidence=float(confidence),
        setup_quality=parsed["setup_quality"],
        entry_price=levels[0],
        stop_price=levels[1],
        target_price=levels[2],
        idea_fails_if=parsed["idea_fails_if"],
        data_conflict=parsed["data_conflict"],
        reason=parsed["reason"],
    )


def apply_engine_demotions(advice: Advice) -> "tuple[Advice, str | None]":
    if 0.45 <= advice.confidence <= 0.55:
        return (
            Advice(
                "NO_TRADE", advice.confidence, advice.setup_quality,
                None, None, None, advice.idea_fails_if,
                advice.data_conflict, advice.reason,
            ),
            "BORDERLINE_CONFIDENCE",
        )
    if advice.data_conflict:
        return (
            Advice(
                "NO_TRADE", advice.confidence, advice.setup_quality,
                None, None, None, advice.idea_fails_if,
                advice.data_conflict, advice.reason,
            ),
            "DATA_CONFLICT",
        )
    return advice, None


class AdviceService:
    def __init__(self, store, model_client, *, now=None) -> None:
        self._store = store
        self._client = model_client
        self._now = now or (lambda: datetime.now(IST))

    def run_once(self) -> AdviceRunResult:
        now = self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=IST)
        current = self._store.latest_market_data()
        if current is None:
            return AdviceRunResult(
                status="SKIPPED",
                advice_id=None,
                advice=None,
                fallback_reason="NO_MARKET_DATA",
            )
        candidate = _parse_json_value(current.get("shadow_candidate"))
        if not isinstance(candidate, dict):
            return AdviceRunResult(
                status="SKIPPED",
                advice_id=None,
                advice=None,
                fallback_reason="NO_SHADOW_CANDIDATE",
            )
        blockers = _parse_json_value(current.get("gate_reasons"), []) or []
        hard = sorted(set(blockers) - TOLERATED_SHADOW_BLOCKERS)
        if hard:
            return AdviceRunResult(
                status="SKIPPED",
                advice_id=None,
                advice=None,
                fallback_reason="ENGINE_BLOCK:" + ",".join(hard),
            )
        if self._store.model_advice_exists(current["time"], PROMPT_SHA256):
            return AdviceRunResult(
                status="SKIPPED",
                advice_id=None,
                advice=None,
                fallback_reason="ALREADY_ADVISED",
            )
        recent = self._store.recent_market_data(
            limit=MAX_RECENT_ROWS, through=current["time"]
        )
        try:
            snapshot = SnapshotBuilder().build(current, recent, now)
        except SnapshotError as error:
            return AdviceRunResult(
                status="SKIPPED",
                advice_id=None,
                advice=None,
                fallback_reason="SNAPSHOT:" + str(error),
            )
        snapshot_json = json.dumps(
            snapshot, separators=(",", ":"), sort_keys=True
        )
        exact_input = json.dumps(
            {"system_prompt": SYSTEM_PROMPT, "snapshot": snapshot},
            separators=(",", ":"),
            sort_keys=True,
        )
        attempts = []
        advice = None
        fallback_reason = None
        raw_output = ""
        started = time.monotonic()
        repair = None
        for attempt_index in range(2):
            attempt_started = time.monotonic()
            raw = None
            try:
                raw = self._client.generate(
                    SYSTEM_PROMPT, snapshot_json, ADVICE_SCHEMA,
                    repair_error=repair,
                )
                raw_output = raw
                advice = validate_advice(raw, snapshot)
                attempts.append(
                    {
                        "raw": raw,
                        "error": None,
                        "hallucination_event": False,
                        "latency_ms": round(
                            (time.monotonic() - attempt_started) * 1000.0, 3
                        ),
                    }
                )
                break
            except AdviceValidationError as error:
                attempts.append(
                    {
                        "raw": raw,
                        "error": error.code,
                        "hallucination_event": error.hallucination_event,
                        "latency_ms": round(
                            (time.monotonic() - attempt_started) * 1000.0, 3
                        ),
                    }
                )
                if attempt_index == 0:
                    repair = error.code
                    continue
                fallback_reason = error.code
            except LLMError as error:
                attempts.append(
                    {
                        "raw": None,
                        "error": type(error).__name__,
                        "hallucination_event": False,
                        "latency_ms": round(
                            (time.monotonic() - attempt_started) * 1000.0, 3
                        ),
                    }
                )
                fallback_reason = type(error).__name__
                break
        latency_ms = round((time.monotonic() - started) * 1000.0, 3)

        if advice is not None:
            advice, demotion = apply_engine_demotions(advice)
            if demotion is not None:
                fallback_reason = demotion

        status = "ADVISED" if advice is not None else "FALLBACK"
        if advice is None:
            advice = _fallback_advice()
            if fallback_reason is None:
                fallback_reason = "UNKNOWN"
        advice_id = str(uuid.uuid4())
        times = [_aware(row.get("time")) for row in recent]
        times = [t for t in times if t is not None]
        context_from = min(times) if times else _aware(current["time"])
        context_to = _aware(current["time"])
        row = ModelAdviceRow(
            advice_id=advice_id,
            advice_at=now,
            context_from=context_from,
            context_to=context_to,
            prompt_version=PROMPT_VERSION,
            model_name=getattr(self._client, "model", "unknown"),
            action=advice.action,
            confidence=advice.confidence,
            setup_quality=advice.setup_quality,
            entry_price=advice.entry_price,
            stop_price=advice.stop_price,
            target_price=advice.target_price,
            idea_fails_if=advice.idea_fails_if,
            data_conflict=advice.data_conflict,
            reason=advice.reason,
            exact_model_input=exact_input,
            exact_model_output=raw_output,
            exact_model_output_raw=raw_output,
            source="shadow",
            instrument_key=candidate.get("instrument_key"),
            strike=candidate.get("strike"),
            prompt_hash=PROMPT_SHA256,
            latency_ms=latency_ms,
            fallback_reason=fallback_reason,
            validation_events=json.dumps(
                [
                    a["error"]
                    for a in attempts
                    if a["error"] is not None
                ],
                separators=(",", ":"),
            ),
            reask_used=len(attempts) > 1,
            hallucination_event=any(
                a["hallucination_event"] for a in attempts
            ),
            model_attempts=json.dumps(
                attempts, separators=(",", ":")
            ),
        )
        self._store.insert_model_advice(row)
        return AdviceRunResult(
            status=status,
            advice_id=advice_id,
            advice=advice,
            fallback_reason=fallback_reason,
            snapshot=snapshot,
        )


def advice_payload(result: AdviceRunResult) -> Mapping:
    return {
        "status": result.status,
        "advice_id": result.advice_id,
        "advice": asdict(result.advice) if result.advice is not None else None,
        "fallback_reason": result.fallback_reason,
    }


def _alert_price(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "n/a"
    return f"{value:.2f}"


def format_shadow_alert(result: AdviceRunResult) -> str:
    if result.status == "SKIPPED":
        return ""
    advice = result.advice
    snapshot = result.snapshot or {}
    candidate = snapshot.get("candidate") or {}
    meta = snapshot.get("meta") or {}
    action = advice.action if advice else None
    decision = {
        "LONG_CALL": "BUY A CALL",
        "LONG_PUT": "BUY A PUT",
        "NO_TRADE": "DO NOT BUY",
    }.get(action, "NO DECISION")
    lines = [
        "PAPER TRADE TEST",
        f"Time: {meta.get('ts_ist') or 'n/a'}",
        f"Decision ID: {result.advice_id or 'n/a'}",
        f"Decision: {decision}",
    ]
    if action in ("LONG_CALL", "LONG_PUT"):
        option_type = "CALL" if action == "LONG_CALL" else "PUT"
        lines.extend(
            [
                f"Option: NIFTY {_alert_price(candidate.get('strike'))} {option_type}",
                f"Buy price: ₹{_alert_price(advice.entry_price)}",
                f"Stop price: ₹{_alert_price(advice.stop_price)}",
                f"Sell target: ₹{_alert_price(advice.target_price)}",
            ]
        )
    lines.extend(
        [
            f"Setup quality: {advice.setup_quality if advice else 'n/a'}",
            "Confidence label: "
            + (f"{advice.confidence:.2f}" if advice else "n/a"),
            f"Reason: {advice.reason if advice else 'n/a'}",
        ]
    )
    if action in ("LONG_CALL", "LONG_PUT"):
        lines.append(f"Invalid if: {advice.idea_fails_if}")
    if result.fallback_reason:
        lines.append(f"System stop reason: {result.fallback_reason}")
    lines.extend(
        [
            "Paper trade only. Do not place a real order.",
            "SHADOW ONLY - DO NOT EXECUTE",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot.advisory",
        description="Produce one shadow advice decision from the latest market row",
    )
    parser.add_argument("--db-path", type=Path, default=Path("data/trading_bot.duckdb"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--output", choices=("json", "text"), default="json"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot-only", action="store_true")
    mode.add_argument("--once", action="store_true")
    return parser


def _emit(stream, payload) -> None:
    print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), file=stream)


def run(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with DuckDBStore(args.db_path) as store:
            if args.snapshot_only:
                now = datetime.now(IST)
                current = store.latest_market_data()
                if current is None:
                    _emit(sys.stderr, {"ok": False, "error": "NO_MARKET_DATA"})
                    return 1
                recent = store.recent_market_data(
                    limit=MAX_RECENT_ROWS, through=current["time"]
                )
                snapshot = SnapshotBuilder().build(current, recent, now)
                _emit(sys.stdout, {"ok": True, "snapshot": snapshot})
                return 0
            load_env_file(
                args.env_file,
                names=("OPENAI_API_KEY", "TRADING_BOT_LLM_MODEL"),
            )
            client = OpenAIResponsesClient.from_env()
            service = AdviceService(store, client)
            result = service.run_once()
            if args.output == "text":
                if result.status == "SKIPPED":
                    print(
                        f"SKIPPED: {result.fallback_reason}",
                        file=sys.stdout,
                    )
                else:
                    print(format_shadow_alert(result), file=sys.stdout)
            else:
                _emit(
                    sys.stdout,
                    {"ok": True, **advice_payload(result)},
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
