import math
import statistics
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
DERIVATIVES_CLOSE = time(15, 40)


@dataclass(frozen=True)
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    oi: float = 0.0


@dataclass(frozen=True)
class FeatureConfig:
    opening_range_minutes: int = 15
    relvol_window_minutes: int = 5
    baseline_sessions: int = 20
    minimum_baseline_sessions: int = 10
    narrow_range_quantile: float = 0.20
    relvol_threshold: float = 1.5
    ivp_sessions: int = 252
    realized_vol_sessions: int = 10
    market_open: time = time(9, 15)


@dataclass(frozen=True)
class FeatureInputs:
    timestamp: datetime
    spot_price: "float | None"
    vix: "float | None"
    future_price: "float | None"
    expiry_date: date
    atm_strike: float
    lot_size: int
    chain_rows: Sequence[Mapping[str, Any]]
    quotes_by_token: Mapping[str, Mapping[str, Any]]
    spot_bars_today: Sequence[Candle]
    future_bars_today: Sequence[Candle]
    spot_minute_history: Sequence[Candle]
    future_minute_history: Sequence[Candle]
    spot_daily_history: Sequence[Candle]
    atm_iv_history: Sequence[float] = ()
    opening_straddle: "float | None" = None
    spread_ratio: "float | None" = None
    data_is_stale: bool = True


@dataclass(frozen=True)
class FeatureFrame:
    timestamp: datetime
    session_state: str
    is_expiry_day: bool
    minutes_to_derivatives_close: int
    lot_size: int
    future_price: "float | None"
    synthetic_fwd_basis: "float | None"
    atm_iv: "float | None"
    atm_expected_move: "float | None"
    opening_straddle: "float | None"
    expected_move_consumed_pct: "float | None"
    iv_percentile: "float | None"
    realized_vol_10d: "float | None"
    vrp_ratio: "float | None"
    opening_range_high: "float | None"
    opening_range_low: "float | None"
    opening_range_width: "float | None"
    narrow_range_threshold: "float | None"
    opening_range_is_narrow: "bool | None"
    opening_range_state: str
    relative_volume: "float | None"
    relative_volume_spike: "bool | None"
    futures_vwap: "float | None"
    vwap_position: str
    vwap_sigma: "float | None"
    first_30m_return_pct: "float | None"
    pcr: "float | None"
    call_oi_walls: tuple
    put_oi_walls: tuple
    local_gex: "float | None"
    local_gex_sign: str
    momentum_reversion_selector: str
    atm_call_delta: "float | None"
    atm_put_delta: "float | None"
    atm_call_theta: "float | None"
    atm_put_theta: "float | None"
    tod_median_30m_range: "float | None"
    missing: tuple


def _ist(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value.astimezone(IST)


def _float(value) -> "float | None":
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _parse_timestamp(value) -> "datetime | None":
    if isinstance(value, datetime):
        return _ist(value)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000.0, tz=IST)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return _ist(datetime.fromisoformat(text))
        except ValueError:
            return None
    return None


def parse_candles(payload) -> "list[Candle]":
    rows = payload.get("candles") if isinstance(payload, Mapping) else payload
    candles = []
    if not isinstance(rows, (list, tuple)):
        return candles
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            continue
        stamp = _parse_timestamp(row[0])
        values = [_float(v) for v in row[1:5]]
        if stamp is None or any(v is None for v in values):
            continue
        volume = _float(row[5]) if len(row) > 5 else None
        oi = _float(row[6]) if len(row) > 6 else None
        candles.append(
            Candle(
                time=stamp,
                open=values[0],
                high=values[1],
                low=values[2],
                close=values[3],
                volume=volume if volume is not None else 0.0,
                oi=oi if oi is not None else 0.0,
            )
        )
    candles.sort(key=lambda candle: candle.time)
    return candles


