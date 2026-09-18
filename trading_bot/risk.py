import math
from dataclasses import dataclass
from datetime import time
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Mapping

from .features import FeatureFrame, FeatureInputs, IST
from .market_rules import TradingCalendar


@dataclass(frozen=True)
class CostConfig:
    brokerage_per_order: float = 20.0
    stt_sell_rate: float = 0.0015
    transaction_rate: float = 0.0003553
    sebi_rate: float = 0.000001
    stamp_buy_rate: float = 0.00003
    gst_rate: float = 0.18
    tick_size: float = 0.05


@dataclass(frozen=True)
class TradeCost:
    brokerage: float
    stt: float
    transaction: float
    sebi: float
    stamp: float
    gst: float
    slippage: float
    total: float
    per_unit: float
    breakeven_ticks: float


@dataclass(frozen=True)
class RiskConfig:
    max_trade_risk_inr: float = 12000.0
    daily_loss_limit_inr: float = 5000.0
    minimum_cost_efficient_lots: int = 2
    maximum_spread_ratio: float = 0.02
    maximum_strike_distance_ratio: float = 0.03
    minimum_relative_volume: float = 1.5
    ivp_block_threshold: float = 65.0
    cost_multiplier: float = 3.0
    earliest_entry: time = time(9, 45)
    latest_entry: time = time(15, 15)
    expiry_entry_cutoff: time = time(13, 15)
    expiry_flat_time: time = time(14, 45)
    shadow_mode: bool = True


@dataclass(frozen=True)
class ShadowCandidate:
    action: str
    instrument_key: str
    strike: float
    entry_price: float
    stop_price: float
    provisional_target_price: float
    risk_per_unit: float
    provisional_reward_per_unit: float
    risk_budget_inr: float
    lots: int
    quoted_spread: float
    cost_1_lot: TradeCost
    cost_5_lots: TradeCost
    sized_cost: "TradeCost | None"
    level_source: str
    calibration_sample_size: int
    theta_decay_per_unit: "float | None"
    theta_required_underlying_move: "float | None"


@dataclass(frozen=True)
class RiskDecision:
    candidate: "ShadowCandidate | None"
    shadow_candidate: bool
    execution_allowed: bool
    blockers: tuple
    warnings: tuple


def calculate_round_trip_cost(
    entry_price,
    exit_price,
    lots,
    lot_size,
    quoted_spread,
    config: CostConfig = CostConfig(),
) -> TradeCost:
    for name, value in (
        ("entry_price", entry_price),
        ("exit_price", exit_price),
        ("lots", lots),
        ("lot_size", lot_size),
        ("tick_size", config.tick_size),
    ):
        if value is None or value <= 0:
            raise ValueError(f"{name} must be > 0")
    for name, value in (
        ("quoted_spread", quoted_spread),
        ("brokerage_per_order", config.brokerage_per_order),
        ("stt_sell_rate", config.stt_sell_rate),
        ("transaction_rate", config.transaction_rate),
        ("sebi_rate", config.sebi_rate),
        ("stamp_buy_rate", config.stamp_buy_rate),
        ("gst_rate", config.gst_rate),
    ):
        if value is None or value < 0:
            raise ValueError(f"{name} must be >= 0")
    units = lots * lot_size
    brokerage = 2 * config.brokerage_per_order
    stt = units * config.stt_sell_rate * exit_price
    transaction = units * config.transaction_rate * (entry_price + exit_price)
    sebi = units * config.sebi_rate * (entry_price + exit_price)
    stamp = units * config.stamp_buy_rate * entry_price
    gst = config.gst_rate * (brokerage + transaction + sebi)
    slippage = units * max(quoted_spread / 2.0, config.tick_size) * 2
    total = brokerage + stt + transaction + sebi + stamp + gst + slippage
    per_unit = total / units
    return TradeCost(
        brokerage=brokerage,
        stt=stt,
        transaction=transaction,
        sebi=sebi,
        stamp=stamp,
        gst=gst,
        slippage=slippage,
        total=total,
        per_unit=per_unit,
        breakeven_ticks=per_unit / config.tick_size,
    )


def _round_up_to_tick(value, tick):
    tick_d = Decimal(str(tick))
    units = (Decimal(str(value)) / tick_d).to_integral_value(
        rounding=ROUND_CEILING
    )
    return float(units * tick_d)


