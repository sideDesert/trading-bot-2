"""Agent-driven decision harness (trading-bot-2).

Unlike the sibling `agent_tool`, NO trade decision is made in Python here. The
Python side only *gathers* facts:

  * raw market data (live quote, option chain, recent 1-minute price action),
  * computed analytics (the full indicator set from the feature engine), and
  * prior agent decisions (history from DuckDB).

The agent reads that context, may web-search for macro/event colour, then makes
the entire call itself (direction + strike + entry/stop/target) and records it
with `record`. The system stays shadow-only; nothing is ever executed.

Commands:
  context   Fetch fresh data + analytics + history as one JSON brief. No verdict.
  record    Persist the agent's own decision.
  recent    List recent agent decisions.
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from .collector import CollectorConfig, MarketDataCollector
from .config import load_env_file
from .features import IST
from .storage import AgentDecisionRow, DuckDBStore
from .upstox.client import UpstoxClient

BOUNDARY = "SHADOW ONLY - DO NOT EXECUTE"

# Factual analytics from the feature engine. Deliberately EXCLUDES the Python
# decision artifacts (gate_reasons, gate_warnings, shadow_candidate,
# block_reason, trading_is_blocked) so the agent forms its own view.
_ANALYTICS_KEYS = (
    "opening_range_state",
    "opening_range_high",
    "opening_range_low",
    "opening_range_width",
    "narrow_range_threshold",
    "opening_range_is_narrow",
    "relative_volume",
    "relative_volume_spike",
    "first_30m_return_pct",
    "futures_vwap",
    "vwap_position",
    "vwap_sigma",
    "iv_percentile",
    "atm_iv",
    "atm_expected_move",
    "expected_move_consumed_pct",
    "realized_vol_10d",
    "vrp_ratio",
    "opening_straddle",
    "pcr",
    "call_oi_wall",
    "put_oi_wall",
    "call_oi_walls",
    "put_oi_walls",
    "local_gex",
    "local_gex_sign",
    "synthetic_fwd_basis",
    "momentum_reversion_selector",
    "tod_median_30m_range",
    "spread",
)

_META_KEYS = (
    "session_state",
    "is_expiry_day",
    "minutes_to_derivatives_close",
    "data_is_stale",
)

_OPTION_KEYS = (
    "atm_strike",
    "atm_call_instrument_key",
    "atm_put_instrument_key",
    "atm_call_price",
    "atm_put_price",
    "lot_size",
)


class AgentBrainError(Exception):
    pass


def _ist(value):
    if isinstance(value, datetime):
        stamp = value if value.tzinfo else value.replace(tzinfo=IST)
        return stamp.astimezone(IST).isoformat()
    return value


def _maybe_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _spot_1m_csv(recent) -> str:
    rows = sorted(
        (r for r in recent if r.get("bar_time") is not None),
        key=lambda r: r["bar_time"],
    )
    lines = ["ts,o,h,l,c"]
    for r in rows:
        o, h, low, c = (
            r.get("spot_bar_open"),
            r.get("spot_bar_high"),
            r.get("spot_bar_low"),
            r.get("spot_bar_close"),
        )
        if None in (o, h, low, c):
            continue
        ts = _ist(r["bar_time"])[11:16]  # HH:MM
        lines.append(f"{ts},{o},{h},{low},{c}")
    return "\n".join(lines)


def build_context(store, *, fetch_status: str, recent_limit: int = 30) -> dict:
    current = store.latest_market_data()
    if current is None:
        return {
            "ok": True,
            "status": "NO_MARKET_DATA",
            "fetch_status": fetch_status,
            "boundary": BOUNDARY,
            "note": "No market data stored yet. Python makes no decision.",
        }
    recent = store.recent_market_data(limit=recent_limit, through=current["time"])
    decisions = store.recent_agent_decisions(limit=10)
    for d in decisions:
        d["decided_at"] = _ist(d.get("decided_at"))
        d["context_ts"] = _ist(d.get("context_ts"))
        d["sources"] = _maybe_json(d.get("sources"))
        # analytics_snapshot is large; expose only that it exists.
        d.pop("analytics_snapshot", None)

    return {
        "ok": True,
        "status": "CONTEXT",
        "fetch_status": fetch_status,
        "boundary": BOUNDARY,
        "note": (
            "Python provides raw data + analytics ONLY. It makes no trade "
            "decision and applies no gates. You decide direction, strike, and "
            "entry/stop/target yourself, or NO_TRADE. Shadow-only."
        ),
        "meta": {
            "ts_ist": _ist(current.get("time")),
            "expiry_date": _ist(current.get("expiry_date")),
            "nifty_spot": current.get("nifty_price"),
            "nifty_future_price": current.get("nifty_future_price"),
            "india_vix": current.get("india_vix"),
            **{k: current.get(k) for k in _META_KEYS},
        },
        "analytics": {
            k: _maybe_json(current.get(k))
            if k in ("call_oi_walls", "put_oi_walls")
            else current.get(k)
            for k in _ANALYTICS_KEYS
        },
        "options": {
            **{k: current.get(k) for k in _OPTION_KEYS},
            "chain_window": _maybe_json(current.get("chain_window")),
        },
        "price_action": {"spot_1m_csv": _spot_1m_csv(recent)},
        "history": {"recent_decisions": decisions},
    }


def _validate_decision(args) -> None:
    action = args.action
    if action not in ("LONG_CALL", "LONG_PUT", "NO_TRADE"):
        raise AgentBrainError("action must be LONG_CALL, LONG_PUT, or NO_TRADE")
    levels = (args.entry_price, args.stop_price, args.target_price)
    if action == "NO_TRADE":
        if any(v is not None for v in levels):
            raise AgentBrainError("NO_TRADE must not carry entry/stop/target")
        return
    if any(v is None for v in levels):
        raise AgentBrainError("a trade requires entry, stop, and target prices")
    entry, stop, target = levels
    if not (stop < entry < target):
        raise AgentBrainError("levels must satisfy stop < entry < target")
    if args.strike is None or not args.instrument_key:
        raise AgentBrainError("a trade requires --strike and --instrument-key")


def queue_paper_order(inbox: Path, store, row: AgentDecisionRow) -> Path:
    market = store.latest_market_data() or {}
    expiry = market.get("expiry_date")
    payload = {
        "decision_id": row.decision_id,
        "decided_at": row.decided_at.isoformat(),
        "action": row.action,
        "instrument_key": row.instrument_key,
        "strike": row.strike,
        "entry_price": row.entry_price,
        "stop_price": row.stop_price,
        "target_price": row.target_price,
        "lot_size": market.get("lot_size"),
        "expiry_date": str(expiry)[:10] if expiry is not None else None,
        "india_vix": market.get("india_vix"),
    }
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / f"{row.decision_id}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)
    return path


def do_record(store, args, now: datetime, inbox: "Path | None" = None) -> dict:
    _validate_decision(args)
    if not args.rationale or not args.rationale.strip():
        raise AgentBrainError("rationale is required")
    sources = None
    if args.sources:
        sources = json.dumps([s for s in args.sources if s.strip()])
    context_ts = (
        datetime.fromisoformat(args.context_ts) if args.context_ts else None
    )
    decision_id = str(uuid.uuid4())
    row = AgentDecisionRow(
        decision_id=decision_id,
        decided_at=now,
        action=args.action,
        rationale=args.rationale.strip(),
        context_ts=context_ts,
        confidence=args.confidence,
        setup_quality=args.setup_quality,
        strike=args.strike,
        instrument_key=args.instrument_key,
        entry_price=args.entry_price,
        stop_price=args.stop_price,
        target_price=args.target_price,
        sources=sources,
        analytics_snapshot=None,
        nifty_spot=args.nifty_spot,
        boundary=BOUNDARY,
    )
    store.insert_agent_decision(row)
    result = {
        "ok": True,
        "status": "RECORDED",
        "decision_id": decision_id,
        "action": args.action,
        "boundary": BOUNDARY,
    }
    if inbox is not None and args.action != "NO_TRADE":
        queue_paper_order(inbox, store, row)
        result["paper_order_queued"] = True
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading_bot.agent_brain", description=__doc__)
    parser.add_argument("--db-path", type=Path, default=Path("data/trading_bot.duckdb"))
    sub = parser.add_subparsers(dest="command", required=True)

    ctx = sub.add_parser("context")
    ctx.add_argument("--env-file", type=Path, default=Path(".env"))
    ctx.add_argument("--recent-limit", type=int, default=30)

    rec = sub.add_parser("record")
    rec.add_argument("--action", required=True)
    rec.add_argument("--strike", type=float, default=None)
    rec.add_argument("--instrument-key", dest="instrument_key", default=None)
    rec.add_argument("--entry-price", dest="entry_price", type=float, default=None)
    rec.add_argument("--stop-price", dest="stop_price", type=float, default=None)
    rec.add_argument("--target-price", dest="target_price", type=float, default=None)
    rec.add_argument("--confidence", type=float, default=None)
    rec.add_argument("--setup-quality", dest="setup_quality", default=None)
    rec.add_argument("--rationale", required=True)
    rec.add_argument("--source", dest="sources", action="append", default=None)
    rec.add_argument("--context-ts", dest="context_ts", default=None)
    rec.add_argument("--nifty-spot", dest="nifty_spot", type=float, default=None)

    listing = sub.add_parser("recent")
    listing.add_argument("--limit", type=int, default=20)
    return parser


def _emit(stream, payload) -> None:
    json.dump(payload, stream, separators=(",", ":"), default=str)
    stream.write("\n")


def run(
    argv=None,
    *,
    upstox_client_factory=UpstoxClient.from_env,
    collector_factory=MarketDataCollector,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        with DuckDBStore(args.db_path) as store:
            if args.command == "context":
                fetch_status = "OK"
                try:
                    load_env_file(args.env_file)
                    client = upstox_client_factory()
                    collector = collector_factory(
                        client, store, CollectorConfig(db_path=args.db_path)
                    )
                    collector.run_once()
                except Exception as error:  # data fetch is best-effort
                    fetch_status = f"FETCH_FAILED:{type(error).__name__}:{error}"
                payload = build_context(
                    store, fetch_status=fetch_status, recent_limit=args.recent_limit
                )
            elif args.command == "record":
                payload = do_record(
                    store,
                    args,
                    datetime.now(IST),
                    inbox=args.db_path.parent / "paper-inbox",
                )
            else:
                payload = {
                    "ok": True,
                    "status": "RECENT",
                    "decisions": store.recent_agent_decisions(limit=args.limit),
                    "boundary": BOUNDARY,
                }
            _emit(sys.stdout, payload)
            return 0
    except (AgentBrainError, Exception) as error:
        _emit(
            sys.stderr,
            {"ok": False, "error": {"type": type(error).__name__, "message": str(error)}},
        )
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
