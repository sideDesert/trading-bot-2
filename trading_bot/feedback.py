import argparse
import json
import math
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import NormalDist
from typing import Mapping

from .config import load_env_file
from .features import IST, linear_quantile, parse_candles
from .risk import CostConfig, calculate_round_trip_cost
from .storage import DuckDBStore, TradeFeedbackRow
from .upstox.client import UpstoxClient, UpstoxError


class FeedbackValidationError(Exception):
    pass


class OutcomeDataError(Exception):
    pass


@dataclass(frozen=True)
class Excursion:
    exit_price: "float | None"
    exited_at: "datetime | None"
    mae: "float | None"
    mfe: "float | None"
    result_status: str


@dataclass(frozen=True)
class SettlementFailure:
    advice_id: str
    error_type: str
    message: str


@dataclass(frozen=True)
class SettlementBatch:
    settled: tuple
    failures: tuple


def _aware_ist(value, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise OutcomeDataError(f"{name} must be a datetime")
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value.astimezone(IST)


def _floor_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def calculate_excursion(
    candles,
    entry_price,
    entered_at,
    horizon_end,
    stop_price=None,
    target_price=None,
) -> Excursion:
    if entry_price is None or entry_price <= 0:
        raise OutcomeDataError("entry_price must be > 0")
    entered_at = _aware_ist(entered_at, "entered_at")
    horizon_end = _aware_ist(horizon_end, "horizon_end")
    if horizon_end <= entered_at:
        raise OutcomeDataError("horizon_end must be after entered_at")
    if stop_price is not None and not 0 < stop_price < entry_price:
        raise OutcomeDataError("stop_price must be > 0 and < entry_price")
    if target_price is not None and target_price <= entry_price:
        raise OutcomeDataError("target_price must be > entry_price")
    start_floor = _floor_minute(entered_at)
    eligible = []
    for candle in candles:
        stamp = _aware_ist(candle.time, "candle.time")
        if stamp > start_floor and stamp + timedelta(minutes=1) <= horizon_end:
            eligible.append((stamp, candle))
    eligible.sort(key=lambda pair: pair[0])
    if not eligible:
        return Excursion(None, None, None, None, "MISSING_DATA")
    mae = 0.0
    mfe = 0.0
    for stamp, candle in eligible:
        stop_hit = stop_price is not None and candle.low <= stop_price
        target_hit = target_price is not None and candle.high >= target_price
        if stop_hit and target_hit:
            return Excursion(
                stop_price,
                stamp,
                max(mae, entry_price - stop_price),
                mfe,
                "STOP_HIT_AMBIGUOUS",
            )
        if stop_hit:
            return Excursion(
                stop_price,
                stamp,
                max(mae, entry_price - stop_price),
                mfe,
                "STOP_HIT",
            )
        if target_hit:
            return Excursion(
                target_price,
                stamp,
                mae,
                max(mfe, target_price - entry_price),
                "TARGET_HIT",
            )
        mae = max(mae, entry_price - candle.low)
        mfe = max(mfe, candle.high - entry_price)
    last_stamp, last = eligible[-1]
    return Excursion(last.close, last_stamp, mae, mfe, "HORIZON_EXIT")


class FeedbackService:
    def __init__(self, store, upstox_client=None, now=None) -> None:
        self._store = store
        self._client = upstox_client
        self._now = now or (lambda: datetime.now(IST))

    def _require_advice(self, advice_id, evaluation_mode):
        if not isinstance(advice_id, str) or not advice_id.strip():
            raise FeedbackValidationError("advice_id must be a non-empty string")
        advice = self._store.get_model_advice(advice_id)
        if advice is None:
            raise FeedbackValidationError(f"unknown advice_id: {advice_id}")
        existing = self._store.get_trade_feedback(advice_id, evaluation_mode)
        if existing is not None:
            raise FeedbackValidationError(
                f"{evaluation_mode} feedback already recorded for "
                f"advice_id: {advice_id}"
            )
        return advice

    def record_not_taken(self, advice_id, notes=None) -> TradeFeedbackRow:
        self._require_advice(advice_id, "USER")
        row = TradeFeedbackRow(
            advice_id=advice_id,
            feedback_at=self._now(),
            trade_was_taken=False,
            entered_at=None,
            exited_at=None,
            actual_entry_price=None,
            actual_exit_price=None,
            lots=None,
            user_verdict="NOT_TAKEN",
            mae=None,
            mfe=None,
            user_notes=notes,
            evaluation_mode="USER",
            price_basis="ACTUAL_FILL",
            result_status="NOT_TAKEN",
            lot_size=None,
            quoted_spread=None,
            excursion_source="UNAVAILABLE",
        )
        self._store.insert_trade_feedback(row)
        return row

    def record_user_trade(
        self,
        advice_id,
        entered_at,
        exited_at,
        entry_price,
        exit_price,
        lots,
        verdict,
        notes=None,
        mae=None,
        mfe=None,
    ) -> TradeFeedbackRow:
        advice = self._require_advice(advice_id, "USER")
        if advice["action"] not in ("LONG_CALL", "LONG_PUT"):
            raise FeedbackValidationError(
                "user trade requires a LONG_CALL or LONG_PUT advice"
            )
        entered_at = _aware_ist(entered_at, "entered_at")
        exited_at = _aware_ist(exited_at, "exited_at")
        if exited_at <= entered_at:
            raise FeedbackValidationError("exited_at must be after entered_at")
        for name, value in (
            ("entry_price", entry_price),
            ("exit_price", exit_price),
        ):
            if value is None or value <= 0:
                raise FeedbackValidationError(f"{name} must be > 0")
        if not isinstance(lots, int) or isinstance(lots, bool) or lots <= 0:
            raise FeedbackValidationError("lots must be a positive integer")
        if verdict not in ("WORKED", "DID_NOT_WORK"):
            raise FeedbackValidationError(
                "verdict must be WORKED or DID_NOT_WORK"
            )
        market = self._store.market_data_at(advice["context_to"])
        if market is None:
            raise FeedbackValidationError(
                "market row for advice context_to is missing"
            )
        lot_size = market.get("lot_size")
        if not isinstance(lot_size, int) or lot_size <= 0:
            raise FeedbackValidationError(
                "market lot_size is missing or invalid"
            )
        try:
            candidate = json.loads(market["shadow_candidate"] or "null")
        except ValueError as exc:
            raise FeedbackValidationError(
                "market shadow_candidate is not valid JSON"
            ) from exc
        quoted_spread = (
            candidate.get("quoted_spread")
            if isinstance(candidate, dict)
            else None
        )
        if (mae is None) != (mfe is None):
            raise FeedbackValidationError(
                "mae and mfe must be provided together"
            )
        if mae is not None and (mae < 0 or mfe < 0):
            raise FeedbackValidationError("mae and mfe must be >= 0")
        row = TradeFeedbackRow(
            advice_id=advice_id,
            feedback_at=self._now(),
            trade_was_taken=True,
            entered_at=entered_at,
            exited_at=exited_at,
            actual_entry_price=float(entry_price),
            actual_exit_price=float(exit_price),
            lots=lots,
            user_verdict=verdict,
            mae=mae,
            mfe=mfe,
            user_notes=notes,
            evaluation_mode="USER",
            price_basis="ACTUAL_FILL",
            result_status="USER_RECORDED",
            lot_size=lot_size,
            quoted_spread=quoted_spread,
            excursion_source=(
                "USER_PROVIDED" if mae is not None else "UNAVAILABLE"
            ),
        )
        self._store.insert_trade_feedback(row)
        return row

    def _settle_row(self, advice, horizon_minutes, now) -> TradeFeedbackRow:
        try:
            candidate = json.loads(
                advice.get("market_shadow_candidate") or "null"
            )
        except ValueError as exc:
            raise OutcomeDataError(
                "market shadow_candidate is not valid JSON"
            ) from exc
        if not isinstance(candidate, dict):
            raise OutcomeDataError("market shadow_candidate missing")
        market_lot_size = advice.get("market_lot_size")
        quoted_spread = candidate.get("quoted_spread")
        entry_price = advice["entry_price"]
        stop_price = advice["stop_price"]
        target_price = advice["target_price"]
        if not (
            isinstance(market_lot_size, int)
            and market_lot_size > 0
            and quoted_spread is not None
            and quoted_spread > 0
            and entry_price is not None
            and entry_price > 0
            and stop_price is not None
            and target_price is not None
            and 0 < stop_price < entry_price < target_price
        ):
            raise OutcomeDataError("settlement inputs incomplete")
        evaluation_lots = max(1, int(candidate.get("lots") or 0))
        entered_at = _aware_ist(advice["advice_at"], "advice_at")
        horizon_end = entered_at + timedelta(minutes=horizon_minutes)
        instrument_key = advice["instrument_key"]
        if entered_at.date() == now.date():
            payload = self._client.intraday_candles(
                instrument_key, unit="minutes", interval=1
            )
        else:
            day = entered_at.date().isoformat()
            payload = self._client.historical_candles(
                instrument_key, day, day, unit="minutes", interval=1
            )
        excursion = calculate_excursion(
            parse_candles(payload),
            entry_price,
            entered_at,
            horizon_end,
            stop_price=stop_price,
            target_price=target_price,
        )
        if excursion.result_status == "MISSING_DATA":
            raise OutcomeDataError("no eligible option candles")
        row = TradeFeedbackRow(
            advice_id=advice["advice_id"],
            feedback_at=now,
            trade_was_taken=False,
            entered_at=entered_at,
            exited_at=excursion.exited_at,
            actual_entry_price=float(entry_price),
            actual_exit_price=excursion.exit_price,
            lots=evaluation_lots,
            user_verdict="NOT_TAKEN",
            mae=excursion.mae,
            mfe=excursion.mfe,
            user_notes=(
                f"Automated {horizon_minutes}-minute shadow outcome."
            ),
            evaluation_mode="SHADOW_30M",
            price_basis="SHADOW_QUOTE_MODEL",
            result_status=excursion.result_status,
            lot_size=market_lot_size,
            quoted_spread=quoted_spread,
            excursion_source="OPTION_1M_LTP_PROXY",
        )
        self._store.insert_trade_feedback(row)
        return row

    def settle_pending(self, horizon_minutes: int = 30, limit: int = 20) -> SettlementBatch:
        if self._client is None:
            raise FeedbackValidationError(
                "settle_pending requires an Upstox client"
            )
        if horizon_minutes != 30:
            raise FeedbackValidationError(
                "horizon_minutes must be 30 for SHADOW_30M"
            )
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise FeedbackValidationError("limit must be a positive integer")
        now = _aware_ist(self._now(), "now")
        cutoff = now - timedelta(minutes=horizon_minutes + 2)
        pending = self._store.pending_shadow_advice(cutoff, limit)
        settled = []
        failures = []
        for advice in pending:
            try:
                settled.append(
                    self._settle_row(advice, horizon_minutes, now)
                )
            except (UpstoxError, OutcomeDataError) as error:
                failures.append(
                    SettlementFailure(
                        advice_id=advice["advice_id"],
                        error_type=type(error).__name__,
                        message=str(error),
                    )
                )
        return SettlementBatch(tuple(settled), tuple(failures))


@dataclass(frozen=True)
class DailyPnl:
    value: float
    costed_trades: int
    uncosted_trades: int


@dataclass(frozen=True)
class ExcursionCalibration:
    action: str
    sample_size: int
    mae_p90: "float | None"
    mfe_median: "float | None"


def _costed(row) -> bool:
    return all(
        row.get(name) is not None and row[name] > 0
        for name in ("actual_entry_price", "actual_exit_price", "lots", "lot_size")
    ) and row.get("quoted_spread") is not None and row["quoted_spread"] >= 0


def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def _row_costs(row, cost_config):
    if not _costed(row):
        return None
    lots = int(row["lots"])
    lot_size = int(row["lot_size"])
    entry = float(row["actual_entry_price"])
    exit_price = float(row["actual_exit_price"])
    gross = (exit_price - entry) * lots * lot_size
    cost = calculate_round_trip_cost(
        entry,
        exit_price,
        lots,
        lot_size,
        float(row["quoted_spread"]),
        config=cost_config,
    ).total
    return gross, cost, gross - cost


def daily_user_net_pnl(
    rows, day: date, cost_config: CostConfig = CostConfig()
) -> DailyPnl:
    value = 0.0
    costed = 0
    uncosted = 0
    for row in rows:
        if row.get("evaluation_mode") != "USER" or not row.get(
            "trade_was_taken"
        ):
            continue
        exited = row.get("exited_at")
        if not isinstance(exited, datetime):
            continue
        if exited.tzinfo is None:
            exited = exited.replace(tzinfo=IST)
        else:
            exited = exited.astimezone(IST)
        if exited.date() != day:
            continue
        parts = _row_costs(row, cost_config)
        if parts is None:
            uncosted += 1
            continue
        value += parts[2]
        costed += 1
    return DailyPnl(value, costed, uncosted)


def _finite_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def build_excursion_calibration(
    rows, action, min_samples=50, cost_config: CostConfig = CostConfig()
) -> ExcursionCalibration:
    if action not in ("LONG_CALL", "LONG_PUT"):
        raise ValueError("action must be LONG_CALL or LONG_PUT")
    if (
        not isinstance(min_samples, int)
        or isinstance(min_samples, bool)
        or min_samples <= 0
    ):
        raise ValueError("min_samples must be a positive integer")
    maes = []
    mfes = []
    for row in rows:
        if row.get("action") != action:
            continue
        parts = _row_costs(row, cost_config)
        if parts is None or parts[2] <= 0:
            continue
        mae = row.get("mae")
        mfe = row.get("mfe")
        if not _finite_number(mae) or mae < 0:
            continue
        if not _finite_number(mfe) or mfe <= 0:
            continue
        maes.append(float(mae))
        mfes.append(float(mfe))
    count = len(maes)
    if count < min_samples:
        return ExcursionCalibration(action, count, None, None)
    return ExcursionCalibration(
        action,
        count,
        linear_quantile(maes, 0.90),
        statistics.median(mfes),
    )


_EULER_MASCHERONI = 0.5772156649015329


def deflated_sharpe_ratio(returns, trial_count: int) -> Mapping:
    if (
        not isinstance(trial_count, int)
        or isinstance(trial_count, bool)
        or trial_count <= 0
    ):
        raise ValueError("trial_count must be a positive integer")
    clean = [
        float(value)
        for value in returns
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    ]
    n = len(clean)
    result = {
        "sample_size": n,
        "trial_count": trial_count,
        "sharpe_per_trade": None,
        "benchmark_sharpe": None,
        "standard_error": None,
        "skew": None,
        "kurtosis": None,
        "value": None,
    }
    if n < 3:
        return result
    stdev = statistics.stdev(clean)
    if stdev <= 0:
        return result
    sr = _mean(clean) / stdev
    m2 = sum((value - _mean(clean)) ** 2 for value in clean) / n
    if m2 <= 0:
        return result
    m3 = sum((value - _mean(clean)) ** 3 for value in clean) / n
    m4 = sum((value - _mean(clean)) ** 4 for value in clean) / n
    skew = m3 / m2 ** 1.5
    kurtosis = m4 / m2 ** 2
    numerator = 1 - skew * sr + ((kurtosis - 1) / 4) * sr * sr
    if numerator <= 0:
        result.update(
            sharpe_per_trade=sr, skew=skew, kurtosis=kurtosis
        )
        return result
    sr_se = math.sqrt(numerator / (n - 1))
    if not math.isfinite(sr_se) or sr_se <= 0:
        result.update(
            sharpe_per_trade=sr, skew=skew, kurtosis=kurtosis
        )
        return result
    normal = NormalDist()
    if trial_count == 1:
        benchmark = 0.0
    else:
        benchmark = sr_se * (
            (1 - _EULER_MASCHERONI) * normal.inv_cdf(1 - 1 / trial_count)
            + _EULER_MASCHERONI
            * normal.inv_cdf(1 - 1 / (trial_count * math.e))
        )
    value = normal.cdf((sr - benchmark) / sr_se)
    result.update(
        sharpe_per_trade=sr,
        benchmark_sharpe=benchmark,
        standard_error=sr_se,
        skew=skew,
        kurtosis=kurtosis,
        value=min(1.0, max(0.0, value)),
    )
    return result


def _round_dsr(dsr: Mapping) -> Mapping:
    rounded = {}
    for key, value in dsr.items():
        if isinstance(value, float):
            rounded[key] = round(value, 6)
        else:
            rounded[key] = value
    return rounded


def build_evaluation_report(
    rows, cost_config: CostConfig = CostConfig(), trial_count: int = 1
) -> Mapping:
    user_records = 0
    shadow_records = 0
    not_taken = 0
    costed = []
    for row in rows:
        if row.get("evaluation_mode") == "SHADOW_30M":
            shadow_records += 1
        else:
            user_records += 1
        if not row.get("trade_was_taken"):
            not_taken += 1
        if not _costed(row):
            continue
        lots = int(row["lots"])
        lot_size = int(row["lot_size"])
        entry = float(row["actual_entry_price"])
        exit_price = float(row["actual_exit_price"])
        gross = (exit_price - entry) * lots * lot_size
        cost = calculate_round_trip_cost(
            entry,
            exit_price,
            lots,
            lot_size,
            float(row["quoted_spread"]),
            config=cost_config,
        ).total
        costed.append(
            {
                "row": row,
                "gross": gross,
                "cost": cost,
                "net": gross - cost,
                "win": gross - cost > 0,
            }
        )
    wins = sum(1 for item in costed if item["win"])
    nets = [item["net"] for item in costed]
    mae_values = [
        float(row["mae"]) for row in rows if row.get("mae") is not None
    ]
    mfe_values = [
        float(row["mfe"]) for row in rows if row.get("mfe") is not None
    ]
    win_capture = [
        (max(float(item["row"]["actual_exit_price"]) - float(item["row"]["actual_entry_price"]), 0.0), float(item["row"]["mfe"]))
        for item in costed
        if item["win"]
        and item["row"].get("mfe") is not None
        and float(item["row"]["mfe"]) > 0
    ]
    capture_ratio = (
        sum(pair[0] for pair in win_capture)
        / sum(pair[1] for pair in win_capture)
        if win_capture
        else None
    )

    def grouped(key):
        groups = {}
        for item in costed:
            value = item["row"].get(key)
            group = groups.setdefault(
                value, {"count": 0, "wins": 0, "net": 0.0}
            )
            group["count"] += 1
            group["wins"] += 1 if item["win"] else 0
            group["net"] += item["net"]
        return {
            str(name): {
                "count": group["count"],
                "objective_wins": group["wins"],
                "net_pnl_inr": round(group["net"], 2),
                "expectancy_inr": round(group["net"] / group["count"], 2),
            }
            for name, group in sorted(groups.items(), key=lambda kv: str(kv[0]))
        }

    expectancy = _mean(nets)
    dsr = deflated_sharpe_ratio(nets, trial_count)
    blocked = []
    if len(costed) < 100:
        blocked.append("SAMPLE_BELOW_100")
    if expectancy is None or expectancy <= 0:
        blocked.append("EXPECTANCY_NOT_POSITIVE")
    if dsr["value"] is None:
        blocked.append("DSR_UNAVAILABLE")
    elif dsr["value"] <= 0.95:
        blocked.append("DSR_BELOW_0_95")
    if capture_ratio is None:
        blocked.append("CAPTURE_RATIO_UNAVAILABLE")
    elif capture_ratio < 0.70:
        blocked.append("CAPTURE_RATIO_BELOW_0_70")
    ready = (
        len(costed) >= 100
        and expectancy is not None
        and expectancy > 0
        and dsr["value"] is not None
        and dsr["value"] > 0.95
        and capture_ratio is not None
        and capture_ratio >= 0.70
    )
    return {
        "total_feedback": len(rows),
        "user_records": user_records,
        "shadow_records": shadow_records,
        "not_taken": not_taken,
        "costed_records": len(costed),
        "objective_wins": wins,
        "objective_win_rate": (
            round(wins / len(costed), 4) if costed else None
        ),
        "gross_pnl_inr": round(sum(item["gross"] for item in costed), 2),
        "costs_inr": round(sum(item["cost"] for item in costed), 2),
        "net_pnl_inr": round(sum(nets), 2),
        "expectancy_inr": round(expectancy, 2) if expectancy is not None else None,
        "mean_mae": round(_mean(mae_values), 4) if mae_values else None,
        "mean_mfe": round(_mean(mfe_values), 4) if mfe_values else None,
        "capture_ratio": (
            round(capture_ratio, 4) if capture_ratio is not None else None
        ),
        "deflated_sharpe": _round_dsr(dsr),
        "by_action": grouped("action"),
        "by_prompt_version": grouped("prompt_version"),
        "by_session_state": grouped("market_session_state"),
        "graduation": {
            "minimum_trades": 100,
            "sample_met": len(costed) >= 100,
            "positive_expectancy": (
                expectancy > 0 if expectancy is not None else False
            ),
            "ready": ready,
            "blocked_by": sorted(blocked),
        },
    }


def _emit(stream, payload) -> None:
    print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), file=stream)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot.feedback",
        description="Record and evaluate shadow trade feedback",
    )
    parser.add_argument(
        "--db-path", type=Path, default=Path("data/trading_bot.duckdb")
    )
    sub = parser.add_subparsers(dest="command", required=True)

    not_taken = sub.add_parser("record-not-taken")
    not_taken.add_argument("--advice-id", required=True)
    not_taken.add_argument("--notes", default=None)

    record = sub.add_parser("record-trade")
    record.add_argument("--advice-id", required=True)
    record.add_argument("--entered-at", required=True)
    record.add_argument("--exited-at", required=True)
    record.add_argument("--entry-price", type=float, required=True)
    record.add_argument("--exit-price", type=float, required=True)
    record.add_argument("--lots", type=int, required=True)
    record.add_argument(
        "--verdict", choices=("WORKED", "DID_NOT_WORK"), required=True
    )
    record.add_argument("--mae", type=float, default=None)
    record.add_argument("--mfe", type=float, default=None)
    record.add_argument("--notes", default=None)

    settle = sub.add_parser("settle-pending")
    settle.add_argument("--horizon-minutes", type=int, default=30)
    settle.add_argument("--limit", type=int, default=20)
    settle.add_argument("--env-file", type=Path, default=Path(".env"))

    recent = sub.add_parser("recent-advice")
    recent.add_argument("--limit", type=int, default=5)

    report_cmd = sub.add_parser("report")
    report_cmd.add_argument("--trial-count", type=int, default=1)
    return parser


