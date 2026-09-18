"""Seed one synthetic BREAKOUT market_data row and drive it through the
agent-tool advice loop, so the /nifty-advice -> /trade-result flow can be
exercised without waiting for a real opening-range breakout.

This is a TEST/DEMO helper. It never touches live orders; the whole system is
shadow-only. It writes a single fabricated row plus (optionally) one model
advice row, both clearly marked as synthetic.

Why it bypasses the CLI `prepare`: the real `python -m trading_bot.agent_tool
prepare` runs the live collector first (collector.run_once), which would
overwrite the latest row with real market data. So we insert the row and call
AgentToolService.prepare_latest() directly, pinning the same `now` the row was
stamped with.

Usage:
    .venv/bin/python -m scripts.seed_breakout            # call, seeds + submits
    .venv/bin/python -m scripts.seed_breakout --direction put
    .venv/bin/python -m scripts.seed_breakout --no-submit  # stop after READY
"""

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from trading_bot.agent_tool import AgentToolService, _result_payload
from trading_bot.features import IST
from trading_bot.risk import ShadowCandidate, TradeCost
from trading_bot.storage import DuckDBStore, MarketDataRow


def _cost(per_unit: float) -> TradeCost:
    # Illustrative only; costs do not gate READY here (gate_reasons is just
    # SHADOW_MODE), they are shown for realism in the candidate payload.
    return TradeCost(
        brokerage=20.0,
        stt=0.0,
        transaction=0.0,
        sebi=0.0,
        stamp=0.0,
        gst=0.0,
        slippage=0.0,
        total=per_unit,
        per_unit=per_unit,
        breakeven_ticks=1.0,
    )


def _candidate(direction: str) -> ShadowCandidate:
    is_call = direction == "call"
    action = "LONG_CALL" if is_call else "LONG_PUT"
    strike = 23300.0
    entry, stop, target = 120.0, 100.0, 170.0  # stop < entry < target
    key = f"NSE_FO|{'C' if is_call else 'P'}{int(strike)}"
    return ShadowCandidate(
        action=action,
        instrument_key=key,
        strike=strike,
        entry_price=entry,
        stop_price=stop,
        provisional_target_price=target,
        risk_per_unit=entry - stop,
        provisional_reward_per_unit=target - entry,
        risk_budget_inr=2500.0,
        lots=5,
        quoted_spread=0.5,
        cost_1_lot=_cost(1.2),
        cost_5_lots=_cost(0.9),
        sized_cost=_cost(0.9),
        level_source="PROVISIONAL_OR_WIDTH",
        calibration_sample_size=0,
        theta_decay_per_unit=None,
        theta_required_underlying_move=None,
    )


def _seed_row(now: datetime, candidate: ShadowCandidate) -> MarketDataRow:
    is_call = candidate.action == "LONG_CALL"
    return MarketDataRow(
        time=now,
        nifty_price=23295.85,
        india_vix=13.5,
        expiry_date=now.date(),
        atm_strike=candidate.strike,
        atm_call_instrument_key=f"NSE_FO|C{int(candidate.strike)}",
        atm_put_instrument_key=f"NSE_FO|P{int(candidate.strike)}",
        atm_call_price=120.0,
        atm_put_price=110.0,
        data_is_stale=False,
        trading_is_blocked=False,
        block_reason="SYNTHETIC_SEED",
        session_state="PRIME",
        opening_range_state="BREAKOUT_UP" if is_call else "BREAKOUT_DOWN",
        gate_reasons=json.dumps(["SHADOW_MODE"]),
        gate_warnings=json.dumps([]),
        shadow_candidate=json.dumps(asdict(candidate)),
        chain_window=json.dumps([]),
        captured_at=now,
    )


def _advice_json(candidate: ShadowCandidate) -> str:
    # Levels must match the candidate exactly; text carries no digits so it
    # passes numeric-provenance validation. Confidence stays outside the
    # 0.45-0.55 borderline band so it is not demoted to NO_TRADE.
    return json.dumps(
        {
            "action": candidate.action,
            "confidence": 0.72,
            "setup_quality": "B",
            "entry_price": candidate.entry_price,
            "stop_price": candidate.stop_price,
            "target_price": candidate.provisional_target_price,
            "idea_fails_if": "Price falls back inside the opening range.",
            "data_conflict": False,
            "reason": "Opening range broke out on strong volume; momentum favors the trade.",
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=Path("data/trading_bot.duckdb"))
    parser.add_argument("--request-dir", type=Path, default=Path("data/agent-requests"))
    parser.add_argument("--direction", choices=("call", "put"), default="call")
    parser.add_argument(
        "--no-submit",
        dest="submit",
        action="store_false",
        help="Stop after READY without storing a model advice row.",
    )
    args = parser.parse_args()

    # Unique, near-now timestamp so it is fresh and does not collide with an
    # already-advised minute on repeat runs.
    now = datetime.now(IST)
    candidate = _candidate(args.direction)

    with DuckDBStore(args.db_path) as store:
        store.upsert_market_data(_seed_row(now, candidate))
        service = AgentToolService(store, args.request_dir, now=lambda: now)
        result = service.prepare_latest()
        print("prepare ->", json.dumps(_result_payload(result), default=str))

        if result.status != "READY":
            print(
                "\nDid not reach READY. If you re-ran within the same "
                "millisecond, try again; otherwise inspect the reason above."
            )
            return

        print(f"\nREADY. request_id = {result.request_id}")
        if not args.submit:
            print("Skipping submit (--no-submit). Nothing stored.")
            return

        submit = service.submit(
            result.request_id,
            _advice_json(candidate),
            agent_name="seed-breakout-script",
        )
        print("submit ->", submit.status, "advice_id =", submit.advice_id)
        if submit.advice is not None:
            print("advice ->", json.dumps(asdict(submit.advice), default=str))
        print(
            "\nDone. A synthetic BUY advice is now on file. In the looping "
            "session you can run /trade-result to record an outcome against it, "
            "e.g. \"I bought at 120 and sold at 150, one lot\"."
        )


if __name__ == "__main__":
    main()