def _round_nearest_tick(value, tick):
    tick_d = Decimal(str(tick))
    units = (Decimal(str(value)) / tick_d).to_integral_value(
        rounding=ROUND_HALF_UP
    )
    return float(units * tick_d)


def _on_tick(value, tick, tolerance=1e-8):
    return abs(value - _round_nearest_tick(value, tick)) <= tolerance


def _float(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _atm_row(chain_rows, atm_strike):
    best = None
    for row in chain_rows or []:
        if not isinstance(row, Mapping):
            continue
        strike = _float(row.get("strike_price"))
        if strike is None:
            continue
        key = (abs(strike - atm_strike), strike)
        if best is None or key < best[0]:
            best = (key, row)
    return best[1] if best else None


def _side_bid_ask(side, quotes_by_token):
    key = (side or {}).get("instrument_key")
    quote = quotes_by_token.get(key) if key else None
    depth = (quote or {}).get("depth") or {}
    buy = depth.get("buy") or []
    sell = depth.get("sell") or []
    bid = _float(buy[0].get("price")) if buy else None
    ask = _float(sell[0].get("price")) if sell else None
    if bid is None or ask is None:
        market = (side or {}).get("market_data") or {}
        bid = _float(market.get("bid_price"))
        ask = _float(market.get("ask_price"))
    return bid, ask


class RiskEngine:
    def __init__(
        self,
        config: RiskConfig = RiskConfig(),
        cost_config: CostConfig = CostConfig(),
        calendar: TradingCalendar = TradingCalendar(),
    ) -> None:
        for name, value in (
            ("max_trade_risk_inr", config.max_trade_risk_inr),
            ("daily_loss_limit_inr", config.daily_loss_limit_inr),
            ("minimum_cost_efficient_lots", config.minimum_cost_efficient_lots),
            ("maximum_spread_ratio", config.maximum_spread_ratio),
            ("maximum_strike_distance_ratio", config.maximum_strike_distance_ratio),
            ("minimum_relative_volume", config.minimum_relative_volume),
            ("ivp_block_threshold", config.ivp_block_threshold),
            ("cost_multiplier", config.cost_multiplier),
        ):
            if value is None or value <= 0:
                raise ValueError(f"{name} must be > 0")
        if config.earliest_entry >= config.latest_entry:
            raise ValueError("earliest_entry must be before latest_entry")
        if config.expiry_entry_cutoff > config.expiry_flat_time:
            raise ValueError("expiry_entry_cutoff must be <= expiry_flat_time")
        self._config = config
        self._cost_config = cost_config
        self._calendar = calendar

    def evaluate(
        self,
        features: FeatureFrame,
        inputs: FeatureInputs,
        *,
        daily_net_pnl: float = 0.0,
        kill_switch_active: bool = False,
        expected_mfe_per_unit: "float | None" = None,
        calibrated_mae_per_unit: "float | None" = None,
        calibrated_mfe_per_unit: "float | None" = None,
        calibration_sample_size: int = 0,
        daily_pnl_available: bool = True,
    ) -> RiskDecision:
        cfg = self._config
        blockers = set()
        warnings = set()
        ts = features.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=IST)
        else:
            ts = ts.astimezone(IST)
        tod = ts.time()
        expiry_day = features.is_expiry_day

        bounds = self._calendar.session_bounds(ts.date())
        if bounds is None:
            blockers.add("UNSUPPORTED_OR_CLOSED_SESSION")
        elif tod < bounds[0] or tod >= bounds[1]:
            blockers.add("OUTSIDE_MARKET_HOURS")
        if tod < cfg.earliest_entry:
            blockers.add("OPEN_BLOCK")
        midday_start = time(12, 30) if expiry_day else time(11, 30)
        midday_end = time(14, 0) if expiry_day else time(13, 30)
        if midday_start <= tod < midday_end:
            blockers.add("MIDDAY_BLOCK")
        if expiry_day and tod >= cfg.expiry_entry_cutoff:
            blockers.add("EXPIRY_ENTRY_CUTOFF")
        if expiry_day and tod >= cfg.expiry_flat_time:
            blockers.add("EXPIRY_FLAT_TIME")
        if tod >= cfg.latest_entry:
            blockers.add("LATE_ENTRY_BLOCK")
        if inputs.data_is_stale:
            blockers.add("STALE_DATA")
        if kill_switch_active:
            blockers.add("KILL_SWITCH")
        if not daily_pnl_available:
            blockers.add("DAILY_PNL_UNAVAILABLE")
        if daily_net_pnl <= -cfg.daily_loss_limit_inr:
            blockers.add("DAILY_LOSS_LIMIT")
        if features.opening_range_is_narrow is None:
            blockers.add("OR_HISTORY_INSUFFICIENT")
        elif features.opening_range_is_narrow:
            blockers.add("NARROW_OPENING_RANGE")
        if features.relative_volume is None:
            blockers.add("RELVOL_HISTORY_INSUFFICIENT")
        elif features.relative_volume < cfg.minimum_relative_volume:
            blockers.add("LOW_RELATIVE_VOLUME")
        if features.iv_percentile is None:
            blockers.add("IVP_HISTORY_INSUFFICIENT")
        elif features.iv_percentile > cfg.ivp_block_threshold:
            blockers.add("IVP_TOO_HIGH")

        candidate, spread_missing, spread_too_wide = self._build_candidate(
            features,
            inputs,
            calibrated_mae_per_unit,
            calibrated_mfe_per_unit,
            calibration_sample_size,
        )
        if candidate is None:
            if features.opening_range_state in ("BREAKOUT_UP", "BREAKOUT_DOWN"):
                blockers.add("CANDIDATE_DATA_MISSING")
            else:
                blockers.add("NO_ORB_BREAKOUT")
            if spread_missing:
                blockers.add("SPREAD_UNAVAILABLE")
        else:
            if spread_too_wide:
                blockers.add("SPREAD_TOO_WIDE")
            spot = _float(inputs.spot_price)
            if spot is not None and spot > 0:
                if (
                    abs(candidate.strike - spot) / spot
                    > cfg.maximum_strike_distance_ratio
                ):
                    blockers.add("STRIKE_TOO_FAR")
            if candidate.lots < 1:
                blockers.add("RISK_BUDGET_TOO_SMALL")
            if candidate.lots < cfg.minimum_cost_efficient_lots:
                blockers.add("COST_INEFFICIENT_SIZE")
            cost_basis = (
                candidate.sized_cost.per_unit
                if candidate.sized_cost is not None
                else candidate.cost_1_lot.per_unit
            )
            if expected_mfe_per_unit is None:
                blockers.add("EXPECTED_MFE_UNAVAILABLE")
            elif expected_mfe_per_unit < cfg.cost_multiplier * cost_basis:
                blockers.add("EXPECTED_EDGE_BELOW_COST")
            if candidate.level_source == "PROVISIONAL_OR_WIDTH":
                blockers.add("CALIBRATION_HISTORY_INSUFFICIENT")
            tod_range = features.tod_median_30m_range
            if (
                candidate.theta_required_underlying_move is None
                or tod_range is None
                or tod_range <= 0
            ):
                blockers.add("THETA_CLOCK_UNAVAILABLE")
            elif candidate.theta_required_underlying_move > tod_range:
                blockers.add("THETA_CLOCK_BLOCK")

        if cfg.shadow_mode:
            blockers.add("SHADOW_MODE")

        if features.local_gex is not None:
            warnings.add("GEX_ASSUMPTION_UNVERIFIED")
        if features.futures_vwap is not None:
            warnings.add("VWAP_IS_MINUTE_BAR_PROXY")
        if candidate is not None:
            if candidate.level_source == "CALIBRATED_MAE_MFE":
                warnings.add("CALIBRATED_MAE_MFE_LEVELS")
            else:
                warnings.add("PROVISIONAL_OR_WIDTH_LEVELS")
        vix = _float(inputs.vix)
        if vix is not None and vix > 16:
            warnings.add("VIX_ABOVE_16")

        return RiskDecision(
            candidate=candidate,
            shadow_candidate=candidate is not None,
            execution_allowed=candidate is not None and not blockers,
            blockers=tuple(sorted(blockers)),
            warnings=tuple(sorted(warnings)),
        )

    def _build_candidate(
        self,
        features,
        inputs,
        calibrated_mae_per_unit=None,
        calibrated_mfe_per_unit=None,
        calibration_sample_size=0,
    ):
        state = features.opening_range_state
        if state == "BREAKOUT_UP":
            side_name = "call_options"
            action = "LONG_CALL"
            delta = features.atm_call_delta
        elif state == "BREAKOUT_DOWN":
            side_name = "put_options"
            action = "LONG_PUT"
            delta = features.atm_put_delta
        else:
            return None, False, False
        row = _atm_row(inputs.chain_rows, inputs.atm_strike)
        if row is None:
            return None, True, False
        side = row.get(side_name) or {}
        key = side.get("instrument_key")
        bid, ask = _side_bid_ask(side, inputs.quotes_by_token)
        if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid:
            return None, True, False
        tick = self._cost_config.tick_size
        if not _on_tick(bid, tick) or not _on_tick(ask, tick):
            return None, False, False
        strike = _float(row.get("strike_price"))
        width = features.opening_range_width
        if (
            not key
            or delta is None
            or delta == 0
            or width is None
            or width <= 0
            or strike is None
            or inputs.lot_size <= 0
        ):
            return None, False, False
        entry = ask
        quoted_spread = ask - bid
        midpoint = (ask + bid) / 2.0
        proportional = quoted_spread / midpoint
        use_calibrated = (
            calibrated_mae_per_unit is not None
            and math.isfinite(calibrated_mae_per_unit)
            and calibrated_mae_per_unit > 0
            and calibrated_mfe_per_unit is not None
            and math.isfinite(calibrated_mfe_per_unit)
            and calibrated_mfe_per_unit > 0
            and calibration_sample_size >= 50
        )
        if use_calibrated:
            level_source = "CALIBRATED_MAE_MFE"
            risk_distance = calibrated_mae_per_unit
            reward_distance = calibrated_mfe_per_unit
        else:
            level_source = "PROVISIONAL_OR_WIDTH"
            provisional = width * abs(delta)
            risk_distance = provisional
            reward_distance = provisional
        raw_stop = max(tick, entry - risk_distance)
        stop = _round_up_to_tick(raw_stop, tick)
        raw_target = entry + reward_distance
        target = _round_nearest_tick(raw_target, tick)
        risk_per_unit = entry - stop
        reward_per_unit = target - entry
        if risk_per_unit <= 0 or reward_per_unit <= 0:
            return None, False, False
        vix = _float(inputs.vix)
        risk_budget = self._config.max_trade_risk_inr * (
            0.5 if vix is not None and vix > 16 else 1.0
        )
        lots = (
            math.floor(risk_budget / (risk_per_unit * inputs.lot_size))
            if risk_per_unit > 0
            else 0
        )
        cost_1 = calculate_round_trip_cost(
            entry, entry, 1, inputs.lot_size, quoted_spread, self._cost_config
        )
        cost_5 = calculate_round_trip_cost(
            entry, entry, 5, inputs.lot_size, quoted_spread, self._cost_config
        )
        sized = (
            calculate_round_trip_cost(
                entry,
                entry,
                lots,
                inputs.lot_size,
                quoted_spread,
                self._cost_config,
            )
            if lots >= 1
            else None
        )
        theta = (
            features.atm_call_theta
            if action == "LONG_CALL"
            else features.atm_put_theta
        )
        theta_decay = None
        theta_required = None
        if theta is not None and math.isfinite(theta):
            theta_decay = abs(theta) * 30 / 385
            cost_basis = (
                sized.per_unit if sized is not None else cost_1.per_unit
            )
            if delta is not None and math.isfinite(delta) and delta != 0:
                theta_required = (theta_decay + cost_basis) / abs(delta)
        candidate = ShadowCandidate(
            action=action,
            instrument_key=key,
            strike=strike,
            entry_price=entry,
            stop_price=stop,
            provisional_target_price=target,
            risk_per_unit=risk_per_unit,
            provisional_reward_per_unit=reward_per_unit,
            risk_budget_inr=risk_budget,
            lots=lots,
            quoted_spread=quoted_spread,
            cost_1_lot=cost_1,
            cost_5_lots=cost_5,
            sized_cost=sized,
            level_source=level_source,
            calibration_sample_size=calibration_sample_size,
            theta_decay_per_unit=theta_decay,
            theta_required_underlying_move=theta_required,
        )
        too_wide = proportional > self._config.maximum_spread_ratio
        return candidate, False, too_wide