_FEEDBACK_ROW_FIELDS = (
    "evaluation_mode",
    "price_basis",
    "result_status",
    "feedback_at",
    "trade_was_taken",
    "entered_at",
    "exited_at",
    "actual_entry_price",
    "actual_exit_price",
    "lots",
    "lot_size",
    "quoted_spread",
    "user_verdict",
    "mae",
    "mfe",
    "user_notes",
    "excursion_source",
)


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _iso_ist(value):
    if not isinstance(value, datetime):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=IST)
    return value.astimezone(IST).isoformat()


def feedback_payload(row: TradeFeedbackRow) -> Mapping:
    payload = asdict(row)
    for name in ("feedback_at", "entered_at", "exited_at"):
        payload[name] = _iso(payload[name])
    return payload


def derived_pnl(row: Mapping, cost_config: CostConfig = CostConfig()) -> Mapping:
    parts = _row_costs(row, cost_config)
    if parts is None:
        return {
            "gross_pnl_inr": None,
            "costs_inr": None,
            "net_pnl_inr": None,
        }
    gross, cost, net = parts
    return {
        "gross_pnl_inr": round(gross, 2),
        "costs_inr": round(cost, 2),
        "net_pnl_inr": round(net, 2),
    }


def recent_advice_payloads(store, limit: int = 5) -> list:
    payloads = []
    for advice in store.recent_model_advice(limit=limit):
        feedback = {}
        for row in store.get_trade_feedback_rows(advice["advice_id"]):
            payload = {
                name: _iso_ist(row.get(name)) for name in _FEEDBACK_ROW_FIELDS
            }
            payload["derived"] = derived_pnl(row)
            feedback[row["evaluation_mode"]] = payload
        payloads.append(
            {
                "advice_id": advice["advice_id"],
                "advice_at": _iso_ist(advice["advice_at"]),
                "action": advice["action"],
                "setup_quality": advice["setup_quality"],
                "confidence": advice["confidence"],
                "entry_price": advice["entry_price"],
                "stop_price": advice["stop_price"],
                "target_price": advice["target_price"],
                "instrument_key": advice["instrument_key"],
                "strike": advice["strike"],
                "source": advice["source"],
                "reason": advice["reason"],
                "feedback": feedback,
            }
        )
    return payloads


