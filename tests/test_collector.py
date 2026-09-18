import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from trading_bot.collector import (
    INDIA_VIX_INSTRUMENT_KEY,
    IST,
    CollectorConfig,
    MarketDataCollector,
)
from trading_bot.storage import MarketDataRow
from trading_bot.upstox.client import (
    NIFTY_INSTRUMENT_KEY,
    UpstoxDataError,
    UpstoxTransportError,
)

NOW = datetime(2026, 9, 22, 9, 20, 30, tzinfo=IST)
NOW_MS = NOW.timestamp() * 1000.0


def chain_rows(call_oi_24000=500, put_oi_24000=700, ce="NSE_FO|C24000", pe="NSE_FO|P24000"):
    return [
        {
            "strike_price": 23900.0,
            "underlying_spot_price": 24010.0,
            "call_options": {
                "instrument_key": "NSE_FO|C23900",
                "market_data": {
                    "ltp": 150.0,
                    "oi": 300,
                    "bid_price": 149.0,
                    "ask_price": 151.0,
                },
                "option_greeks": {},
            },
            "put_options": {
                "instrument_key": "NSE_FO|P23900",
                "market_data": {
                    "ltp": 40.0,
                    "oi": 500,
                    "bid_price": 39.0,
                    "ask_price": 41.0,
                },
                "option_greeks": {},
            },
        },
        {
            "strike_price": 24000.0,
            "underlying_spot_price": 24010.0,
            "call_options": {
                "instrument_key": ce,
                "market_data": {
                    "ltp": 100.0,
                    "oi": call_oi_24000,
                    "bid_price": 99.0,
                    "ask_price": 101.0,
                },
                "option_greeks": {},
            },
            "put_options": {
                "instrument_key": pe,
                "market_data": {
                    "ltp": 90.0,
                    "oi": put_oi_24000,
                    "bid_price": 89.0,
                    "ask_price": 91.0,
                },
                "option_greeks": {},
            },
        },
        {
            "strike_price": 24100.0,
            "underlying_spot_price": 24010.0,
            "call_options": {
                "instrument_key": "NSE_FO|C24100",
                "market_data": {"ltp": 60.0, "oi": 900, "bid_price": 59.0, "ask_price": 61.0},
                "option_greeks": {},
            },
            "put_options": {
                "instrument_key": "NSE_FO|P24100",
                "market_data": {"ltp": 140.0, "oi": 100, "bid_price": 139.0, "ask_price": 141.0},
                "option_greeks": {},
            },
        },
    ]


def search_rows():
    return [
        {"instrument_type": "CE", "trading_symbol": "NIFTY FUT X", "expiry": "2026-09-22", "instrument_key": "NSE_FO|BAD1"},
        {"instrument_type": "FUT", "trading_symbol": "BANKNIFTY FUT X", "expiry": "2026-09-22", "instrument_key": "NSE_FO|BAD2"},
        {"instrument_type": "FUT", "trading_symbol": "NIFTY FUT SEP", "expiry": "2026-08-25", "instrument_key": "NSE_FO|EXPIRED"},
        {"instrument_type": "FUT", "trading_symbol": "NIFTY FUT SEP", "expiry": "2026-09-29", "instrument_key": "NSE_FO|FUT_NEAR"},
        {"instrument_type": "FUT", "trading_symbol": "NIFTY FUT OCT", "expiry": "2026-10-27", "instrument_key": "NSE_FO|FUT_FAR"},
    ]


def quotes(now_ms=NOW_MS, ce="NSE_FO|C24000", pe="NSE_FO|P24000"):
    return {
        "NSE_INDEX:Nifty 50": {
            "instrument_token": NIFTY_INSTRUMENT_KEY,
            "last_price": 24005.0,
            "last_trade_time": str(int(now_ms - 1000)),
        },
        "NSE_INDEX:India VIX": {
            "instrument_token": INDIA_VIX_INSTRUMENT_KEY,
            "last_price": 13.5,
            "last_trade_time": str(int(now_ms - 1000)),
        },
        "NSE_FO:FUT_NEAR": {
            "instrument_token": "NSE_FO|FUT_NEAR",
            "last_price": 24050.0,
            "last_trade_time": str(int(now_ms - 1000)),
        },
        "NSE_FO:CE_DISPLAY": {
            "instrument_token": ce,
            "last_price": 101.0,
            "last_trade_time": str(int(now_ms - 1000)),
            "depth": {"buy": [{"price": 100.0}], "sell": [{"price": 102.0}]},
        },
        "NSE_FO:PE_DISPLAY": {
            "instrument_token": pe,
            "last_price": 91.0,
            "last_trade_time": str(int(now_ms - 1000)),
            "depth": {"buy": [{"price": 89.0}], "sell": [{"price": 93.0}]},
        },
    }


def contract_rows(ce="NSE_FO|C24000", pe="NSE_FO|P24000", lot=65):
    return [
        {"instrument_key": ce, "instrument_type": "CE", "lot_size": lot},
        {"instrument_key": pe, "instrument_type": "PE", "lot_size": lot},
    ]


def intraday_payload(day=date(2026, 9, 22)):
    prefix = day.isoformat()
    return {
        "candles": [
            [f"{prefix}T09:15:00+05:30", 24000.0, 24020.0, 23990.0, 24010.0, 1000.0, 0],
            [f"{prefix}T09:19:00+05:30", 24010.0, 24030.0, 24000.0, 24025.0, 800.0, 0],
        ]
    }


class FakeClient:
    def __init__(self, chains=None, quote_sets=None, searches=None, resolves=None,
                 contracts=None, histories=None, intradays=None):
        self.chains = list(chains if chains is not None else [chain_rows()])
        self.quote_sets = list(quote_sets if quote_sets is not None else [quotes()])
        self.searches = list(searches if searches is not None else [search_rows()])
        self.resolves = list(resolves if resolves is not None else ["2026-09-22"])
        self.contracts = list(contracts if contracts is not None else [contract_rows()])
        self.histories = list(histories if histories is not None else [{"candles": []}])
        self.intradays = list(intradays if intradays is not None else [intraday_payload()])
        self.calls = []
        self.quote_requests = []

    def _next(self, queue):
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item

    def resolve_expiry(self, key, expiry, *, as_of=None):
        self.calls.append(("resolve_expiry", key, expiry, as_of))
        return self._next(self.resolves)

    def option_chain(self, key, expiry):
        self.calls.append(("option_chain", key, expiry))
        return self._next(self.chains)

    def search_instruments(self, query, **kwargs):
        self.calls.append(("search_instruments", query, kwargs))
        return self._next(self.searches)

    def market_quotes(self, keys):
        self.calls.append(("market_quotes", list(keys)))
        self.quote_requests.append(list(keys))
        return self._next(self.quote_sets)

    def option_contracts(self, key, expiry):
        self.calls.append(("option_contracts", key, expiry))
        return self._next(self.contracts)

    def historical_candles(self, key, from_date, to_date, unit="minutes", interval=1):
        self.calls.append(("historical_candles", key, unit, from_date, to_date))
        item = self._next(self.histories)
        return item() if callable(item) else item

    def intraday_candles(self, key, unit="minutes", interval=1):
        self.calls.append(("intraday_candles", key, unit))
        item = self._next(self.intradays)
        return item() if callable(item) else item


class FakeStore:
    def __init__(self):
        self.rows = []

    def upsert_market_data(self, row):
        self.rows.append(row)

    def atm_iv_history(self, before, limit=252):
        return []

    def evaluation_rows(self):
        return []


class FakeClock:
    def __init__(self, now=NOW):
        self.now = now
        self.monotonic = 0.0
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.monotonic += seconds


