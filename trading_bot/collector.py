import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .advisory import AdviceService, advice_payload, format_shadow_alert
from .config import load_env_file
from .features import FeatureEngine, FeatureInputs, parse_candles
from .feedback import (
    ExcursionCalibration,
    FeedbackService,
    build_excursion_calibration,
    daily_user_net_pnl,
    feedback_payload,
)
from .llm import OpenAIResponsesClient
from .market_rules import TradingCalendar
from .risk import RiskEngine
from .storage import DuckDBStore, MarketDataRow
from .upstox.client import (
    NIFTY_INSTRUMENT_KEY,
    UpstoxClient,
    UpstoxDataError,
    UpstoxError,
)

INDIA_VIX_INSTRUMENT_KEY = "NSE_INDEX|India VIX"
IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class CollectorConfig:
    db_path: Path = Path("data/trading_bot.duckdb")
    quote_interval_seconds: float = 5.0
    chain_interval_seconds: float = 30.0
    stale_after_seconds: float = 15.0
    chain_stale_after_seconds: float = 90.0
    bar_stale_after_seconds: float = 120.0
    historical_calendar_days: int = 45
    kill_switch_path: Path = Path("data/KILL_SWITCH")
    env_file: Path = Path(".env")


@dataclass(frozen=True)
class SessionInstruments:
    session_date: date
    expiry_date: date
    future_instrument_key: str
    atm_strike: float
    call_instrument_key: str
    put_instrument_key: str
    lot_size: int
    basis_option_keys: tuple


def _chain_rows(chain) -> list:
    if isinstance(chain, list):
        return [row for row in chain if isinstance(row, dict)]
    if isinstance(chain, dict):
        for value in chain.values():
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _atm_row(chain_rows, spot):
    candidates = []
    for row in chain_rows:
        strike = row.get("strike_price")
        call_key = (row.get("call_options") or {}).get("instrument_key")
        put_key = (row.get("put_options") or {}).get("instrument_key")
        if strike is None or not call_key or not put_key:
            continue
        try:
            strike_value = float(strike)
        except (TypeError, ValueError):
            continue
        candidates.append((abs(strike_value - spot), strike_value, row))
    if not candidates:
        raise UpstoxDataError("option chain contains no usable strikes")
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][1], candidates[0][2]


def _spot_from_chain(chain_rows):
    for row in chain_rows:
        spot = row.get("underlying_spot_price")
        if spot is not None:
            try:
                return float(spot)
            except (TypeError, ValueError):
                continue
    raise UpstoxDataError("option chain missing underlying_spot_price")


def _nearest_future(instruments, session_date):
    best = None
    for row in instruments or []:
        if not isinstance(row, dict):
            continue
        if row.get("instrument_type") != "FUT":
            continue
        symbol = row.get("trading_symbol") or ""
        if not str(symbol).startswith("NIFTY FUT "):
            continue
        try:
            expiry = date.fromisoformat(str(row.get("expiry")))
        except (TypeError, ValueError):
            continue
        if expiry < session_date:
            continue
        key = row.get("instrument_key")
        if not key:
            continue
        if best is None or expiry < best[0]:
            best = (expiry, key)
    if best is None:
        raise UpstoxDataError("no non-expired NIFTY future found")
    return best[1]