def linear_quantile(values, quantile) -> "float | None":
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be within [0, 1]")
    cleaned = sorted(v for v in (_float(x) for x in values) if v is not None)
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return cleaned[0]
    h = (len(cleaned) - 1) * quantile
    low = math.floor(h)
    high = math.ceil(h)
    if low == high:
        return cleaned[low]
    return cleaned[low] + (cleaned[high] - cleaned[low]) * (h - low)


def _minute_label(value: datetime) -> time:
    return _ist(value).time().replace(second=0, microsecond=0)


def _minute_of_day(label: time) -> int:
    return label.hour * 60 + label.minute


def _time_from_minutes(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)


def _market_data(side) -> Mapping:
    return (side or {}).get("market_data") or {}


def _greeks(side) -> Mapping:
    return (side or {}).get("option_greeks") or {}


def _atm_chain_row(chain_rows, atm_strike):
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


def _strike_index(chain_rows):
    strikes = sorted(
        {
            strike
            for strike in (_float(row.get("strike_price")) for row in chain_rows or [] if isinstance(row, Mapping))
            if strike is not None
        }
    )
    return strikes


def _top_bid_ask(quote) -> "tuple[float | None, float | None]":
    depth = (quote or {}).get("depth") or {}
    buy = depth.get("buy") or []
    sell = depth.get("sell") or []
    bid = _float(buy[0].get("price")) if buy else None
    ask = _float(sell[0].get("price")) if sell else None
    return bid, ask


def _side_bid_ask(side, quotes_by_token) -> "tuple[float | None, float | None]":
    key = (side or {}).get("instrument_key")
    quote = quotes_by_token.get(key) if key else None
    bid, ask = _top_bid_ask(quote)
    if bid is None or ask is None:
        market = _market_data(side)
        bid = _float(market.get("bid_price"))
        ask = _float(market.get("ask_price"))
    return bid, ask


def _proportional_spread(bid, ask) -> "float | None":
    if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid:
        return None
    return (ask - bid) / ((ask + bid) / 2.0)