def run(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with DuckDBStore(args.db_path) as store:
            if args.command == "record-not-taken":
                row = FeedbackService(store).record_not_taken(
                    args.advice_id, notes=args.notes
                )
                _emit(sys.stdout, {"ok": True, "feedback": feedback_payload(row)})
                return 0
            if args.command == "record-trade":
                row = FeedbackService(store).record_user_trade(
                    args.advice_id,
                    datetime.fromisoformat(args.entered_at),
                    datetime.fromisoformat(args.exited_at),
                    args.entry_price,
                    args.exit_price,
                    args.lots,
                    args.verdict,
                    notes=args.notes,
                    mae=args.mae,
                    mfe=args.mfe,
                )
                _emit(
                    sys.stdout,
                    {
                        "ok": True,
                        "feedback": feedback_payload(row),
                        "derived": derived_pnl(asdict(row)),
                    },
                )
                return 0
            if args.command == "recent-advice":
                _emit(
                    sys.stdout,
                    {
                        "ok": True,
                        "advice": recent_advice_payloads(
                            store, limit=args.limit
                        ),
                    },
                )
                return 0
            if args.command == "settle-pending":
                load_env_file(args.env_file)
                service = FeedbackService(store, UpstoxClient.from_env())
                batch = service.settle_pending(
                    horizon_minutes=args.horizon_minutes, limit=args.limit
                )
                _emit(
                    sys.stdout,
                    {
                        "ok": True,
                        "settled": [
                            feedback_payload(row) for row in batch.settled
                        ],
                        "failures": [
                            asdict(failure) for failure in batch.failures
                        ],
                    },
                )
                return 0
            report = build_evaluation_report(
                store.evaluation_rows(), trial_count=args.trial_count
            )
            _emit(sys.stdout, report)
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