def make_collector(client=None, store=None, clock=None, **config_kw):
    client = client or FakeClient()
    store = store or FakeStore()
    clock = clock or FakeClock()
    collector = MarketDataCollector(
        client,
        store,
        CollectorConfig(**config_kw),
        now=lambda: clock.now,
        monotonic=lambda: clock.monotonic,
        sleep=clock.sleep,
    )
    return collector, client, store, clock


class CollectorTests(unittest.TestCase):
    def test_run_once_builds_row(self):
        collector, client, store, clock = make_collector()
        row = collector.run_once()
        self.assertIsInstance(row, MarketDataRow)
        self.assertEqual(row.time, NOW.replace(second=0, microsecond=0))
        self.assertEqual(row.expiry_date, date(2026, 9, 22))
        self.assertEqual(row.nifty_price, 24005.0)
        self.assertEqual(row.india_vix, 13.5)
        self.assertEqual(row.atm_strike, 24000.0)
        self.assertEqual(row.atm_call_instrument_key, "NSE_FO|C24000")
        self.assertEqual(row.atm_put_instrument_key, "NSE_FO|P24000")
        self.assertEqual(row.atm_call_price, 101.0)
        self.assertEqual(row.atm_put_price, 91.0)
        self.assertAlmostEqual(row.pcr, 1300.0 / 1700.0)
        self.assertEqual(row.call_oi_wall, 24100.0)
        self.assertEqual(row.put_oi_wall, 24000.0)
        self.assertAlmostEqual(row.spread, (93.0 - 89.0) / 91.0)
        self.assertAlmostEqual(row.source_age_seconds, 1.0)
        self.assertFalse(row.data_is_stale)
        self.assertTrue(row.trading_is_blocked)
        self.assertEqual(row.block_reason, "SHADOW_MODE")
        self.assertEqual(len(store.rows), 1)

    def test_session_uses_resolved_expiry_and_nearest_future(self):
        collector, client, store, clock = make_collector()
        collector.run_once()
        resolve_calls = [c for c in client.calls if c[0] == "resolve_expiry"]
        self.assertEqual(resolve_calls[0][3], date(2026, 9, 22))
        chain_calls = [c for c in client.calls if c[0] == "option_chain"]
        self.assertEqual(chain_calls[0][2], "2026-09-22")
        self.assertIn("NSE_FO|FUT_NEAR", client.quote_requests[0])
        search_calls = [c for c in client.calls if c[0] == "search_instruments"]
        self.assertEqual(search_calls[0][1], "NIFTY FUT")
        self.assertEqual(search_calls[0][2], {"records": 30})

    def test_quotes_mapped_by_instrument_token(self):
        weird = quotes()
        weird["ZZZ:nifty"] = weird.pop("NSE_INDEX:Nifty 50")
        client = FakeClient(quote_sets=[weird])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertEqual(row.nifty_price, 24005.0)
        self.assertFalse(row.data_is_stale)

    def test_option_price_falls_back_to_chain_ltp(self):
        q = quotes()
        del q["NSE_FO:CE_DISPLAY"]["last_price"]
        del q["NSE_FO:PE_DISPLAY"]["last_price"]
        client = FakeClient(quote_sets=[q])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertEqual(row.atm_call_price, 100.0)
        self.assertEqual(row.atm_put_price, 90.0)

    def test_spread_falls_back_to_chain_bid_ask(self):
        q = quotes()
        del q["NSE_FO:CE_DISPLAY"]["depth"]
        del q["NSE_FO:PE_DISPLAY"]["depth"]
        client = FakeClient(quote_sets=[q])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertAlmostEqual(row.spread, (91.0 - 89.0) / 90.0)

    def test_stale_when_quote_missing(self):
        q = quotes()
        del q["NSE_INDEX:India VIX"]
        client = FakeClient(quote_sets=[q])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertTrue(row.data_is_stale)
        self.assertEqual(row.block_reason, "STALE_DATA")

    def test_stale_when_timestamp_old_or_missing(self):
        old = quotes(now_ms=NOW_MS - 60_000)
        client = FakeClient(quote_sets=[old])
        collector, client, store, clock = make_collector(
            client=client, stale_after_seconds=15.0
        )
        row = collector.run_once()
        self.assertTrue(row.data_is_stale)
        self.assertEqual(row.source_age_seconds, 61.0)

        no_ts = quotes()
        for v in no_ts.values():
            del v["last_trade_time"]
        client2 = FakeClient(quote_sets=[no_ts])
        collector2, _, _, _ = make_collector(client=client2)
        row2 = collector2.run_once()
        self.assertTrue(row2.data_is_stale)
        self.assertIsNone(row2.source_age_seconds)

    def test_timestamp_iso_fallback_and_clamp(self):
        q = quotes()
        for v in q.values():
            v["timestamp"] = "2026-09-22T09:20:29+05:30"
            del v["last_trade_time"]
        client = FakeClient(quote_sets=[q])
        collector, _, _, _ = make_collector(client=client)
        row = collector.run_once()
        self.assertAlmostEqual(row.source_age_seconds, 1.0)

        future = quotes(now_ms=NOW_MS + 120_000)
        client2 = FakeClient(quote_sets=[future])
        collector2, _, _, _ = make_collector(client=client2)
        row2 = collector2.run_once()
        self.assertEqual(row2.source_age_seconds, 0.0)
        self.assertFalse(row2.data_is_stale)

    def test_session_refresh_on_new_day(self):
        clock = FakeClock()
        client = FakeClient(
            intradays=[lambda: intraday_payload(clock.now.date())]
        )
        collector, client, store, clock = make_collector(client=client, clock=clock)
        collector.run_once()
        clock.now = NOW + timedelta(days=1)
        collector.run_once()
        resolve_calls = [c for c in client.calls if c[0] == "resolve_expiry"]
        self.assertEqual(len(resolve_calls), 2)
        self.assertEqual(resolve_calls[1][3], date(2026, 9, 23))

    def test_run_forever_one_row_per_minute_and_atm_refresh(self):
        second_chain = chain_rows(ce="NSE_FO|C24100", pe="NSE_FO|P24100")
        second_chain[1]["strike_price"] = 24050.0
        second_chain[1]["call_options"]["instrument_key"] = "NSE_FO|C24050"
        second_chain[1]["put_options"]["instrument_key"] = "NSE_FO|P24050"
        q2 = quotes(ce="NSE_FO|C24050", pe="NSE_FO|P24050")
        client = FakeClient(
            chains=[chain_rows(), second_chain],
            quote_sets=[quotes(), q2, q2, q2],
            contracts=[
                contract_rows(),
                contract_rows("NSE_FO|C24050", "NSE_FO|P24050"),
            ],
        )
        clock = FakeClock()
        store = FakeStore()

        class StopLoop(Exception):
            pass

        sleeps = []

        def sleep(s):
            sleeps.append(s)
            clock.monotonic += s
            if len(sleeps) == 2:
                clock.now = NOW + timedelta(minutes=1)
            if len(sleeps) >= 3:
                raise StopLoop

        collector = MarketDataCollector(
            client,
            store,
            CollectorConfig(quote_interval_seconds=5.0, chain_interval_seconds=10.0),
            now=lambda: clock.now,
            monotonic=lambda: clock.monotonic,
            sleep=sleep,
        )
        with self.assertRaises(StopLoop):
            collector.run_forever()
        self.assertEqual(len(store.rows), 2)
        self.assertEqual(store.rows[0].time.minute, 20)
        self.assertEqual(store.rows[1].time.minute, 21)
        self.assertIn("NSE_FO|C24050", client.quote_requests[-1])

    def test_missing_prices_stay_none_and_stale(self):
        q = quotes()
        del q["NSE_INDEX:Nifty 50"]
        q["NSE_FO:CE_DISPLAY"]["last_price"] = None
        client = FakeClient(quote_sets=[q])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertIsNone(row.nifty_price)
        self.assertEqual(row.atm_call_price, 100.0)
        self.assertTrue(row.data_is_stale)
        self.assertEqual(row.block_reason, "STALE_DATA")

    def test_spread_none_when_one_side_invalid(self):
        q = quotes()
        del q["NSE_FO:PE_DISPLAY"]["depth"]
        broken_chain = chain_rows()
        broken_chain[1]["put_options"]["market_data"]["bid_price"] = 0
        broken_chain[1]["put_options"]["market_data"]["ask_price"] = 0
        client = FakeClient(chains=[broken_chain], quote_sets=[q])
        collector, _, _, _ = make_collector(client=client)
        row = collector.run_once()
        self.assertIsNone(row.spread)