def _basis_option_keys(chain_rows, atm_strike):
    valid = []
    for row in chain_rows:
        if not isinstance(row, dict):
            continue
        try:
            strike = float(row.get("strike_price"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(strike):
            continue
        valid.append((strike, row))
    if not valid:
        return ()
    strikes = sorted({strike for strike, _ in valid})
    atm_index = min(
        range(len(strikes)),
        key=lambda i: (abs(strikes[i] - atm_strike), strikes[i]),
    )
    wanted = {
        strikes[i]
        for i in range(max(0, atm_index - 1), min(len(strikes), atm_index + 2))
    }
    keys = []
    seen = set()
    for strike, row in sorted(valid, key=lambda pair: pair[0]):
        if strike not in wanted:
            continue
        for side_name in ("call_options", "put_options"):
            key = (row.get(side_name) or {}).get("instrument_key")
            if key and key not in seen:
                seen.add(key)
                keys.append(key)
    return tuple(keys)


def _lot_size_for(contracts, instrument_key) -> "int | None":
    for row in contracts or []:
        if not isinstance(row, dict):
            continue
        if row.get("instrument_key") != instrument_key:
            continue
        try:
            size = int(row.get("lot_size"))
        except (TypeError, ValueError):
            return None
        return size if size > 0 else None
    return None


def _validate_lot_size(contracts, call_key, put_key) -> int:
    call_size = _lot_size_for(contracts, call_key)
    put_size = _lot_size_for(contracts, put_key)
    if call_size is None or put_size is None or call_size != put_size:
        raise UpstoxDataError("missing or mismatched ATM lot sizes")
    return call_size


def _quote_timestamp_epoch_ms(quote):
    raw = quote.get("last_trade_time")
    if raw is not None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    raw = quote.get("timestamp")
    if raw is not None:
        try:
            text = str(raw)
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            return datetime.fromisoformat(text).timestamp() * 1000.0
        except (TypeError, ValueError, OverflowError):
            return None
    return None


def _side_spread(bid, ask):
    try:
        bid = float(bid)
        ask = float(ask)
    except (TypeError, ValueError):
        return None
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    midpoint = (ask + bid) / 2.0
    if midpoint <= 0:
        return None
    return (ask - bid) / midpoint


def _quote_top_spread(quote):
    depth = quote.get("depth") or {}
    buy = depth.get("buy") or []
    sell = depth.get("sell") or []
    if not buy or not sell:
        return None
    return _side_spread(buy[0].get("price"), sell[0].get("price"))


def _quote_top_mid(quote):
    depth = quote.get("depth") or {}
    buy = depth.get("buy") or []
    sell = depth.get("sell") or []
    if not buy or not sell:
        return None
    try:
        bid = float(buy[0].get("price"))
        ask = float(sell[0].get("price"))
    except (TypeError, ValueError):
        return None
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    return (bid + ask) / 2.0


def _chain_side_spread(side):
    market = (side or {}).get("market_data") or {}
    return _side_spread(market.get("bid_price"), market.get("ask_price"))


def _mid(bid, ask):
    try:
        bid = float(bid)
        ask = float(ask)
    except (TypeError, ValueError):
        return None
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    return (bid + ask) / 2.0


class MarketDataCollector:
    def __init__(
        self,
        client,
        store,
        config: CollectorConfig = CollectorConfig(),
        *,
        now=None,
        monotonic=None,
        sleep=None,
        feature_engine=None,
        risk_engine=None,
        calendar=None,
    ) -> None:
        self._client = client
        self._store = store
        self._config = config
        self._now = now or (lambda: datetime.now(IST))
        self._monotonic = monotonic or time.monotonic
        self._sleep = sleep or time.sleep
        self._features = feature_engine or FeatureEngine()
        self._risk = risk_engine or RiskEngine()
        self._calendar = calendar or TradingCalendar()
        self._session = None
        self._chain_rows = []
        self._quotes_by_token = {}
        self._last_chain_poll = None
        self._last_chain_success_at = None
        self._spot_minute_history = []
        self._future_minute_history = []
        self._spot_daily_history = []
        self._spot_bars_today = []
        self._future_bars_today = []
        self._last_bar_success_at = None
        self._opening_straddle = None

    def run_once(self) -> MarketDataRow:
        self._ensure_session()
        self._poll_quotes()
        self._refresh_intraday_bars()
        self._maybe_capture_opening_straddle()
        row = self._build_row(self._now_ist().replace(second=0, microsecond=0))
        self._store.upsert_market_data(row)
        return row

    def run_forever(self, on_row=None, on_error=None) -> None:
        last_minute = None
        next_chain_at = (
            self._last_chain_poll + self._config.chain_interval_seconds
            if self._last_chain_poll is not None
            else None
        )
        while True:
            now = self._now_ist()
            if not self._collection_active(now):
                self._sleep(self._config.quote_interval_seconds)
                continue
            if (
                self._session is None
                or now.date() != self._session.session_date
            ):
                try:
                    self._ensure_session()
                    next_chain_at = (
                        self._last_chain_poll + self._config.chain_interval_seconds
                    )
                except UpstoxError as error:
                    if on_error is not None:
                        on_error(error)
                    self._sleep(self._config.quote_interval_seconds)
                    continue
            elif next_chain_at is None or self._monotonic() >= next_chain_at:
                try:
                    self._refresh_chain()
                    self._last_chain_poll = self._monotonic()
                    next_chain_at = (
                        self._last_chain_poll + self._config.chain_interval_seconds
                    )
                except UpstoxError as error:
                    if on_error is not None:
                        on_error(error)
                    next_chain_at = (
                        self._monotonic() + self._config.quote_interval_seconds
                    )
            try:
                self._poll_quotes()
            except UpstoxError as error:
                if on_error is not None:
                    on_error(error)
            self._maybe_capture_opening_straddle()
            minute = self._now_ist().replace(second=0, microsecond=0)
            if minute != last_minute:
                try:
                    self._refresh_intraday_bars()
                except UpstoxError as error:
                    if on_error is not None:
                        on_error(error)
                row = self._build_row(minute)
                self._store.upsert_market_data(row)
                last_minute = minute
                if on_row is not None:
                    on_row(row)
            self._sleep(self._config.quote_interval_seconds)

    def _collection_active(self, now: datetime) -> bool:
        bounds = self._calendar.session_bounds(now.date())
        if bounds is None:
            return False
        tod = now.time()
        start_minutes = bounds[0].hour * 60 + bounds[0].minute - 10
        warmup = (start_minutes // 60, start_minutes % 60)
        warmup_time = now.replace(
            hour=warmup[0], minute=warmup[1], second=0, microsecond=0
        ).time()
        return warmup_time <= tod < bounds[1]

    def _now_ist(self) -> datetime:
        value = self._now()
        if value.tzinfo is None:
            return value.replace(tzinfo=IST)
        return value.astimezone(IST)

    def _historical_minutes(self, instrument_key: str, start: date, end: date):
        if start > end:
            return []
        candles = {}
        chunk_start = start
        while chunk_start <= end:
            chunk_end = min(chunk_start + timedelta(days=28), end)
            payload = self._client.historical_candles(
                instrument_key,
                chunk_start.isoformat(),
                chunk_end.isoformat(),
                unit="minutes",
                interval=1,
            )
            for candle in parse_candles(payload):
                candles[candle.time] = candle
            chunk_start = chunk_end + timedelta(days=1)
        return [candles[key] for key in sorted(candles)]

    def _ensure_session(self) -> None:
        session_date = self._now_ist().date()
        if self._session is not None and self._session.session_date == session_date:
            return
        resolved = self._client.resolve_expiry(
            NIFTY_INSTRUMENT_KEY, "current_week", as_of=session_date
        )
        chain = self._client.option_chain(NIFTY_INSTRUMENT_KEY, resolved)
        rows = _chain_rows(chain)
        if not rows:
            raise UpstoxDataError("option chain contains no usable rows")
        spot = _spot_from_chain(rows)
        strike, atm = _atm_row(rows, spot)
        call_key = atm["call_options"]["instrument_key"]
        put_key = atm["put_options"]["instrument_key"]
        contracts = self._client.option_contracts(NIFTY_INSTRUMENT_KEY, resolved)
        lot_size = _validate_lot_size(contracts, call_key, put_key)
        instruments = self._client.search_instruments("NIFTY FUT", records=30)
        future_key = _nearest_future(instruments, session_date)
        from_day = session_date - timedelta(
            days=self._config.historical_calendar_days
        )
        to_day = session_date - timedelta(days=1)
        spot_minutes = [
            candle
            for candle in self._historical_minutes(
                NIFTY_INSTRUMENT_KEY, from_day, to_day
            )
            if candle.time.date() < session_date
        ]
        future_minutes = [
            candle
            for candle in self._historical_minutes(
                future_key, from_day, to_day
            )
            if candle.time.date() < session_date
        ]
        spot_daily = [
            candle
            for candle in parse_candles(
                self._client.historical_candles(
                    NIFTY_INSTRUMENT_KEY,
                    from_day.isoformat(),
                    to_day.isoformat(),
                    unit="days",
                    interval=1,
                )
            )
            if candle.time.date() < session_date
        ]
        session = SessionInstruments(
            session_date=session_date,
            expiry_date=date.fromisoformat(resolved),
            future_instrument_key=future_key,
            atm_strike=strike,
            call_instrument_key=call_key,
            put_instrument_key=put_key,
            lot_size=lot_size,
            basis_option_keys=_basis_option_keys(rows, strike),
        )
        self._chain_rows = rows
        self._spot_minute_history = spot_minutes
        self._future_minute_history = future_minutes
        self._spot_daily_history = spot_daily
        self._spot_bars_today = []
        self._future_bars_today = []
        self._opening_straddle = None
        self._last_bar_success_at = None
        self._last_chain_poll = self._monotonic()
        self._last_chain_success_at = self._now_ist()
        self._session = session

    def _refresh_chain(self) -> None:
        if self._session is None:
            return
        chain = self._client.option_chain(
            NIFTY_INSTRUMENT_KEY, self._session.expiry_date.isoformat()
        )
        rows = _chain_rows(chain)
        if not rows:
            raise UpstoxDataError("option chain contains no usable rows")
        spot = _spot_from_chain(rows)
        strike, atm = _atm_row(rows, spot)
        call_key = atm["call_options"]["instrument_key"]
        put_key = atm["put_options"]["instrument_key"]
        lot_size = self._session.lot_size
        if (call_key, put_key) != (
            self._session.call_instrument_key,
            self._session.put_instrument_key,
        ):
            contracts = self._client.option_contracts(
                NIFTY_INSTRUMENT_KEY, self._session.expiry_date.isoformat()
            )
            lot_size = _validate_lot_size(contracts, call_key, put_key)
        session = SessionInstruments(
            session_date=self._session.session_date,
            expiry_date=self._session.expiry_date,
            future_instrument_key=self._session.future_instrument_key,
            atm_strike=strike,
            call_instrument_key=call_key,
            put_instrument_key=put_key,
            lot_size=lot_size,
            basis_option_keys=_basis_option_keys(rows, strike),
        )
        self._chain_rows = rows
        self._session = session
        self._last_chain_success_at = self._now_ist()

    def _refresh_intraday_bars(self) -> None:
        now = self._now_ist()
        current_minute = now.time().replace(second=0, microsecond=0)
        spot_payload = self._client.intraday_candles(
            NIFTY_INSTRUMENT_KEY, unit="minutes", interval=1
        )
        future_payload = self._client.intraday_candles(
            self._session.future_instrument_key, unit="minutes", interval=1
        )
        session_date = self._session.session_date
        market_open = now.replace(hour=9, minute=15, second=0, microsecond=0).time()
        spot_bars = [
            candle
            for candle in parse_candles(spot_payload)
            if candle.time.date() == session_date
            and market_open
            <= candle.time.time().replace(second=0, microsecond=0)
            < current_minute
        ]
        future_bars = [
            candle
            for candle in parse_candles(future_payload)
            if candle.time.date() == session_date
            and market_open
            <= candle.time.time().replace(second=0, microsecond=0)
            < current_minute
        ]
        if now.time() >= now.replace(hour=9, minute=16).time():
            for name, bars in (("spot", spot_bars), ("future", future_bars)):
                if not bars:
                    raise UpstoxDataError(f"no closed {name} intraday bars")
        self._spot_bars_today = spot_bars
        self._future_bars_today = future_bars
        self._last_bar_success_at = now

    def _maybe_capture_opening_straddle(self) -> None:
        if self._opening_straddle is not None or self._session is None:
            return
        now = self._now_ist()
        tod = now.time()
        open_t = now.replace(hour=9, minute=15, second=0, microsecond=0).time()
        close_t = now.replace(hour=9, minute=20, second=0, microsecond=0).time()
        if not (open_t <= tod < close_t):
            return
        call_mid = self._option_mid(self._session.call_instrument_key, "call_options")
        put_mid = self._option_mid(self._session.put_instrument_key, "put_options")
        if call_mid is not None and put_mid is not None:
            self._opening_straddle = call_mid + put_mid

    def _option_mid(self, instrument_key, side_name):
        quote = self._quotes_by_token.get(instrument_key)
        mid = _quote_top_mid(quote) if quote is not None else None
        if mid is None:
            market = (self._chain_side(side_name) or {}).get("market_data") or {}
            mid = _mid(market.get("bid_price"), market.get("ask_price"))
        return mid

    def _poll_quotes(self) -> None:
        keys = [
            NIFTY_INSTRUMENT_KEY,
            INDIA_VIX_INSTRUMENT_KEY,
            self._session.future_instrument_key,
            *self._session.basis_option_keys,
        ]
        deduped = list(dict.fromkeys(keys))
        quotes = self._client.market_quotes(deduped)
        by_token = {}
        if isinstance(quotes, dict):
            for value in quotes.values():
                if isinstance(value, dict) and value.get("instrument_token"):
                    by_token[value["instrument_token"]] = value
        self._quotes_by_token = by_token

    def _quote(self, key):
        return self._quotes_by_token.get(key)

    def _option_price(self, quote, chain_side):
        if quote is not None:
            price = quote.get("last_price")
            if price is not None:
                try:
                    return float(price)
                except (TypeError, ValueError):
                    pass
        market = (chain_side or {}).get("market_data") or {}
        ltp = market.get("ltp")
        if ltp is not None:
            try:
                return float(ltp)
            except (TypeError, ValueError):
                return None
        return None

    def _chain_side(self, option_type):
        for row in self._chain_rows:
            try:
                if float(row.get("strike_price")) == float(
                    self._session.atm_strike
                ):
                    return row.get(option_type)
            except (TypeError, ValueError):
                continue
        return None

    def _pcr(self):
        call_oi = 0.0
        put_oi = 0.0
        for row in self._chain_rows:
            for side_name, acc in (
                ("call_options", "call"),
                ("put_options", "put"),
            ):
                market = (row.get(side_name) or {}).get("market_data") or {}
                oi = market.get("oi")
                try:
                    value = float(oi)
                except (TypeError, ValueError):
                    continue
                if acc == "call":
                    call_oi += value
                else:
                    put_oi += value
        if call_oi <= 0:
            return None
        return put_oi / call_oi

    def _oi_wall(self, side_name):
        best = None
        for row in self._chain_rows:
            market = (row.get(side_name) or {}).get("market_data") or {}
            try:
                oi = float(market.get("oi"))
                strike = float(row.get("strike_price"))
            except (TypeError, ValueError):
                continue
            if best is None or oi > best[0]:
                best = (oi, strike)
        return best[1] if best is not None else None

    def _chain_window(self):
        rows = []
        for row in self._chain_rows:
            if not isinstance(row, dict):
                continue
            try:
                strike = float(row.get("strike_price"))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(strike):
                continue
            rows.append((abs(strike - self._session.atm_strike), strike, row))
        rows.sort(key=lambda item: (item[0], item[1]))
        window = []
        for _, strike, row in rows[:9]:
            call = row.get("call_options") or {}
            put = row.get("put_options") or {}
            call_greeks = call.get("option_greeks") or {}
            put_greeks = put.get("option_greeks") or {}
            call_market = call.get("market_data") or {}
            put_market = put.get("market_data") or {}
            call_quote = self._quotes_by_token.get(call.get("instrument_key"))
            put_quote = self._quotes_by_token.get(put.get("instrument_key"))
            ce_mid = (
                _quote_top_mid(call_quote) if call_quote is not None else None
            )
            if ce_mid is None:
                ce_mid = _mid(
                    call_market.get("bid_price"), call_market.get("ask_price")
                )
            pe_mid = (
                _quote_top_mid(put_quote) if put_quote is not None else None
            )
            if pe_mid is None:
                pe_mid = _mid(
                    put_market.get("bid_price"), put_market.get("ask_price")
                )
            window.append(
                {
                    "strike": strike,
                    "ce_mid": ce_mid,
                    "pe_mid": pe_mid,
                    "ce_oi": call_market.get("oi"),
                    "pe_oi": put_market.get("oi"),
                    "ce_iv": call_greeks.get("iv"),
                    "pe_iv": put_greeks.get("iv"),
                    "ce_delta": call_greeks.get("delta"),
                    "pe_delta": put_greeks.get("delta"),
                }
            )
        return window

    def _atm_spread(self):
        sides = []
        for key, side_name in (
            (self._session.call_instrument_key, "call_options"),
            (self._session.put_instrument_key, "put_options"),
        ):
            quote = self._quote(key)
            value = _quote_top_spread(quote) if quote is not None else None
            if value is None:
                value = _chain_side_spread(self._chain_side(side_name))
            if value is None:
                return None
            sides.append(value)
        return max(sides)

    def _source_age(self, now_ms):
        ages = []
        for key in (
            NIFTY_INSTRUMENT_KEY,
            INDIA_VIX_INSTRUMENT_KEY,
            self._session.future_instrument_key,
            self._session.call_instrument_key,
            self._session.put_instrument_key,
        ):
            quote = self._quote(key)
            if quote is None:
                return None
            stamp = _quote_timestamp_epoch_ms(quote)
            if stamp is None:
                return None
            ages.append(max(0.0, (now_ms - stamp) / 1000.0))
        return max(ages) if ages else None

    def _build_row(self, minute: datetime) -> MarketDataRow:
        session = self._session
        nifty_quote = self._quote(NIFTY_INSTRUMENT_KEY)
        vix_quote = self._quote(INDIA_VIX_INSTRUMENT_KEY)
        future_quote = self._quote(session.future_instrument_key)
        call_quote = self._quote(session.call_instrument_key)
        put_quote = self._quote(session.put_instrument_key)

        def price_of(quote):
            if quote is None:
                return None
            try:
                return float(quote.get("last_price"))
            except (TypeError, ValueError):
                return None

        nifty_price = price_of(nifty_quote)
        india_vix = price_of(vix_quote)
        future_price = price_of(future_quote)
        call_side = self._chain_side("call_options")
        put_side = self._chain_side("put_options")
        call_price = self._option_price(call_quote, call_side)
        put_price = self._option_price(put_quote, put_side)

        now = self._now_ist()
        now_ms = now.timestamp() * 1000.0
        age = self._source_age(now_ms)
        chain_age = None
        if self._last_chain_success_at is not None:
            chain_age = max(
                0.0,
                (now - self._last_chain_success_at).total_seconds(),
            )
        bar_age = None
        if self._last_bar_success_at is not None:
            bar_age = max(
                0.0, (now - self._last_bar_success_at).total_seconds()
            )
        spot_map = {bar.time: bar for bar in self._spot_bars_today}
        future_map = {bar.time: bar for bar in self._future_bars_today}
        common_times = sorted(set(spot_map) & set(future_map))
        if common_times:
            bar_time = common_times[-1]
            spot_bar = spot_map[bar_time]
            future_bar = future_map[bar_time]
        else:
            bar_time = None
            spot_bar = None
            future_bar = None

        stale = (
            nifty_price is None
            or india_vix is None
            or future_price is None
            or call_price is None
            or put_price is None
            or age is None
            or age > self._config.stale_after_seconds
            or chain_age is None
            or chain_age > self._config.chain_stale_after_seconds
        )
        bars_required = now.time() >= now.replace(hour=9, minute=16).time()
        if bars_required and (
            bar_age is None
            or bar_age > self._config.bar_stale_after_seconds
            or not self._spot_bars_today
            or not self._future_bars_today
            or bar_time is None
        ):
            stale = True

        inputs = FeatureInputs(
            timestamp=minute,
            spot_price=nifty_price,
            vix=india_vix,
            future_price=future_price,
            expiry_date=session.expiry_date,
            atm_strike=session.atm_strike,
            lot_size=session.lot_size,
            chain_rows=self._chain_rows,
            quotes_by_token=self._quotes_by_token,
            spot_bars_today=self._spot_bars_today,
            future_bars_today=self._future_bars_today,
            spot_minute_history=self._spot_minute_history,
            future_minute_history=self._future_minute_history,
            spot_daily_history=self._spot_daily_history,
            atm_iv_history=self._store.atm_iv_history(before=minute, limit=252),
            opening_straddle=self._opening_straddle,
            spread_ratio=self._atm_spread(),
            data_is_stale=stale,
        )
        frame = self._features.compute(inputs)
        kill_active = self._config.kill_switch_path.exists()
        eval_rows = self._store.evaluation_rows()
        daily = daily_user_net_pnl(eval_rows, now.date())
        candidate_action = {
            "BREAKOUT_UP": "LONG_CALL",
            "BREAKOUT_DOWN": "LONG_PUT",
        }.get(frame.opening_range_state)
        if candidate_action is not None:
            calibration = build_excursion_calibration(
                eval_rows, candidate_action
            )
        else:
            calibration = ExcursionCalibration("", 0, None, None)
        decision = self._risk.evaluate(
            frame,
            inputs,
            daily_net_pnl=daily.value,
            kill_switch_active=kill_active,
            expected_mfe_per_unit=calibration.mfe_median,
            calibrated_mae_per_unit=calibration.mae_p90,
            calibrated_mfe_per_unit=calibration.mfe_median,
            calibration_sample_size=calibration.sample_size,
            daily_pnl_available=daily.uncosted_trades == 0,
        )

        if stale:
            block_reason = "STALE_DATA"
        elif kill_active:
            block_reason = "KILL_SWITCH"
        else:
            block_reason = "SHADOW_MODE"

        compact = {"separators": (",", ":"), "sort_keys": True}
        candidate_json = (
            json.dumps(asdict(decision.candidate), **compact)
            if decision.candidate is not None
            else None
        )
        return MarketDataRow(
            time=minute,
            nifty_price=nifty_price,
            india_vix=india_vix,
            expiry_date=session.expiry_date,
            atm_strike=session.atm_strike,
            atm_call_instrument_key=session.call_instrument_key,
            atm_put_instrument_key=session.put_instrument_key,
            atm_call_price=call_price,
            atm_put_price=put_price,
            iv_percentile=frame.iv_percentile,
            pcr=frame.pcr,
            relative_volume=frame.relative_volume,
            vwap_position=frame.vwap_position,
            opening_range_state=frame.opening_range_state,
            call_oi_wall=frame.call_oi_walls[0][0] if frame.call_oi_walls else None,
            put_oi_wall=frame.put_oi_walls[0][0] if frame.put_oi_walls else None,
            spread=self._atm_spread(),
            source_age_seconds=age,
            chain_age_seconds=chain_age,
            data_is_stale=stale,
            trading_is_blocked=not decision.execution_allowed,
            block_reason=block_reason,
            bar_time=bar_time,
            spot_bar_open=spot_bar.open if spot_bar else None,
            spot_bar_high=spot_bar.high if spot_bar else None,
            spot_bar_low=spot_bar.low if spot_bar else None,
            spot_bar_close=spot_bar.close if spot_bar else None,
            future_bar_open=future_bar.open if future_bar else None,
            future_bar_high=future_bar.high if future_bar else None,
            future_bar_low=future_bar.low if future_bar else None,
            future_bar_close=future_bar.close if future_bar else None,
            future_bar_volume=future_bar.volume if future_bar else None,
            nifty_future_price=future_price,
            lot_size=session.lot_size,
            session_state=frame.session_state,
            is_expiry_day=frame.is_expiry_day,
            minutes_to_derivatives_close=frame.minutes_to_derivatives_close,
            synthetic_fwd_basis=frame.synthetic_fwd_basis,
            atm_iv=frame.atm_iv,
            atm_expected_move=frame.atm_expected_move,
            opening_straddle=frame.opening_straddle,
            expected_move_consumed_pct=frame.expected_move_consumed_pct,
            realized_vol_10d=frame.realized_vol_10d,
            vrp_ratio=frame.vrp_ratio,
            opening_range_high=frame.opening_range_high,
            opening_range_low=frame.opening_range_low,
            opening_range_width=frame.opening_range_width,
            narrow_range_threshold=frame.narrow_range_threshold,
            opening_range_is_narrow=frame.opening_range_is_narrow,
            relative_volume_spike=frame.relative_volume_spike,
            futures_vwap=frame.futures_vwap,
            vwap_sigma=frame.vwap_sigma,
            first_30m_return_pct=frame.first_30m_return_pct,
            call_oi_walls=json.dumps(
                [list(pair) for pair in frame.call_oi_walls], **compact
            ),
            put_oi_walls=json.dumps(
                [list(pair) for pair in frame.put_oi_walls], **compact
            ),
            local_gex=frame.local_gex,
            local_gex_sign=frame.local_gex_sign,
            momentum_reversion_selector=frame.momentum_reversion_selector,
            gate_reasons=json.dumps(list(decision.blockers), **compact),
            gate_warnings=json.dumps(list(decision.warnings), **compact),
            shadow_candidate=candidate_json,
            bar_age_seconds=bar_age,
            captured_at=now,
            chain_window=json.dumps(self._chain_window(), **compact),
            tod_median_30m_range=frame.tod_median_30m_range,
            daily_net_pnl=daily.value,
            daily_pnl_costed_trades=daily.costed_trades,
            daily_pnl_uncosted_trades=daily.uncosted_trades,
            expected_mfe_per_unit=calibration.mfe_median,
            calibration_sample_size=calibration.sample_size,
            calibrated_mae_p90=calibration.mae_p90,
        )


def _emit(stream, payload) -> None:
    print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), file=stream)


def _row_payload(row: MarketDataRow):
    payload = {
        "time": row.time.isoformat(),
        "expiry_date": row.expiry_date.isoformat(),
        "bar_time": row.bar_time.isoformat() if row.bar_time else None,
        "captured_at": row.captured_at.isoformat() if row.captured_at else None,
        "chain_window": json.loads(row.chain_window)
        if row.chain_window
        else None,
        "atm_strike": row.atm_strike,
        "atm_call_instrument_key": row.atm_call_instrument_key,
        "atm_put_instrument_key": row.atm_put_instrument_key,
        "lot_size": row.lot_size,
        "nifty_price": row.nifty_price,
        "india_vix": row.india_vix,
        "nifty_future_price": row.nifty_future_price,
        "atm_call_price": row.atm_call_price,
        "atm_put_price": row.atm_put_price,
        "session_state": row.session_state,
        "is_expiry_day": row.is_expiry_day,
        "minutes_to_derivatives_close": row.minutes_to_derivatives_close,
        "synthetic_fwd_basis": row.synthetic_fwd_basis,
        "atm_iv": row.atm_iv,
        "atm_expected_move": row.atm_expected_move,
        "opening_straddle": row.opening_straddle,
        "expected_move_consumed_pct": row.expected_move_consumed_pct,
        "iv_percentile": row.iv_percentile,
        "realized_vol_10d": row.realized_vol_10d,
        "vrp_ratio": row.vrp_ratio,
        "opening_range_high": row.opening_range_high,
        "opening_range_low": row.opening_range_low,
        "opening_range_width": row.opening_range_width,
        "narrow_range_threshold": row.narrow_range_threshold,
        "opening_range_is_narrow": row.opening_range_is_narrow,
        "opening_range_state": row.opening_range_state,
        "relative_volume": row.relative_volume,
        "relative_volume_spike": row.relative_volume_spike,
        "futures_vwap": row.futures_vwap,
        "vwap_position": row.vwap_position,
        "vwap_sigma": row.vwap_sigma,
        "first_30m_return_pct": row.first_30m_return_pct,
        "pcr": row.pcr,
        "call_oi_wall": row.call_oi_wall,
        "put_oi_wall": row.put_oi_wall,
        "call_oi_walls": json.loads(row.call_oi_walls) if row.call_oi_walls else None,
        "put_oi_walls": json.loads(row.put_oi_walls) if row.put_oi_walls else None,
        "local_gex": row.local_gex,
        "local_gex_sign": row.local_gex_sign,
        "momentum_reversion_selector": row.momentum_reversion_selector,
        "spread": row.spread,
        "source_age_seconds": row.source_age_seconds,
        "chain_age_seconds": row.chain_age_seconds,
        "bar_age_seconds": row.bar_age_seconds,
        "data_is_stale": row.data_is_stale,
        "trading_is_blocked": row.trading_is_blocked,
        "block_reason": row.block_reason,
        "gate_reasons": json.loads(row.gate_reasons) if row.gate_reasons else None,
        "gate_warnings": json.loads(row.gate_warnings) if row.gate_warnings else None,
        "shadow_candidate": json.loads(row.shadow_candidate)
        if row.shadow_candidate
        else None,
        "tod_median_30m_range": row.tod_median_30m_range,
        "daily_net_pnl": row.daily_net_pnl,
        "daily_pnl_costed_trades": row.daily_pnl_costed_trades,
        "daily_pnl_uncosted_trades": row.daily_pnl_uncosted_trades,
        "expected_mfe_per_unit": row.expected_mfe_per_unit,
        "calibration_sample_size": row.calibration_sample_size,
        "calibrated_mae_p90": row.calibrated_mae_p90,
    }
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot.collector",
        description="Collect normalized NIFTY market data into DuckDB",
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--db-path", type=Path, default=Path("data/trading_bot.duckdb"))
    parser.add_argument("--quote-interval-seconds", type=float, default=5.0)
    parser.add_argument("--chain-interval-seconds", type=float, default=30.0)
    parser.add_argument("--stale-after-seconds", type=float, default=15.0)
    parser.add_argument("--chain-stale-after-seconds", type=float, default=90.0)
    parser.add_argument("--bar-stale-after-seconds", type=float, default=120.0)
    parser.add_argument("--historical-calendar-days", type=int, default=45)
    parser.add_argument("--kill-switch-path", type=Path, default=Path("data/KILL_SWITCH"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--enable-openai-advisory",
        dest="enable_advisory",
        action="store_true",
        help=(
            "enable the optional standalone OpenAI advisory adapter "
            "(the harness-native trading_bot.agent_tool is preferred)"
        ),
    )
    parser.add_argument(
        "--enable-advisory",
        dest="enable_advisory",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--advisory-output", choices=("json", "text"), default="text"
    )
    parser.add_argument("--no-auto-settle", action="store_true")
    return parser


def run(
    argv=None,
    *,
    upstox_client_factory=UpstoxClient.from_env,
    advice_client_factory=OpenAIResponsesClient.from_env,
) -> int:
    args = build_parser().parse_args(argv)
    if args.quote_interval_seconds <= 0:
        _emit(sys.stderr, {"ok": False, "error": "quote-interval-seconds must be > 0"})
        return 2
    if args.chain_interval_seconds <= 0:
        _emit(sys.stderr, {"ok": False, "error": "chain-interval-seconds must be > 0"})
        return 2
    if args.stale_after_seconds <= 0:
        _emit(sys.stderr, {"ok": False, "error": "stale-after-seconds must be > 0"})
        return 2
    if args.chain_stale_after_seconds <= 0:
        _emit(
            sys.stderr,
            {"ok": False, "error": "chain-stale-after-seconds must be > 0"},
        )
        return 2
    if args.bar_stale_after_seconds <= 0:
        _emit(
            sys.stderr,
            {"ok": False, "error": "bar-stale-after-seconds must be > 0"},
        )
        return 2
    if args.historical_calendar_days <= 0:
        _emit(
            sys.stderr,
            {"ok": False, "error": "historical-calendar-days must be > 0"},
        )
        return 2
    config = CollectorConfig(
        db_path=args.db_path,
        quote_interval_seconds=args.quote_interval_seconds,
        chain_interval_seconds=args.chain_interval_seconds,
        stale_after_seconds=args.stale_after_seconds,
        chain_stale_after_seconds=args.chain_stale_after_seconds,
        bar_stale_after_seconds=args.bar_stale_after_seconds,
        historical_calendar_days=args.historical_calendar_days,
        kill_switch_path=args.kill_switch_path,
        env_file=args.env_file,
    )
    try:
        load_env_file(config.env_file)
        client = upstox_client_factory()
        advice_client = None
        if args.enable_advisory:
            load_env_file(
                config.env_file,
                names=("OPENAI_API_KEY", "TRADING_BOT_LLM_MODEL"),
            )
            advice_client = advice_client_factory()
        with DuckDBStore(config.db_path) as store:
            collector = MarketDataCollector(client, store, config)
            advice_service = (
                AdviceService(store, advice_client)
                if advice_client is not None
                else None
            )
            feedback_service = (
                FeedbackService(store, client)
                if advice_client is not None and not args.no_auto_settle
                else None
            )

            def handle_row(row):
                _emit(sys.stdout, {"ok": True, "row": _row_payload(row)})
                if advice_service is not None:
                    result = advice_service.run_once()
                    if result.status != "SKIPPED":
                        if args.advisory_output == "text":
                            print(
                                format_shadow_alert(result), file=sys.stdout
                            )
                        else:
                            _emit(
                                sys.stdout,
                                {
                                    "ok": True,
                                    "event": "shadow_advice",
                                    **advice_payload(result),
                                },
                            )
                if feedback_service is not None:
                    batch = feedback_service.settle_pending()
                    if not batch.settled and not batch.failures:
                        return
                    if args.advisory_output == "text":
                        print(
                            f"Settled shadow outcomes: {len(batch.settled)}",
                            file=sys.stdout,
                        )
                        if batch.failures:
                            _emit(
                                sys.stderr,
                                {
                                    "ok": False,
                                    "event": "shadow_settlement_failure",
                                    "failures": [
                                        asdict(failure)
                                        for failure in batch.failures
                                    ],
                                },
                            )
                    else:
                        _emit(
                            sys.stdout,
                            {
                                "ok": True,
                                "event": "shadow_settlement",
                                "settled": [
                                    feedback_payload(r)
                                    for r in batch.settled
                                ],
                                "failures": [
                                    asdict(failure)
                                    for failure in batch.failures
                                ],
                            },
                        )

            if args.once:
                handle_row(collector.run_once())
            else:
                collector.run_forever(
                    on_row=handle_row,
                    on_error=lambda error: _emit(
                        sys.stderr,
                        {
                            "ok": False,
                            "recovering": True,
                            "error": {
                                "type": type(error).__name__,
                                "message": str(error),
                            },
                        },
                    ),
                )
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        _emit(
            sys.stderr,
            {"ok": False, "error": {"type": type(error).__name__, "message": str(error)}},
        )
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