class FeatureEngine:
    def __init__(self, config: FeatureConfig = FeatureConfig()) -> None:
        if config.opening_range_minutes <= 0:
            raise ValueError("opening_range_minutes must be > 0")
        if config.relvol_window_minutes <= 0:
            raise ValueError("relvol_window_minutes must be > 0")
        if config.baseline_sessions <= 0:
            raise ValueError("baseline_sessions must be > 0")
        if config.minimum_baseline_sessions <= 0:
            raise ValueError("minimum_baseline_sessions must be > 0")
        if config.minimum_baseline_sessions > config.baseline_sessions:
            raise ValueError("minimum_baseline_sessions must be <= baseline_sessions")
        if not 0 <= config.narrow_range_quantile <= 1:
            raise ValueError("narrow_range_quantile must be within [0, 1]")
        if config.relvol_threshold <= 0:
            raise ValueError("relvol_threshold must be > 0")
        if config.ivp_sessions <= 0:
            raise ValueError("ivp_sessions must be > 0")
        if config.realized_vol_sessions <= 0:
            raise ValueError("realized_vol_sessions must be > 0")
        self._config = config

    def compute(self, inputs: FeatureInputs) -> FeatureFrame:
        cfg = self._config
        ts = _ist(inputs.timestamp)
        tod = ts.time().replace(second=0, microsecond=0)
        tod_exact = ts.time()
        spot = _float(inputs.spot_price)
        vix = _float(inputs.vix)
        future_price = _float(inputs.future_price)

        open_minute = _minute_of_day(cfg.market_open)
        or_end_minute = open_minute + cfg.opening_range_minutes
        minute_now = _minute_of_day(tod)

        session_state = self._session_state(tod_exact, open_minute, or_end_minute)
        close_dt = ts.replace(hour=15, minute=40, second=0, microsecond=0)
        minutes_to_close = max(
            0, math.floor((close_dt - ts).total_seconds() / 60.0)
        )

        chain_rows = [
            row
            for row in (inputs.chain_rows or [])
            if isinstance(row, Mapping)
        ]
        strikes = _strike_index(chain_rows)
        atm_row = _atm_chain_row(chain_rows, inputs.atm_strike)

        atm_iv = self._atm_iv(atm_row)
        expected_move = (
            spot * (atm_iv / 100.0) * math.sqrt(1.0 / 252.0)
            if spot is not None and spot > 0 and atm_iv is not None and atm_iv > 0
            else None
        )

        open_label = cfg.market_open
        open_bars = {
            _minute_label(bar.time): bar for bar in inputs.spot_bars_today or []
        }
        first_open_bar = open_bars.get(open_label)
        consumed = None
        if (
            first_open_bar is not None
            and inputs.opening_straddle is not None
            and inputs.opening_straddle > 0
            and spot is not None
        ):
            consumed = (
                abs(spot - first_open_bar.open) / inputs.opening_straddle * 100.0
            )

        ivp = self._iv_percentile(inputs.atm_iv_history, atm_iv)
        realized = self._realized_vol(inputs.spot_daily_history)
        vrp = (
            atm_iv / realized
            if atm_iv is not None
            and realized is not None
            and atm_iv > 0
            and realized > 0
            else None
        )

        (
            or_high,
            or_low,
            or_width,
            or_state,
        ) = self._opening_range(inputs.spot_bars_today, spot, tod, open_minute)
        threshold = self._narrow_threshold(inputs.spot_daily_history)
        is_narrow = (
            or_width < threshold
            if or_width is not None and threshold is not None
            else None
        )

        relvol = self._relative_volume(
            inputs.future_bars_today, inputs.future_minute_history, ts
        )
        relvol_spike = (
            relvol >= cfg.relvol_threshold if relvol is not None else None
        )

        vwap = self._futures_vwap(inputs.future_bars_today, ts)
        vwap_position = self._vwap_position(future_price, vwap)
        vwap_sigma = self._vwap_sigma(
            inputs.future_bars_today, inputs.future_minute_history, ts, future_price, vwap
        )

        first_30m = self._first_30m_return(inputs.spot_bars_today, tod, open_minute)
        pcr = self._pcr(chain_rows)
        call_walls = self._oi_walls(chain_rows, "call_options")
        put_walls = self._oi_walls(chain_rows, "put_options")
        basis = self._synthetic_basis(
            chain_rows, strikes, inputs.atm_strike, inputs.quotes_by_token, future_price
        )
        gex, gex_sign = self._local_gex(
            chain_rows, strikes, inputs.atm_strike, spot
        )
        selector = self._selector(gex_sign, inputs.spread_ratio)
        call_delta, put_delta, call_theta, put_theta = self._atm_greeks(atm_row)
        tod_range = self._tod_median_30m_range(inputs.spot_minute_history, ts)

        frame = FeatureFrame(
            timestamp=ts,
            session_state=session_state,
            is_expiry_day=ts.date() == inputs.expiry_date,
            minutes_to_derivatives_close=minutes_to_close,
            lot_size=inputs.lot_size,
            future_price=future_price,
            synthetic_fwd_basis=basis,
            atm_iv=atm_iv,
            atm_expected_move=expected_move,
            opening_straddle=inputs.opening_straddle,
            expected_move_consumed_pct=consumed,
            iv_percentile=ivp,
            realized_vol_10d=realized,
            vrp_ratio=vrp,
            opening_range_high=or_high,
            opening_range_low=or_low,
            opening_range_width=or_width,
            narrow_range_threshold=threshold,
            opening_range_is_narrow=is_narrow,
            opening_range_state=or_state,
            relative_volume=relvol,
            relative_volume_spike=relvol_spike,
            futures_vwap=vwap,
            vwap_position=vwap_position,
            vwap_sigma=vwap_sigma,
            first_30m_return_pct=first_30m,
            pcr=pcr,
            call_oi_walls=call_walls,
            put_oi_walls=put_walls,
            local_gex=gex,
            local_gex_sign=gex_sign,
            momentum_reversion_selector=selector,
            atm_call_delta=call_delta,
            atm_put_delta=put_delta,
            atm_call_theta=call_theta,
            atm_put_theta=put_theta,
            tod_median_30m_range=tod_range,
            missing=(),
        )
        missing = sorted(
            name
            for name, value in (
                ("future_price", frame.future_price),
                ("synthetic_fwd_basis", frame.synthetic_fwd_basis),
                ("atm_iv", frame.atm_iv),
                ("atm_expected_move", frame.atm_expected_move),
                ("opening_straddle", frame.opening_straddle),
                ("expected_move_consumed_pct", frame.expected_move_consumed_pct),
                ("iv_percentile", frame.iv_percentile),
                ("realized_vol_10d", frame.realized_vol_10d),
                ("vrp_ratio", frame.vrp_ratio),
                ("opening_range_high", frame.opening_range_high),
                ("opening_range_low", frame.opening_range_low),
                ("opening_range_width", frame.opening_range_width),
                ("narrow_range_threshold", frame.narrow_range_threshold),
                ("opening_range_is_narrow", frame.opening_range_is_narrow),
                ("relative_volume", frame.relative_volume),
                ("relative_volume_spike", frame.relative_volume_spike),
                ("futures_vwap", frame.futures_vwap),
                ("vwap_sigma", frame.vwap_sigma),
                ("first_30m_return_pct", frame.first_30m_return_pct),
                ("pcr", frame.pcr),
                ("local_gex", frame.local_gex),
                ("atm_call_delta", frame.atm_call_delta),
                ("atm_put_delta", frame.atm_put_delta),
                ("atm_call_theta", frame.atm_call_theta),
                ("atm_put_theta", frame.atm_put_theta),
                ("tod_median_30m_range", frame.tod_median_30m_range),
            )
            if value is None
        )
        for name, value in (
            ("opening_range_state", frame.opening_range_state),
            ("vwap_position", frame.vwap_position),
            ("local_gex_sign", frame.local_gex_sign),
        ):
            if value == "UNAVAILABLE":
                missing.append(name)
        return FeatureFrame(**{**frame.__dict__, "missing": tuple(sorted(missing))})

    def _session_state(self, tod: time, open_minute: int, or_end_minute: int) -> str:
        minute = _minute_of_day(tod)
        if minute < open_minute:
            return "PREOPEN"
        if minute < or_end_minute:
            return "OPENING_RANGE"
        if tod < time(11, 15):
            return "PRIME"
        if tod < time(14, 0):
            return "MIDDAY"
        if tod < time(15, 15):
            return "LATE"
        if tod < time(15, 40):
            return "CAS"
        return "CLOSED"

    def _atm_iv(self, atm_row) -> "float | None":
        if atm_row is None:
            return None
        values = []
        for side_name in ("call_options", "put_options"):
            iv = _float(_greeks(atm_row.get(side_name)).get("iv"))
            if iv is not None and iv > 0:
                values.append(iv)
        if not values:
            return None
        return sum(values) / len(values)

    def _iv_percentile(self, history, atm_iv) -> "float | None":
        if atm_iv is None or atm_iv <= 0:
            return None
        valid = [
            v
            for v in (_float(x) for x in history or [])
            if v is not None and v > 0
        ]
        recent = valid[-self._config.ivp_sessions :]
        if len(recent) < self._config.ivp_sessions:
            return None
        below = sum(1 for v in recent if v < atm_iv)
        return below / len(recent) * 100.0

    def _realized_vol(self, daily_history) -> "float | None":
        bars = sorted((daily_history or []), key=lambda bar: bar.time)
        closes = [bar.close for bar in bars if _float(bar.close) is not None]
        need_closes = self._config.realized_vol_sessions + 1
        recent = closes[-need_closes:]
        if len(recent) < 7:
            return None
        returns = [
            math.log(recent[i] / recent[i - 1])
            for i in range(1, len(recent))
            if recent[i - 1] > 0 and recent[i] > 0
        ]
        if len(returns) < 6:
            return None
        return statistics.pstdev(returns) * math.sqrt(252.0) * 100.0

    def _opening_range(self, bars_today, spot, tod, open_minute):
        cfg = self._config
        labels = {
            _time_from_minutes(open_minute + i)
            for i in range(cfg.opening_range_minutes)
        }
        by_label = {}
        for bar in bars_today or []:
            label = _minute_label(bar.time)
            if label in labels and label not in by_label:
                by_label[label] = bar
        or_end = _time_from_minutes(open_minute + cfg.opening_range_minutes)
        if tod < or_end:
            return None, None, None, "FORMING"
        if len(by_label) != cfg.opening_range_minutes:
            return None, None, None, "UNAVAILABLE"
        high = max(bar.high for bar in by_label.values())
        low = min(bar.low for bar in by_label.values())
        width = high - low
        if spot is None or spot <= 0:
            return high, low, width, "UNAVAILABLE"
        if spot > high:
            state = "BREAKOUT_UP"
        elif spot < low:
            state = "BREAKOUT_DOWN"
        else:
            state = "INSIDE"
        return high, low, width, state

    def _narrow_threshold(self, daily_history) -> "float | None":
        cfg = self._config
        bars = sorted((daily_history or []), key=lambda bar: bar.time)
        trs = []
        previous_close = None
        for bar in bars:
            high = _float(bar.high)
            low = _float(bar.low)
            close = _float(bar.close)
            if high is None or low is None:
                previous_close = close
                continue
            tr = high - low
            if previous_close is not None:
                tr = max(
                    tr,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            trs.append(tr)
            previous_close = close if close is not None else previous_close
        recent = trs[-cfg.baseline_sessions :]
        if len(recent) < cfg.minimum_baseline_sessions:
            return None
        return linear_quantile(recent, cfg.narrow_range_quantile)

    def _relative_volume(self, bars_today, minute_history, ts) -> "float | None":
        cfg = self._config
        today_bars = sorted((bars_today or []), key=lambda bar: bar.time)
        current_minute = _minute_label(ts)
        completed = [
            bar for bar in today_bars if _minute_label(bar.time) < current_minute
        ]
        window = completed[-cfg.relvol_window_minutes :]
        if len(window) < cfg.relvol_window_minutes:
            return None
        labels = [_minute_label(bar.time) for bar in window]
        expected = [
            _time_from_minutes(_minute_of_day(labels[0]) + i)
            for i in range(cfg.relvol_window_minutes)
        ]
        if labels != expected:
            return None
        current_total = sum(bar.volume for bar in window)
        label_set = set(labels)
        by_day = {}
        for bar in minute_history or []:
            label = _minute_label(bar.time)
            if label in label_set:
                by_day.setdefault(_ist(bar.time).date(), {})[label] = bar.volume
        totals = []
        for day in sorted(by_day):
            labels_seen = by_day[day]
            if len(labels_seen) == cfg.relvol_window_minutes:
                totals.append(sum(labels_seen.values()))
        recent = totals[-cfg.baseline_sessions :]
        if len(recent) < cfg.minimum_baseline_sessions:
            return None
        baseline = statistics.median(recent)
        if baseline <= 0:
            return None
        return current_total / baseline

    def _futures_vwap(self, bars_today, ts) -> "float | None":
        current_minute = _minute_label(ts)
        numerator = 0.0
        denominator = 0.0
        for bar in sorted((bars_today or []), key=lambda bar: bar.time):
            label = _minute_label(bar.time)
            if label < self._config.market_open or label >= current_minute:
                continue
            typical = (bar.high + bar.low + bar.close) / 3.0
            numerator += typical * bar.volume
            denominator += bar.volume
        if denominator <= 0:
            return None
        return numerator / denominator

    @staticmethod
    def _vwap_position(future_price, vwap) -> str:
        if future_price is None or vwap is None:
            return "UNAVAILABLE"
        diff = future_price - vwap
        if abs(diff) <= 0.05:
            return "AT"
        return "ABOVE" if diff > 0 else "BELOW"

    def _vwap_sigma(self, bars_today, minute_history, ts, future_price, vwap) -> "float | None":
        cfg = self._config
        if future_price is None or vwap is None:
            return None
        today_bars = sorted((bars_today or []), key=lambda bar: bar.time)
        current_minute = _minute_label(ts)
        completed = [
            bar for bar in today_bars if _minute_label(bar.time) < current_minute
        ]
        if not completed:
            return None
        target_label = _minute_label(completed[-1].time)
        by_day = {}
        for bar in minute_history or []:
            by_day.setdefault(_ist(bar.time).date(), []).append(bar)
        deviations = []
        for day in sorted(by_day):
            day_bars = sorted(by_day[day], key=lambda bar: bar.time)
            numerator = 0.0
            denominator = 0.0
            close_at_label = None
            for bar in day_bars:
                label = _minute_label(bar.time)
                if label > target_label:
                    break
                typical = (bar.high + bar.low + bar.close) / 3.0
                numerator += typical * bar.volume
                denominator += bar.volume
                if label == target_label:
                    close_at_label = bar.close
            if close_at_label is None or denominator <= 0:
                continue
            deviations.append(close_at_label - numerator / denominator)
        recent = deviations[-cfg.baseline_sessions :]
        if len(recent) < cfg.minimum_baseline_sessions:
            return None
        sigma = statistics.pstdev(recent)
        if sigma <= 0:
            return None
        return (future_price - vwap) / sigma

    def _first_30m_return(self, bars_today, tod, open_minute) -> "float | None":
        if tod < _time_from_minutes(open_minute + 30):
            return None
        labels = [_time_from_minutes(open_minute + i) for i in range(30)]
        by_label = {}
        for bar in bars_today or []:
            label = _minute_label(bar.time)
            if label in set(labels) and label not in by_label:
                by_label[label] = bar
        if len(by_label) != 30:
            return None
        first = by_label[labels[0]]
        last = by_label[labels[-1]]
        if first.open <= 0:
            return None
        return (last.close / first.open - 1.0) * 100.0

    @staticmethod
    def _pcr(chain_rows) -> "float | None":
        call_oi = 0.0
        put_oi = 0.0
        for row in chain_rows:
            call = _float(_market_data(row.get("call_options")).get("oi"))
            put = _float(_market_data(row.get("put_options")).get("oi"))
            if call is not None and call >= 0:
                call_oi += call
            if put is not None and put >= 0:
                put_oi += put
        if call_oi <= 0 or put_oi <= 0:
            return None
        return put_oi / call_oi

    @staticmethod
    def _oi_walls(chain_rows, side_name) -> tuple:
        pairs = []
        for row in chain_rows:
            strike = _float(row.get("strike_price"))
            oi = _float(_market_data(row.get(side_name)).get("oi"))
            if strike is None or oi is None or oi <= 0:
                continue
            pairs.append((strike, oi))
        pairs.sort(key=lambda pair: (-pair[1], pair[0]))
        return tuple(pairs[:2])

    def _synthetic_basis(
        self, chain_rows, strikes, atm_strike, quotes_by_token, future_price
    ) -> "float | None":
        if future_price is None or not strikes:
            return None
        atm_index = min(
            range(len(strikes)),
            key=lambda i: (abs(strikes[i] - atm_strike), strikes[i]),
        )
        wanted = {
            strikes[i]
            for i in range(max(0, atm_index - 1), min(len(strikes), atm_index + 2))
        }
        forwards = []
        for row in chain_rows:
            strike = _float(row.get("strike_price"))
            if strike is None or strike not in wanted:
                continue
            call_bid, call_ask = _side_bid_ask(
                row.get("call_options"), quotes_by_token
            )
            put_bid, put_ask = _side_bid_ask(
                row.get("put_options"), quotes_by_token
            )
            call_spread = _proportional_spread(call_bid, call_ask)
            put_spread = _proportional_spread(put_bid, put_ask)
            if (
                call_spread is None
                or put_spread is None
                or call_spread > 0.02
                or put_spread > 0.02
            ):
                continue
            call_mid = (call_bid + call_ask) / 2.0
            put_mid = (put_bid + put_ask) / 2.0
            forwards.append(strike + call_mid - put_mid)
        if not forwards:
            return None
        return statistics.median(forwards) - future_price

    def _local_gex(self, chain_rows, strikes, atm_strike, spot):
        if spot is None or spot <= 0 or not strikes:
            return None, "UNAVAILABLE"
        atm_index = min(
            range(len(strikes)),
            key=lambda i: (abs(strikes[i] - atm_strike), strikes[i]),
        )
        wanted = {
            strikes[i]
            for i in range(max(0, atm_index - 5), min(len(strikes), atm_index + 6))
        }
        contributions = []
        for row in chain_rows:
            strike = _float(row.get("strike_price"))
            if strike is None or strike not in wanted:
                continue
            call_oi = _float(_market_data(row.get("call_options")).get("oi"))
            put_oi = _float(_market_data(row.get("put_options")).get("oi"))
            call_gamma = _float(_greeks(row.get("call_options")).get("gamma"))
            put_gamma = _float(_greeks(row.get("put_options")).get("gamma"))
            if (
                call_oi is None
                or put_oi is None
                or call_gamma is None
                or put_gamma is None
                or call_oi < 0
                or put_oi < 0
                or call_gamma < 0
                or put_gamma < 0
            ):
                continue
            contributions.append(
                (put_oi * put_gamma - call_oi * call_gamma) * spot * spot * 0.01
            )
        if not contributions:
            return None, "UNAVAILABLE"
        total = sum(contributions)
        deadband = statistics.median(abs(c) for c in contributions)
        if total > deadband:
            return total, "POSITIVE"
        if total < -deadband:
            return total, "NEGATIVE"
        return total, "NEUTRAL"

    @staticmethod
    def _selector(gex_sign, spread_ratio) -> str:
        if gex_sign == "POSITIVE":
            return "REVERSION_BIAS"
        if gex_sign == "NEGATIVE" and spread_ratio is not None and spread_ratio > 0.02:
            return "MOMENTUM_BIAS"
        return "NEUTRAL"

    def _tod_median_30m_range(self, minute_history, ts) -> "float | None":
        cfg = self._config
        start = _minute_of_day(_minute_label(ts))
        if start + 29 > 23 * 60 + 59:
            return None
        labels = {_time_from_minutes(start + i) for i in range(30)}
        today = _ist(ts).date()
        by_day = {}
        for bar in minute_history or []:
            day = _ist(bar.time).date()
            if day >= today:
                continue
            label = _minute_label(bar.time)
            if label in labels:
                by_day.setdefault(day, {})[label] = bar
        ranges = []
        for day in sorted(by_day):
            bars = by_day[day]
            if len(bars) != 30:
                continue
            ranges.append(
                max(bar.high for bar in bars.values())
                - min(bar.low for bar in bars.values())
            )
        recent = ranges[-cfg.baseline_sessions :]
        if len(recent) < cfg.minimum_baseline_sessions:
            return None
        return statistics.median(recent)

    @staticmethod
    def _atm_greeks(atm_row):
        if atm_row is None:
            return None, None, None, None
        call = _greeks(atm_row.get("call_options"))
        put = _greeks(atm_row.get("put_options"))
        return (
            _float(call.get("delta")),
            _float(put.get("delta")),
            _float(call.get("theta")),
            _float(put.get("theta")),
        )