class CollectorRecoveryTests(unittest.TestCase):
    def _run_until_stop(self, collector, store, errors, clock, stop_after_sleeps, now_steps=None):
        class StopLoop(Exception):
            pass

        sleeps = []

        def sleep(s):
            sleeps.append(s)
            clock.monotonic += s
            if now_steps and len(sleeps) in now_steps:
                clock.now = now_steps[len(sleeps)]
            if len(sleeps) >= stop_after_sleeps:
                raise StopLoop

        collector._sleep = sleep
        with self.assertRaises(StopLoop):
            collector.run_forever(
                on_row=lambda row: None, on_error=errors.append
            )
        return sleeps

    def test_initial_discovery_error_retries(self):
        client = FakeClient(
            resolves=[UpstoxTransportError("boom"), "2026-09-22"]
        )
        collector, client, store, clock = make_collector(client=client)
        errors = []
        self._run_until_stop(collector, store, errors, clock, 2)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], UpstoxTransportError)
        self.assertEqual(len(store.rows), 1)

    def test_quote_error_retains_quotes_then_stale(self):
        client = FakeClient(
            quote_sets=[quotes(), UpstoxTransportError("net down"), quotes()]
        )
        clock = FakeClock()
        store = FakeStore()
        collector = MarketDataCollector(
            client,
            store,
            CollectorConfig(quote_interval_seconds=5.0),
            now=lambda: clock.now,
            monotonic=lambda: clock.monotonic,
            sleep=lambda s: None,
        )
        errors = []
        self._run_until_stop(
            collector, store, errors, clock, 2,
            now_steps={1: NOW + timedelta(seconds=60)},
        )
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(store.rows), 2)
        self.assertFalse(store.rows[0].data_is_stale)
        self.assertTrue(store.rows[1].data_is_stale)
        self.assertGreater(store.rows[1].source_age_seconds, 15.0)

    def test_chain_error_retains_chain_and_ages_out(self):
        client = FakeClient(
            chains=[chain_rows(), UpstoxTransportError("chain fail")],
        )
        clock = FakeClock()
        store = FakeStore()
        collector = MarketDataCollector(
            client,
            store,
            CollectorConfig(
                quote_interval_seconds=5.0,
                chain_interval_seconds=10.0,
                stale_after_seconds=3600.0,
                chain_stale_after_seconds=30.0,
            ),
            now=lambda: clock.now,
            monotonic=lambda: clock.monotonic,
            sleep=lambda s: None,
        )
        errors = []
        self._run_until_stop(
            collector, store, errors, clock, 3,
            now_steps={1: NOW + timedelta(minutes=1, seconds=45)},
        )
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], UpstoxTransportError)
        self.assertEqual(len(store.rows), 2)
        self.assertAlmostEqual(store.rows[0].chain_age_seconds, 0.0)
        self.assertFalse(store.rows[0].data_is_stale)
        self.assertAlmostEqual(store.rows[1].chain_age_seconds, 105.0)
        self.assertTrue(store.rows[1].data_is_stale)
        self.assertEqual(store.rows[1].block_reason, "STALE_DATA")

    def test_empty_chain_refresh_preserves_state_and_ages_stale(self):
        client = FakeClient(chains=[chain_rows(), []])
        clock = FakeClock()
        store = FakeStore()
        collector = MarketDataCollector(
            client,
            store,
            CollectorConfig(
                quote_interval_seconds=5.0,
                chain_interval_seconds=10.0,
                stale_after_seconds=3600.0,
                chain_stale_after_seconds=30.0,
            ),
            now=lambda: clock.now,
            monotonic=lambda: clock.monotonic,
            sleep=lambda s: None,
        )
        errors = []
        self._run_until_stop(
            collector, store, errors, clock, 3,
            now_steps={1: NOW + timedelta(minutes=1, seconds=45)},
        )
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], UpstoxDataError)
        self.assertEqual(len(store.rows), 2)
        self.assertEqual(store.rows[0].atm_strike, 24000.0)
        self.assertEqual(store.rows[1].atm_strike, 24000.0)
        self.assertAlmostEqual(store.rows[1].chain_age_seconds, 105.0)
        self.assertTrue(store.rows[1].data_is_stale)
        self.assertEqual(store.rows[1].block_reason, "STALE_DATA")
        self.assertIn("NSE_FO|C24000", client.quote_requests[-1])

    def test_failed_future_discovery_leaves_clean_state(self):
        client = FakeClient(searches=[[]])
        collector, client, store, clock = make_collector(client=client)
        with self.assertRaises(UpstoxDataError):
            collector.run_once()
        self.assertIsNone(collector._session)
        self.assertEqual(collector._chain_rows, [])
        self.assertIsNone(collector._last_chain_success_at)

    def test_run_forever_after_run_once(self):
        collector, client, store, clock = make_collector()
        collector.run_once()
        self.assertIsNotNone(collector._last_chain_poll)

        class StopLoop(Exception):
            pass

        def sleep(s):
            clock.monotonic += s
            raise StopLoop

        collector._sleep = sleep
        with self.assertRaises(StopLoop):
            collector.run_forever()
        self.assertGreaterEqual(len(client.quote_requests), 2)

    def test_row_written_under_post_request_minute(self):
        client = FakeClient()
        clock = FakeClock()
        store = FakeStore()
        now_calls = [
            datetime(2026, 9, 22, 9, 20, 59, tzinfo=IST),
        ]

        def now():
            if now_calls:
                return now_calls.pop(0)
            return datetime(2026, 9, 22, 9, 21, 35, tzinfo=IST)

        class StopLoop(Exception):
            pass

        collector = MarketDataCollector(
            client,
            store,
            CollectorConfig(quote_interval_seconds=5.0),
            now=now,
            monotonic=lambda: clock.monotonic,
            sleep=lambda s: (_ for _ in ()).throw(StopLoop),
        )
        with self.assertRaises(StopLoop):
            collector.run_forever()
        self.assertEqual(len(store.rows), 1)
        self.assertEqual(store.rows[0].time.minute, 21)

    def test_unexpected_error_propagates(self):
        client = FakeClient(quote_sets=[quotes(), RuntimeError("bug")])
        clock = FakeClock()
        store = FakeStore()
        collector = MarketDataCollector(
            client,
            store,
            CollectorConfig(quote_interval_seconds=5.0),
            now=lambda: clock.now,
            monotonic=lambda: clock.monotonic,
            sleep=lambda s: setattr(clock, "monotonic", clock.monotonic + s),
        )
        with self.assertRaises(RuntimeError):
            collector.run_forever()


class CollectorIntegrationTests(unittest.TestCase):
    def test_dynamic_lot_size_stored(self):
        client = FakeClient(contracts=[contract_rows(lot=65)])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertEqual(row.lot_size, 65)

        client75 = FakeClient(contracts=[contract_rows(lot=75)])
        collector75, _, _, _ = make_collector(client=client75)
        row75 = collector75.run_once()
        self.assertEqual(row75.lot_size, 75)

    def test_mismatched_or_missing_lot_size_fails_atomically(self):
        bad = contract_rows()
        bad[1]["lot_size"] = 75
        client = FakeClient(contracts=[bad])
        collector, client, store, clock = make_collector(client=client)
        with self.assertRaises(UpstoxDataError):
            collector.run_once()
        self.assertIsNone(collector._session)
        self.assertEqual(collector._chain_rows, [])

        client2 = FakeClient(contracts=[[]])
        collector2, _, _, _ = make_collector(client=client2)
        with self.assertRaises(UpstoxDataError):
            collector2.run_once()
        self.assertIsNone(collector2._session)

    def test_basis_option_keys_quoted_and_follow_atm(self):
        collector, client, store, clock = make_collector()
        collector.run_once()
        first = client.quote_requests[0]
        for key in (
            "NSE_FO|C23900", "NSE_FO|P23900", "NSE_FO|C24000",
            "NSE_FO|P24000", "NSE_FO|C24100", "NSE_FO|P24100",
        ):
            self.assertIn(key, first)
        self.assertEqual(
            collector._session.basis_option_keys,
            (
                "NSE_FO|C23900", "NSE_FO|P23900",
                "NSE_FO|C24000", "NSE_FO|P24000",
                "NSE_FO|C24100", "NSE_FO|P24100",
            ),
        )

    def test_history_fetched_once_per_session(self):
        collector, client, store, clock = make_collector()
        collector.run_once()
        collector.run_once()
        history_calls = [c for c in client.calls if c[0] == "historical_candles"]
        self.assertEqual(len(history_calls), 5)
        nifty_minutes = [
            c for c in history_calls
            if c[1] == NIFTY_INSTRUMENT_KEY and c[2] == "minutes"
        ]
        future_minutes = [
            c for c in history_calls
            if c[1] == "NSE_FO|FUT_NEAR" and c[2] == "minutes"
        ]
        daily = [c for c in history_calls if c[2] == "days"]
        expected_chunks = [
            ("2026-08-08", "2026-09-05"),
            ("2026-09-06", "2026-09-21"),
        ]
        self.assertEqual(
            [(c[3], c[4]) for c in nifty_minutes], expected_chunks
        )
        self.assertEqual(
            [(c[3], c[4]) for c in future_minutes], expected_chunks
        )
        self.assertEqual(len(daily), 1)
        self.assertEqual((daily[0][3], daily[0][4]), ("2026-08-08", "2026-09-21"))

    def test_historical_minutes_chunking_and_dedupe(self):
        client = FakeClient()
        collector, _, _, _ = make_collector(client=client)
        self.assertEqual(
            collector._historical_minutes("K", date(2026, 9, 10), date(2026, 9, 5)),
            [],
        )
        calls = lambda: [
            c for c in client.calls if c[0] == "historical_candles"
        ]
        collector._historical_minutes("K", date(2026, 9, 5), date(2026, 9, 5))
        collector._historical_minutes("K", date(2026, 8, 8), date(2026, 9, 5))
        collector._historical_minutes("K", date(2026, 8, 8), date(2026, 9, 6))
        ranges = [(c[3], c[4]) for c in calls()]
        self.assertEqual(
            ranges,
            [
                ("2026-09-05", "2026-09-05"),
                ("2026-08-08", "2026-09-05"),
                ("2026-08-08", "2026-09-05"),
                ("2026-09-06", "2026-09-06"),
            ],
        )

        payloads = [
            {"candles": [
                ["2026-09-05T10:00:00+05:30", 1.0, 2.0, 0.5, 1.5, 10.0, 0],
                ["2026-08-10T10:00:00+05:30", 3.0, 4.0, 2.5, 3.5, 20.0, 0],
                ["2026-08-10T10:00:00+05:30", 9.0, 9.0, 9.0, 9.0, 30.0, 0],
            ]},
        ]
        client2 = FakeClient(histories=payloads)
        collector2, _, _, _ = make_collector(client=client2)
        merged = collector2._historical_minutes(
            "K", date(2026, 8, 8), date(2026, 9, 5)
        )
        self.assertEqual([c.close for c in merged], [9.0, 1.5])
        self.assertEqual(
            merged, sorted(merged, key=lambda c: c.time)
        )

    def test_intraday_fetch_only_on_new_row_minute(self):
        clock = FakeClock()
        client = FakeClient()
        store = FakeStore()

        class StopLoop(Exception):
            pass

        sleeps = []

        def sleep(s):
            sleeps.append(s)
            clock.monotonic += s
            if len(sleeps) == 1:
                clock.now = NOW + timedelta(seconds=20)
            if len(sleeps) == 2:
                clock.now = NOW + timedelta(minutes=1)
            if len(sleeps) >= 3:
                raise StopLoop

        collector = MarketDataCollector(
            client, store, CollectorConfig(quote_interval_seconds=5.0),
            now=lambda: clock.now, monotonic=lambda: clock.monotonic,
            sleep=sleep,
        )
        with self.assertRaises(StopLoop):
            collector.run_forever()
        intraday_calls = [
            c for c in client.calls if c[0] == "intraday_candles"
        ]
        self.assertEqual(len(intraday_calls), 4)
        self.assertEqual(len(store.rows), 2)

    def test_only_closed_today_bars_passed(self):
        payload = intraday_payload()
        payload["candles"].append(
            ["2026-09-22T09:20:00+05:30", 24025.0, 24040.0, 24020.0, 24035.0, 500.0, 0]
        )
        payload["candles"].append(
            ["2026-09-21T09:19:00+05:30", 1.0, 2.0, 0.5, 1.5, 10.0, 0]
        )
        client = FakeClient(intradays=[payload])
        collector, client, store, clock = make_collector(client=client)
        collector.run_once()
        self.assertEqual(len(collector._spot_bars_today), 2)
        self.assertEqual(
            max(b.time.time() for b in collector._spot_bars_today).strftime("%H:%M"),
            "09:19",
        )

    def test_feature_values_land_in_row(self):
        collector, client, store, clock = make_collector()
        row = collector.run_once()
        self.assertEqual(row.session_state, "OPENING_RANGE")
        self.assertTrue(row.is_expiry_day)
        self.assertEqual(row.minutes_to_derivatives_close, 380)
        self.assertEqual(row.nifty_future_price, 24050.0)
        self.assertIsNotNone(row.futures_vwap)
        self.assertEqual(row.spot_bar_close, 24025.0)
        self.assertEqual(row.future_bar_close, 24025.0)
        self.assertEqual(row.future_bar_volume, 800.0)
        self.assertEqual(row.bar_time.minute, 19)
        self.assertIsNotNone(row.bar_age_seconds)
        import json as _json
        reasons = _json.loads(row.gate_reasons)
        self.assertIn("SHADOW_MODE", reasons)
        warnings = _json.loads(row.gate_warnings)
        self.assertIn("VWAP_IS_MINUTE_BAR_PROXY", warnings)
        self.assertIsNone(row.opening_straddle)
        self.assertIsNone(row.shadow_candidate)
        self.assertEqual(row.captured_at, NOW)
        window = _json.loads(row.chain_window)
        self.assertEqual(len(window), 3)
        self.assertEqual(window[0]["strike"], 24000.0)
        self.assertEqual(window[1]["strike"], 23900.0)
        self.assertEqual(
            set(window[0]),
            {
                "strike", "ce_mid", "pe_mid", "ce_oi", "pe_oi",
                "ce_iv", "pe_iv", "ce_delta", "pe_delta",
            },
        )

    def test_opening_straddle_captured_in_window_only(self):
        early_clock = FakeClock(now=datetime(2026, 9, 22, 9, 17, 30, tzinfo=IST))
        collector, client, store, clock = make_collector(clock=early_clock)
        row = collector.run_once()
        self.assertAlmostEqual(row.opening_straddle, 192.0)

        late_clock = FakeClock(now=datetime(2026, 9, 22, 9, 25, 0, tzinfo=IST))
        collector2, _, _, _ = make_collector(clock=late_clock)
        row2 = collector2.run_once()
        self.assertIsNone(row2.opening_straddle)

    def test_bar_failure_retains_history_then_ages_stale(self):
        client = FakeClient(
            intradays=[
                intraday_payload(),
                intraday_payload(),
                UpstoxTransportError("bars down"),
                UpstoxTransportError("bars down"),
                intraday_payload(),
            ]
        )
        clock = FakeClock()
        store = FakeStore()
        collector = MarketDataCollector(
            client,
            store,
            CollectorConfig(
                quote_interval_seconds=5.0,
                stale_after_seconds=3600.0,
                chain_stale_after_seconds=3600.0,
                bar_stale_after_seconds=120.0,
            ),
            now=lambda: clock.now,
            monotonic=lambda: clock.monotonic,
            sleep=lambda s: None,
        )
        errors = []
        sleeps = []

        class StopLoop(Exception):
            pass

        def sleep(s):
            sleeps.append(s)
            clock.monotonic += s
            if len(sleeps) == 1:
                clock.now = NOW + timedelta(minutes=1)
            if len(sleeps) == 2:
                clock.now = NOW + timedelta(minutes=4)
            if len(sleeps) >= 3:
                raise StopLoop

        collector._sleep = sleep
        with self.assertRaises(StopLoop):
            collector.run_forever(on_error=errors.append)
        self.assertEqual(len(errors), 2)
        self.assertTrue(
            all(isinstance(e, UpstoxTransportError) for e in errors)
        )
        self.assertEqual(len(store.rows), 3)
        self.assertFalse(store.rows[0].data_is_stale)
        self.assertFalse(store.rows[1].data_is_stale)
        self.assertGreater(store.rows[1].bar_age_seconds, 0.0)
        self.assertTrue(store.rows[2].data_is_stale)
        self.assertGreater(store.rows[2].bar_age_seconds, 120.0)

    def test_kill_switch_sets_block_reason(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            kill = Path(tmp) / "KILL_SWITCH"
            kill.touch()
            collector, client, store, clock = make_collector(
                kill_switch_path=kill
            )
            row = collector.run_once()
            self.assertEqual(row.block_reason, "KILL_SWITCH")
            import json as _json
            self.assertIn("KILL_SWITCH", _json.loads(row.gate_reasons))

    def test_continuous_mode_inactive_days_make_no_calls(self):
        for day in (date(2026, 9, 20), date(2026, 9, 14), date(2027, 1, 4)):
            clock = FakeClock(now=datetime(day.year, day.month, day.day, 10, 0, tzinfo=IST))
            client = FakeClient()
            store = FakeStore()

            class StopLoop(Exception):
                pass

            count = [0]

            def sleep(s):
                count[0] += 1
                if count[0] >= 2:
                    raise StopLoop

            collector = MarketDataCollector(
                client, store, CollectorConfig(),
                now=lambda: clock.now, monotonic=lambda: clock.monotonic,
                sleep=sleep,
            )
            with self.assertRaises(StopLoop):
                collector.run_forever()
            self.assertEqual(client.calls, [])
            self.assertEqual(store.rows, [])

    def test_continuous_warmup_at_0905_collects(self):
        clock = FakeClock(now=datetime(2026, 9, 22, 9, 5, 0, tzinfo=IST))
        client = FakeClient(intradays=[{"candles": []}])
        store = FakeStore()

        class StopLoop(Exception):
            pass

        def sleep(s):
            raise StopLoop

        collector = MarketDataCollector(
            client, store, CollectorConfig(),
            now=lambda: clock.now, monotonic=lambda: clock.monotonic,
            sleep=sleep,
        )
        with self.assertRaises(StopLoop):
            collector.run_forever()
        self.assertTrue(client.calls)

    def test_run_once_offhours_still_collects(self):
        clock = FakeClock(now=datetime(2026, 9, 20, 10, 0, 0, tzinfo=IST))
        client = FakeClient(
            intradays=[lambda: intraday_payload(clock.now.date())]
        )
        collector, client, store, clock = make_collector(client=client, clock=clock)
        row = collector.run_once()
        self.assertIsInstance(row, MarketDataRow)
        import json as _json
        self.assertIn(
            "UNSUPPORTED_OR_CLOSED_SESSION", _json.loads(row.gate_reasons)
        )

    def test_malformed_strike_rows_ignored_in_basis_keys(self):
        chain = chain_rows()
        chain.append({"strike_price": "abc", "call_options": {}, "put_options": {}})
        chain.append({"strike_price": None})
        chain.append(
            {
                "strike_price": float("nan"),
                "call_options": {"instrument_key": "NSE_FO|CNAN"},
                "put_options": {"instrument_key": "NSE_FO|PNAN"},
            }
        )
        client = FakeClient(chains=[chain])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertEqual(
            collector._session.basis_option_keys,
            (
                "NSE_FO|C23900", "NSE_FO|P23900",
                "NSE_FO|C24000", "NSE_FO|P24000",
                "NSE_FO|C24100", "NSE_FO|P24100",
            ),
        )
        self.assertEqual(row.atm_strike, 24000.0)

    def test_preopen_bars_ignored_with_valid_bars(self):
        payload = intraday_payload()
        payload["candles"].insert(
            0, ["2026-09-22T09:05:00+05:30", 1.0, 2.0, 0.5, 1.5, 10.0, 0]
        )
        client = FakeClient(intradays=[payload])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertEqual(len(collector._spot_bars_today), 2)
        self.assertFalse(row.data_is_stale)

    def test_preopen_only_bars_raise_after_0916(self):
        preopen = {
            "candles": [
                ["2026-09-22T09:05:00+05:30", 1.0, 2.0, 0.5, 1.5, 10.0, 0]
            ]
        }
        client = FakeClient(intradays=[preopen])
        collector, client, store, clock = make_collector(client=client)
        with self.assertRaises(UpstoxDataError):
            collector.run_once()

    def test_missing_or_old_future_quote_is_stale(self):
        q = quotes()
        del q["NSE_FO:FUT_NEAR"]
        client = FakeClient(quote_sets=[q])
        collector, _, _, _ = make_collector(client=client)
        row = collector.run_once()
        self.assertTrue(row.data_is_stale)
        self.assertIsNone(row.nifty_future_price)
        self.assertIsNone(row.source_age_seconds)

        old = quotes()
        old["NSE_FO:FUT_NEAR"]["last_trade_time"] = str(int(NOW_MS - 60_000))
        client2 = FakeClient(quote_sets=[old])
        collector2, _, _, _ = make_collector(client=client2)
        row2 = collector2.run_once()
        self.assertTrue(row2.data_is_stale)
        self.assertGreater(row2.source_age_seconds, 15.0)

    def test_empty_bars_at_0916_stale_after_preopen_success(self):
        empty = {"candles": []}
        preopen = {
            "candles": [
                ["2026-09-22T09:05:00+05:30", 1.0, 2.0, 0.5, 1.5, 10.0, 0]
            ]
        }
        client = FakeClient(intradays=[empty, empty, preopen, preopen])
        clock = FakeClock(now=datetime(2026, 9, 22, 9, 5, 0, tzinfo=IST))
        store = FakeStore()
        collector = MarketDataCollector(
            client,
            store,
            CollectorConfig(quote_interval_seconds=5.0, stale_after_seconds=3600.0),
            now=lambda: clock.now,
            monotonic=lambda: clock.monotonic,
            sleep=lambda s: None,
        )
        errors = []
        sleeps = []

        class StopLoop(Exception):
            pass

        def sleep(s):
            sleeps.append(s)
            clock.monotonic += s
            if len(sleeps) == 1:
                clock.now = datetime(2026, 9, 22, 9, 16, 30, tzinfo=IST)
            if len(sleeps) >= 2:
                raise StopLoop

        collector._sleep = sleep
        with self.assertRaises(StopLoop):
            collector.run_forever(on_error=errors.append)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], UpstoxDataError)
        self.assertEqual(len(store.rows), 2)
        self.assertFalse(store.rows[0].data_is_stale)
        self.assertTrue(store.rows[1].data_is_stale)
        self.assertIsNone(store.rows[1].bar_time)

    def test_bars_use_latest_common_timestamp(self):
        spot_payload = intraday_payload()
        future_payload = {
            "candles": [
                ["2026-09-22T09:15:00+05:30", 24050.0, 24060.0, 24040.0, 24055.0, 300.0, 0],
            ]
        }
        client = FakeClient(intradays=[spot_payload, future_payload])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertEqual(row.bar_time.minute, 15)
        self.assertEqual(row.spot_bar_close, 24010.0)
        self.assertEqual(row.future_bar_close, 24055.0)
        self.assertFalse(row.data_is_stale)

    def test_no_common_bar_timestamp_null_and_stale(self):
        spot_payload = {
            "candles": [
                ["2026-09-22T09:19:00+05:30", 24010.0, 24030.0, 24000.0, 24025.0, 800.0, 0],
            ]
        }
        future_payload = {
            "candles": [
                ["2026-09-22T09:18:00+05:30", 24050.0, 24060.0, 24040.0, 24055.0, 300.0, 0],
            ]
        }
        client = FakeClient(intradays=[spot_payload, future_payload])
        collector, client, store, clock = make_collector(client=client)
        row = collector.run_once()
        self.assertIsNone(row.bar_time)
        self.assertIsNone(row.spot_bar_close)
        self.assertIsNone(row.future_bar_close)
        self.assertTrue(row.data_is_stale)

    def test_shadow_candidate_serializes_when_orb_breakout(self):
        import json as _json

        def bar(minute):
            return [
                f"2026-09-22T09:{minute:02d}:00+05:30",
                23900.0, 23910.0, 23890.0, 23900.0, 500.0, 0,
            ]

        payload = {"candles": [bar(m) for m in range(15, 30)]}
        chain = chain_rows()
        chain[1]["call_options"]["option_greeks"] = {"delta": 0.5, "iv": 12.0}
        chain[1]["put_options"]["option_greeks"] = {"delta": -0.5, "iv": 12.0}
        client = FakeClient(
            chains=[chain],
            intradays=[payload, payload],
        )
        clock = FakeClock(now=datetime(2026, 9, 22, 9, 35, 0, tzinfo=IST))
        collector, client, store, clock = make_collector(client=client, clock=clock)
        row = collector.run_once()
        self.assertIsNotNone(row.shadow_candidate)
        candidate = _json.loads(row.shadow_candidate)
        self.assertEqual(candidate["action"], "LONG_CALL")
        self.assertEqual(candidate["instrument_key"], "NSE_FO|C24000")
        self.assertEqual(candidate["risk_budget_inr"], 12000.0)


class CliAdvisoryTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.duckdb"
        self.env_file = Path(self.tmp.name) / "missing.env"

    def _row(self):
        return MarketDataRow(
            time=NOW,
            nifty_price=24005.0,
            india_vix=13.5,
            expiry_date=date(2026, 9, 22),
            atm_strike=24000.0,
            atm_call_instrument_key="NSE_FO|C24000",
            atm_put_instrument_key="NSE_FO|P24000",
            atm_call_price=101.0,
            atm_put_price=91.0,
            captured_at=NOW,
        )

    def _run(self, argv, advice_factory, result):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        from unittest import mock

        from trading_bot.collector import run

        calls = {"advice_factory": 0, "service": []}

        def fake_advice_factory():
            calls["advice_factory"] += 1
            return object()

        class FakeService:
            def __init__(self, store, client):
                self.store = store
                calls["service"].append(self)

            def run_once(self):
                self.saw_row = self.store.latest_market_data() is not None
                return result

        class FakeCollector:
            def __init__(self, client, store, config):
                self.store = store

            def run_once(self):
                row = self._row_ref
                self.store.upsert_market_data(row)
                return row

            def run_forever(self, on_row=None, on_error=None):
                on_row(self._row_ref)

        collector_holder = []

        def collector_factory(client, store, config):
            instance = FakeCollector(client, store, config)
            instance._row_ref = self._row()
            collector_holder.append(instance)
            return instance

        out = io.StringIO()
        err = io.StringIO()
        factory = advice_factory or fake_advice_factory
        with mock.patch(
            "trading_bot.collector.MarketDataCollector",
            side_effect=collector_factory,
        ), mock.patch(
            "trading_bot.collector.AdviceService", FakeService
        ), redirect_stdout(out), redirect_stderr(err):
            code = run(
                argv
                + [
                    "--db-path", str(self.db_path),
                    "--env-file", str(self.env_file),
                ],
                upstox_client_factory=lambda: FakeClient(),
                advice_client_factory=factory,
            )
        return code, out, err, calls

    def _result(self, status, advice=None, fallback=None,
                snapshot=None, **kwargs):
        from trading_bot.advisory import AdviceRunResult

        if "fallback_reason" in kwargs:
            fallback = kwargs["fallback_reason"]
        return AdviceRunResult(
            status=status,
            advice_id="a1" if status != "SKIPPED" else None,
            advice=advice,
            fallback_reason=fallback,
            snapshot=snapshot,
        )

    def test_disabled_creates_no_advice_client(self):
        def boom():
            raise AssertionError("advice factory must not be called")

        code, out, err, calls = self._run(
            ["--once"], boom, self._result("SKIPPED", fallback="x")
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls["advice_factory"], 0)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn('"row"', lines[0])

    def test_enabled_once_advised_text(self):
        from trading_bot.advisory import Advice

        result = self._result(
            "ADVISED",
            advice=Advice(
                "LONG_CALL", 0.7, "B", 100.0, 86.8, 113.2,
                "Invalid below 86.8.", False, "ORB breakout.",
            ),
            snapshot={"candidate": {"strike": 24050.0}},
        )
        code, out, err, calls = self._run(
            ["--once", "--enable-advisory"], None, result
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls["advice_factory"], 1)
        service = calls["service"][0]
        self.assertTrue(service.saw_row)
        self.assertIn("SHADOW ONLY - DO NOT EXECUTE", out.getvalue())
        self.assertIn("Option: NIFTY 24050.00 CALL", out.getvalue())
        self.assertNotIn("lots", out.getvalue())
        self.assertNotIn("risk_budget", out.getvalue())
        self.assertIn('"row"', out.getvalue())

    def test_enable_openai_advisory_primary_flag(self):
        result = self._result("SKIPPED", fallback="NO_SHADOW_CANDIDATE")
        code, out, err, calls = self._run(
            ["--once", "--enable-openai-advisory"], None, result
        )
        self.assertEqual(code, 0)
        self.assertEqual(calls["advice_factory"], 1)

    def test_enabled_skipped_emits_only_market_row(self):
        result = self._result("SKIPPED", fallback="NO_SHADOW_CANDIDATE")
        code, out, err, calls = self._run(
            ["--once", "--enable-advisory"], None, result
        )
        self.assertEqual(code, 0)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn('"row"', lines[0])
        self.assertNotIn("SHADOW", out.getvalue())

    def test_enabled_fallback_json_event(self):
        from trading_bot.advisory import Advice

        result = self._result(
            "FALLBACK",
            advice=Advice(
                "NO_TRADE", 0.0, "C", None, None, None,
                "No trade was authorized.", True,
                "Deterministic safety fallback.",
            ),
            fallback_reason="BORDERLINE_CONFIDENCE",
        )
        code, out, err, calls = self._run(
            ["--once", "--enable-advisory", "--advisory-output", "json"],
            None,
            result,
        )
        self.assertEqual(code, 0)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        import json as _json

        event = _json.loads(lines[1])
        self.assertEqual(event["event"], "shadow_advice")
        self.assertEqual(event["status"], "FALLBACK")
        self.assertEqual(event["fallback_reason"], "BORDERLINE_CONFIDENCE")

    def test_daily_loss_limit_from_user_feedback(self):
        import json as _json

        class Store(FakeStore):
            def evaluation_rows(self):
                return [
                    {
                        "evaluation_mode": "USER",
                        "trade_was_taken": True,
                        "exited_at": NOW,
                        "actual_entry_price": 100.0,
                        "actual_exit_price": 10.0,
                        "lots": 2,
                        "lot_size": 65,
                        "quoted_spread": 1.0,
                    }
                ]

        collector, client, store, clock = make_collector(store=Store())
        row = collector.run_once()
        reasons = _json.loads(row.gate_reasons)
        self.assertIn("DAILY_LOSS_LIMIT", reasons)
        self.assertLessEqual(row.daily_net_pnl, -5000.0)
        self.assertEqual(row.daily_pnl_costed_trades, 1)

    def test_incomplete_user_feedback_fails_closed(self):
        import json as _json

        class Store(FakeStore):
            def evaluation_rows(self):
                return [
                    {
                        "evaluation_mode": "USER",
                        "trade_was_taken": True,
                        "exited_at": NOW,
                        "actual_entry_price": 100.0,
                        "actual_exit_price": 110.0,
                        "lots": None,
                        "lot_size": 65,
                        "quoted_spread": 1.0,
                    }
                ]

        collector, client, store, clock = make_collector(store=Store())
        row = collector.run_once()
        reasons = _json.loads(row.gate_reasons)
        self.assertIn("DAILY_PNL_UNAVAILABLE", reasons)
        self.assertEqual(row.daily_pnl_uncosted_trades, 1)

    def test_shadow_feedback_excluded_from_daily_pnl(self):
        import json as _json

        class Store(FakeStore):
            def evaluation_rows(self):
                return [
                    {
                        "evaluation_mode": "SHADOW_30M",
                        "trade_was_taken": False,
                        "exited_at": NOW,
                        "actual_entry_price": 100.0,
                        "actual_exit_price": 1.0,
                        "lots": 2,
                        "lot_size": 65,
                        "quoted_spread": 1.0,
                    }
                ]

        collector, client, store, clock = make_collector(store=Store())
        row = collector.run_once()
        reasons = _json.loads(row.gate_reasons)
        self.assertNotIn("DAILY_LOSS_LIMIT", reasons)
        self.assertEqual(row.daily_net_pnl, 0.0)

    def test_calibration_flows_into_candidate(self):
        import json as _json

        from trading_bot.features import FeatureFrame

        frame = FeatureFrame(
            timestamp=NOW.replace(second=0, microsecond=0),
            session_state="PRIME",
            is_expiry_day=False,
            minutes_to_derivatives_close=340,
            lot_size=65,
            future_price=24050.0,
            synthetic_fwd_basis=None,
            atm_iv=None,
            atm_expected_move=None,
            opening_straddle=None,
            expected_move_consumed_pct=None,
            iv_percentile=40.0,
            realized_vol_10d=None,
            vrp_ratio=None,
            opening_range_high=24030.0,
            opening_range_low=24000.0,
            opening_range_width=30.0,
            narrow_range_threshold=None,
            opening_range_is_narrow=False,
            opening_range_state="BREAKOUT_UP",
            relative_volume=2.0,
            relative_volume_spike=True,
            futures_vwap=None,
            vwap_position="UNAVAILABLE",
            vwap_sigma=None,
            first_30m_return_pct=None,
            pcr=None,
            call_oi_walls=(),
            put_oi_walls=(),
            local_gex=None,
            local_gex_sign="UNAVAILABLE",
            momentum_reversion_selector="NEUTRAL",
            atm_call_delta=0.55,
            atm_put_delta=-0.45,
            atm_call_theta=-3.0,
            atm_put_theta=-2.0,
            tod_median_30m_range=100.0,
            missing=(),
        )

        class StubFeatures:
            def compute(self, inputs):
                return frame

        class Store(FakeStore):
            def evaluation_rows(self):
                return [
                    {
                        "evaluation_mode": "SHADOW_30M",
                        "trade_was_taken": False,
                        "exited_at": NOW,
                        "actual_entry_price": 100.0,
                        "actual_exit_price": 110.0,
                        "lots": 1,
                        "lot_size": 65,
                        "quoted_spread": 1.0,
                        "mae": 2.0,
                        "mfe": 12.0,
                        "action": "LONG_CALL",
                    }
                    for _ in range(60)
                ]

        store = Store()
        clock = FakeClock()
        collector = MarketDataCollector(
            FakeClient(),
            store,
            CollectorConfig(),
            now=lambda: clock.now,
            monotonic=lambda: clock.monotonic,
            sleep=clock.sleep,
            feature_engine=StubFeatures(),
        )
        row = collector.run_once()
        self.assertEqual(row.calibration_sample_size, 60)
        self.assertEqual(row.calibrated_mae_p90, 2.0)
        self.assertEqual(row.expected_mfe_per_unit, 12.0)
        self.assertEqual(row.tod_median_30m_range, 100.0)
        candidate = _json.loads(row.shadow_candidate)
        self.assertEqual(candidate["level_source"], "CALIBRATED_MAE_MFE")
        self.assertEqual(candidate["calibration_sample_size"], 60)
        warnings = _json.loads(row.gate_warnings)
        self.assertIn("CALIBRATED_MAE_MFE_LEVELS", warnings)

    def test_no_calibration_history_stays_provisional(self):
        import json as _json

        from trading_bot.features import FeatureFrame

        frame = FeatureFrame(
            timestamp=NOW.replace(second=0, microsecond=0),
            session_state="PRIME",
            is_expiry_day=False,
            minutes_to_derivatives_close=340,
            lot_size=65,
            future_price=24050.0,
            synthetic_fwd_basis=None,
            atm_iv=None,
            atm_expected_move=None,
            opening_straddle=None,
            expected_move_consumed_pct=None,
            iv_percentile=40.0,
            realized_vol_10d=None,
            vrp_ratio=None,
            opening_range_high=24030.0,
            opening_range_low=24000.0,
            opening_range_width=30.0,
            narrow_range_threshold=None,
            opening_range_is_narrow=False,
            opening_range_state="BREAKOUT_UP",
            relative_volume=2.0,
            relative_volume_spike=True,
            futures_vwap=None,
            vwap_position="UNAVAILABLE",
            vwap_sigma=None,
            first_30m_return_pct=None,
            pcr=None,
            call_oi_walls=(),
            put_oi_walls=(),
            local_gex=None,
            local_gex_sign="UNAVAILABLE",
            momentum_reversion_selector="NEUTRAL",
            atm_call_delta=0.55,
            atm_put_delta=-0.45,
            atm_call_theta=-3.0,
            atm_put_theta=-2.0,
            tod_median_30m_range=100.0,
            missing=(),
        )

        class StubFeatures:
            def compute(self, inputs):
                return frame

        clock = FakeClock()
        collector = MarketDataCollector(
            FakeClient(),
            FakeStore(),
            CollectorConfig(),
            now=lambda: clock.now,
            monotonic=lambda: clock.monotonic,
            sleep=clock.sleep,
            feature_engine=StubFeatures(),
        )
        row = collector.run_once()
        candidate = _json.loads(row.shadow_candidate)
        self.assertEqual(candidate["level_source"], "PROVISIONAL_OR_WIDTH")
        reasons = _json.loads(row.gate_reasons)
        self.assertIn("CALIBRATION_HISTORY_INSUFFICIENT", reasons)
        self.assertEqual(row.calibration_sample_size, 0)
        self.assertIsNone(row.expected_mfe_per_unit)

    def test_advisory_config_failure_nonzero_no_secret(self):
        import os
        from unittest import mock

        from trading_bot.llm import LLMConfigurationError

        def factory():
            raise LLMConfigurationError(
                "TRADING_BOT_LLM_MODEL environment variable is not set"
            )

        with mock.patch.dict(
            os.environ, {"OPENAI_API_KEY": "sk-abc123"}
        ):
            code, out, err, calls = self._run(
                ["--once", "--enable-advisory"], factory,
                self._result("SKIPPED"),
            )
        self.assertEqual(code, 1)
        self.assertIn("LLMConfigurationError", err.getvalue())
        self.assertNotIn("sk-abc123", err.getvalue() + out.getvalue())
        self.assertNotIn('"row"', out.getvalue())


class CliSettlementTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.duckdb"
        self.env_file = Path(self.tmp.name) / "missing.env"

    def _row(self):
        return MarketDataRow(
            time=NOW,
            nifty_price=24005.0,
            india_vix=13.5,
            expiry_date=date(2026, 9, 22),
            atm_strike=24000.0,
            atm_call_instrument_key="NSE_FO|C24000",
            atm_put_instrument_key="NSE_FO|P24000",
            atm_call_price=101.0,
            atm_put_price=91.0,
            captured_at=NOW,
        )

    def _run(self, argv, batch):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        from unittest import mock

        from trading_bot.advisory import AdviceRunResult
        from trading_bot.collector import run

        events = []
        holder = {"feedback": []}

        class FakeAdvice:
            def __init__(self, store, client):
                pass

            def run_once(self):
                events.append("advice")
                return AdviceRunResult(
                    status="SKIPPED",
                    advice_id=None,
                    advice=None,
                    fallback_reason="NO_SHADOW_CANDIDATE",
                )

        class FakeFeedback:
            def __init__(self, store, client):
                holder["feedback"].append(self)

            def settle_pending(self):
                events.append("settle")
                return batch

        class FakeCollector:
            def __init__(self, client, store, config):
                self.store = store
                self._row_ref = None

            def run_once(self):
                self.store.upsert_market_data(self._row_ref)
                return self._row_ref

            def run_forever(self, on_row=None, on_error=None):
                on_row(self._row_ref)

        def collector_factory(client, store, config):
            instance = FakeCollector(client, store, config)
            instance._row_ref = self._row()
            return instance

        out = io.StringIO()
        err = io.StringIO()
        with mock.patch(
            "trading_bot.collector.MarketDataCollector",
            side_effect=collector_factory,
        ), mock.patch(
            "trading_bot.collector.AdviceService", FakeAdvice
        ), mock.patch(
            "trading_bot.collector.FeedbackService", FakeFeedback
        ), redirect_stdout(out), redirect_stderr(err):
            code = run(
                argv
                + [
                    "--db-path", str(self.db_path),
                    "--env-file", str(self.env_file),
                ],
                upstox_client_factory=lambda: FakeClient(),
                advice_client_factory=lambda: object(),
            )
        return code, out, err, events, holder

    def _batch(self, settled=(), failures=()):
        from trading_bot.feedback import SettlementBatch

        return SettlementBatch(tuple(settled), tuple(failures))

    def _settled_row(self):
        from trading_bot.storage import TradeFeedbackRow

        return TradeFeedbackRow(
            advice_id="adv1",
            feedback_at=NOW,
            trade_was_taken=False,
            entered_at=NOW,
            exited_at=NOW,
            actual_entry_price=100.0,
            actual_exit_price=105.0,
            lots=2,
            user_verdict="NOT_TAKEN",
            mae=1.0,
            mfe=6.0,
            user_notes="Automated 30-minute shadow outcome.",
            evaluation_mode="SHADOW_30M",
            price_basis="SHADOW_QUOTE_MODEL",
            result_status="HORIZON_EXIT",
            lot_size=65,
            quoted_spread=1.0,
            excursion_source="OPTION_1M_LTP_PROXY",
        )

    def test_advice_runs_before_settlement_by_default(self):
        code, out, err, events, holder = self._run(
            ["--once", "--enable-advisory"], self._batch()
        )
        self.assertEqual(code, 0)
        self.assertEqual(events, ["advice", "settle"])
        self.assertEqual(len(holder["feedback"]), 1)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)

    def test_no_auto_settle_skips_feedback_service(self):
        code, out, err, events, holder = self._run(
            ["--once", "--enable-advisory", "--no-auto-settle"],
            self._batch(settled=[self._settled_row()]),
        )
        self.assertEqual(code, 0)
        self.assertEqual(events, ["advice"])
        self.assertEqual(holder["feedback"], [])

    def test_settlement_json_event(self):
        code, out, err, events, holder = self._run(
            ["--once", "--enable-advisory", "--advisory-output", "json"],
            self._batch(settled=[self._settled_row()]),
        )
        self.assertEqual(code, 0)
        import json as _json

        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        event = _json.loads(lines[1])
        self.assertEqual(event["event"], "shadow_settlement")
        self.assertEqual(len(event["settled"]), 1)
        self.assertEqual(event["settled"][0]["advice_id"], "adv1")
        self.assertEqual(event["failures"], [])

    def test_settlement_text_output_and_failures(self):
        from trading_bot.feedback import SettlementFailure

        batch = self._batch(
            settled=[self._settled_row()],
            failures=[
                SettlementFailure("adv9", "UpstoxTransportError", "timeout")
            ],
        )
        code, out, err, events, holder = self._run(
            ["--once", "--enable-advisory"], batch
        )
        self.assertEqual(code, 0)
        self.assertIn("Settled shadow outcomes: 1", out.getvalue())
        import json as _json

        err_lines = [
            l for l in err.getvalue().splitlines() if l.startswith("{")
        ]
        self.assertEqual(len(err_lines), 1)
        event = _json.loads(err_lines[0])
        self.assertEqual(event["event"], "shadow_settlement_failure")
        self.assertEqual(event["failures"][0]["advice_id"], "adv9")

    def test_disabled_advisory_no_settlement(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        from unittest import mock

        from trading_bot.collector import run

        calls = []

        class FakeFeedback:
            def __init__(self, store, client):
                calls.append("constructed")

            def settle_pending(self):
                calls.append("settle")

        class FakeCollector:
            def __init__(self, client, store, config):
                self.store = store
                self._row_ref = None

            def run_once(self):
                self.store.upsert_market_data(self._row_ref)
                return self._row_ref

        def collector_factory(client, store, config):
            instance = FakeCollector(client, store, config)
            instance._row_ref = self._row()
            return instance

        out = io.StringIO()
        with mock.patch(
            "trading_bot.collector.MarketDataCollector",
            side_effect=collector_factory,
        ), mock.patch(
            "trading_bot.collector.FeedbackService", FakeFeedback
        ), redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = run(
                [
                    "--once",
                    "--db-path", str(self.db_path),
                    "--env-file", str(self.env_file),
                ],
                upstox_client_factory=lambda: FakeClient(),
            )
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
