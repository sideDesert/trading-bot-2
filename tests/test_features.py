import math
import unittest
from dataclasses import replace
from datetime import date, datetime, time, timedelta

from trading_bot.features import (
    IST,
    Candle,
    FeatureConfig,
    FeatureEngine,
    FeatureInputs,
    linear_quantile,
    parse_candles,
)

DAY = date(2026, 9, 22)


def minute_bar(day, hour, minute, o=100.0, h=101.0, l=99.0, c=100.5, v=1000.0):
    return Candle(
        time=datetime(day.year, day.month, day.day, hour, minute, tzinfo=IST),
        open=o, high=h, low=l, close=c, volume=v,
    )


def opening_bars(day=DAY, count=15, base=24000.0):
    bars = []
    for i in range(count):
        minute = 15 + i
        bars.append(
            minute_bar(day, 9, minute, o=base + i, h=base + i + 5, l=base + i - 5, c=base + i)
        )
    return bars


def daily_bars(end_day=DAY, count=20, step=1.0):
    bars = []
    for i in range(count):
        d = end_day - timedelta(days=count - i)
        c = 24000.0 + i * 10
        bars.append(
            Candle(
                time=datetime(d.year, d.month, d.day, 15, 30, tzinfo=IST),
                open=c - step, high=c + step, low=c - step, close=c, volume=1e6,
            )
        )
    return bars


def minute_history(days=20, labels=((9, 40), (9, 41), (9, 42), (9, 43), (9, 44)), vol=100.0):
    bars = []
    for i in range(days):
        d = DAY - timedelta(days=i + 1)
        for h, m in labels:
            bars.append(minute_bar(d, h, m, v=vol))
    return bars


def chain_row(strike, call_oi=500, put_oi=700, call_iv=11.89, put_iv=9.75,
              call_delta=0.55, put_delta=-0.45, call_theta=-3.0, put_theta=-2.0,
              call_gamma=0.001, put_gamma=0.001, ce=None, pe=None,
              call_bid=99.0, call_ask=100.0, put_bid=89.0, put_ask=90.0):
    return {
        "strike_price": strike,
        "call_options": {
            "instrument_key": ce or f"NSE_FO|C{int(strike)}",
            "market_data": {"oi": call_oi, "bid_price": call_bid, "ask_price": call_ask, "ltp": call_ask},
            "option_greeks": {"iv": call_iv, "delta": call_delta, "theta": call_theta, "gamma": call_gamma},
        },
        "put_options": {
            "instrument_key": pe or f"NSE_FO|P{int(strike)}",
            "market_data": {"oi": put_oi, "bid_price": put_bid, "ask_price": put_ask, "ltp": put_ask},
            "option_greeks": {"iv": put_iv, "delta": put_delta, "theta": put_theta, "gamma": put_gamma},
        },
    }


def base_inputs(**overrides):
    values = dict(
        timestamp=datetime(2026, 9, 22, 10, 0, tzinfo=IST),
        spot_price=24050.0,
        vix=13.5,
        future_price=24080.0,
        expiry_date=date(2026, 9, 29),
        atm_strike=24050.0,
        lot_size=75,
        chain_rows=[chain_row(24000), chain_row(24050), chain_row(24100)],
        quotes_by_token={},
        spot_bars_today=opening_bars(),
        future_bars_today=[],
        spot_minute_history=[],
        future_minute_history=[],
        spot_daily_history=daily_bars(),
        atm_iv_history=[],
        opening_straddle=200.0,
        spread_ratio=None,
        data_is_stale=False,
    )
    values.update(overrides)
    return FeatureInputs(**values)


class ParseCandlesTests(unittest.TestCase):
    def test_dict_and_bare_payload(self):
        payload = {"candles": [
            ["2026-09-22T09:16:00+05:30", 1, 2, 0.5, 1.5, 10, 20],
            ["2026-09-22T09:15:00+05:30", 0.9, 1.9, 0.4, 1.4],
        ]}
        candles = parse_candles(payload)
        self.assertEqual(len(candles), 2)
        self.assertEqual(candles[0].time.hour, 9)
        self.assertEqual(candles[0].time.minute, 15)
        self.assertEqual(candles[0].volume, 0.0)
        self.assertEqual(candles[0].oi, 0.0)
        self.assertEqual(candles[1].volume, 10.0)
        bare = parse_candles(payload["candles"])
        self.assertEqual(len(bare), 2)

    def test_z_and_malformed(self):
        candles = parse_candles({"candles": [
            ["2026-09-22T03:45:00Z", 1, 2, 0.5, 1.5, 1, 1],
            ["not-a-date", 1, 2, 0.5, 1.5],
            ["2026-09-22T09:17:00+05:30", "x", 2, 0.5, 1.5],
            ["2026-09-22T09:18:00+05:30", 1, 2],
            "junk",
        ]})
        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].time, datetime(2026, 9, 22, 9, 15, tzinfo=IST))

    def test_empty_and_bad_payload(self):
        self.assertEqual(parse_candles({"status": "success"}), [])
        self.assertEqual(parse_candles(None), [])


class QuantileTests(unittest.TestCase):
    def test_type7(self):
        self.assertAlmostEqual(
            linear_quantile(list(range(1, 11)), 0.2), 2.8
        )
        self.assertEqual(linear_quantile([5], 0.5), 5)
        self.assertIsNone(linear_quantile([], 0.5))
        self.assertIsNone(linear_quantile([None, "x"], 0.5))

    def test_quantile_validation(self):
        for bad in (-0.01, 1.01, -1, 2):
            with self.assertRaises(ValueError):
                linear_quantile([1, 2, 3], bad)
        self.assertEqual(linear_quantile([1, 2, 3], 0), 1)
        self.assertEqual(linear_quantile([1, 2, 3], 1), 3)


class ConfigValidationTests(unittest.TestCase):
    def test_invalid_configs(self):
        for kwargs in (
            {"opening_range_minutes": 0},
            {"relvol_window_minutes": 0},
            {"baseline_sessions": 0},
            {"minimum_baseline_sessions": 0},
            {"minimum_baseline_sessions": 21},
            {"narrow_range_quantile": -0.1},
            {"narrow_range_quantile": 1.1},
            {"relvol_threshold": 0},
            {"ivp_sessions": 0},
            {"realized_vol_sessions": 0},
        ):
            with self.assertRaises(ValueError):
                FeatureEngine(FeatureConfig(**kwargs))


class FeatureEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = FeatureEngine()

    def compute(self, **overrides):
        return self.engine.compute(base_inputs(**overrides))

    def test_session_states(self):
        cases = [
            (time(9, 14), "PREOPEN"),
            (time(9, 15), "OPENING_RANGE"),
            (time(9, 29, 59), "OPENING_RANGE"),
            (time(9, 30), "PRIME"),
            (time(11, 14, 59), "PRIME"),
            (time(11, 15), "MIDDAY"),
            (time(13, 59, 59), "MIDDAY"),
            (time(14, 0), "LATE"),
            (time(15, 14, 59), "LATE"),
            (time(15, 15), "CAS"),
            (time(15, 39, 59), "CAS"),
            (time(15, 40), "CLOSED"),
        ]
        for tod, expected in cases:
            ts = datetime(2026, 9, 22, tod.hour, tod.minute, tod.second, tzinfo=IST)
            frame = self.compute(timestamp=ts)
            self.assertEqual(frame.session_state, expected, tod)

    def test_minutes_to_close(self):
        frame = self.compute(timestamp=datetime(2026, 9, 22, 10, 0, 30, tzinfo=IST))
        self.assertEqual(frame.minutes_to_derivatives_close, 339)
        frame = self.compute(timestamp=datetime(2026, 9, 22, 16, 0, tzinfo=IST))
        self.assertEqual(frame.minutes_to_derivatives_close, 0)

    def test_expiry_day(self):
        self.assertFalse(self.compute().is_expiry_day)
        self.assertTrue(
            self.compute(expiry_date=date(2026, 9, 22)).is_expiry_day
        )

    def test_atm_iv_and_expected_move(self):
        frame = self.compute()
        self.assertAlmostEqual(frame.atm_iv, (11.89 + 9.75) / 2)
        expected = 24050.0 * (frame.atm_iv / 100) * math.sqrt(1 / 252)
        self.assertAlmostEqual(frame.atm_expected_move, expected)

    def test_atm_iv_single_valid_side(self):
        row = chain_row(24050, put_iv=-1)
        frame = self.compute(chain_rows=[row])
        self.assertEqual(frame.atm_iv, 11.89)

    def test_consumed_pct(self):
        frame = self.compute(spot_price=24120.0)
        open_price = 24000.0
        self.assertAlmostEqual(
            frame.expected_move_consumed_pct,
            abs(24120.0 - open_price) / 200.0 * 100,
        )

    def test_iv_percentile(self):
        history = list(range(1, 253))
        frame = self.compute(atm_iv_history=history)
        below = sum(1 for v in history if v < frame.atm_iv)
        self.assertAlmostEqual(frame.iv_percentile, below / 252 * 100)
        short = self.compute(atm_iv_history=history[:251])
        self.assertIsNone(short.iv_percentile)

    def test_realized_vol_and_vrp(self):
        closes = [100.0 * (1.01 ** i) for i in range(11)]
        bars = [
            Candle(
                time=datetime(2026, 9, i + 1, 15, 30, tzinfo=IST),
                open=c, high=c, low=c, close=c,
            )
            for i, c in enumerate(closes)
        ]
        frame = self.compute(spot_daily_history=bars)
        returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, 11)]
        import statistics
        expected = statistics.pstdev(returns) * math.sqrt(252) * 100
        self.assertAlmostEqual(frame.realized_vol_10d, expected)
        self.assertAlmostEqual(frame.vrp_ratio, frame.atm_iv / expected)

    def test_realized_vol_minimum(self):
        bars = daily_bars(count=6)
        frame = self.compute(spot_daily_history=bars)
        self.assertIsNone(frame.realized_vol_10d)
        frame = self.compute(spot_daily_history=daily_bars(count=7))
        self.assertIsNotNone(frame.realized_vol_10d)

    def test_opening_range(self):
        frame = self.compute()
        self.assertEqual(frame.opening_range_high, 24019.0)
        self.assertEqual(frame.opening_range_low, 23995.0)
        self.assertEqual(frame.opening_range_width, 24.0)
        self.assertEqual(frame.opening_range_state, "BREAKOUT_UP")

    def test_opening_range_states(self):
        inside = self.compute(spot_price=24010.0)
        self.assertEqual(inside.opening_range_state, "INSIDE")
        down = self.compute(spot_price=23900.0)
        self.assertEqual(down.opening_range_state, "BREAKOUT_DOWN")
        forming = self.compute(
            timestamp=datetime(2026, 9, 22, 9, 20, tzinfo=IST)
        )
        self.assertEqual(forming.opening_range_state, "FORMING")
        incomplete = self.compute(spot_bars_today=opening_bars(count=10))
        self.assertEqual(incomplete.opening_range_state, "UNAVAILABLE")
        self.assertIsNone(incomplete.opening_range_width)
        no_spot = self.compute(spot_price=None)
        self.assertEqual(no_spot.opening_range_state, "UNAVAILABLE")
        self.assertIsNotNone(no_spot.opening_range_width)
        self.assertIn("opening_range_state", no_spot.missing)

    def test_narrow_range(self):
        frame = self.compute()
        self.assertIsNotNone(frame.narrow_range_threshold)
        self.assertEqual(frame.opening_range_is_narrow, frame.opening_range_width < frame.narrow_range_threshold)
        thin = daily_bars(count=20, step=100.0)
        frame2 = self.compute(spot_daily_history=thin)
        self.assertTrue(frame2.opening_range_is_narrow)
        short = self.compute(spot_daily_history=daily_bars(count=5))
        self.assertIsNone(short.narrow_range_threshold)
        self.assertIsNone(short.opening_range_is_narrow)

    def test_relative_volume(self):
        labels = tuple((9, 40 + i) for i in range(5))
        today = [minute_bar(DAY, 9, 40 + i, v=200.0) for i in range(5)]
        today += opening_bars()
        history = minute_history(days=20, labels=labels, vol=100.0)
        ts = datetime(2026, 9, 22, 9, 50, tzinfo=IST)
        frame = self.compute(
            timestamp=ts,
            future_bars_today=today,
            future_minute_history=history,
        )
        self.assertAlmostEqual(frame.relative_volume, 1000.0 / 500.0)
        self.assertTrue(frame.relative_volume_spike)
        thin = self.compute(
            timestamp=ts,
            future_bars_today=today,
            future_minute_history=minute_history(days=9, labels=labels),
        )
        self.assertIsNone(thin.relative_volume)
        self.assertIsNone(thin.relative_volume_spike)

    def test_vwap_and_position(self):
        bars = [
            minute_bar(DAY, 9, 15, h=102, l=98, c=100, v=300),
            minute_bar(DAY, 9, 16, h=104, l=100, c=102, v=100),
        ]
        ts = datetime(2026, 9, 22, 9, 30, tzinfo=IST)
        vwap = ((102 + 98 + 100) / 3 * 300 + (104 + 100 + 102) / 3 * 100) / 400
        frame = self.compute(
            timestamp=ts, future_bars_today=bars, future_price=vwap + 1.0
        )
        self.assertAlmostEqual(frame.futures_vwap, vwap)
        self.assertEqual(frame.vwap_position, "ABOVE")
        at = self.compute(
            timestamp=ts, future_bars_today=bars, future_price=vwap
        )
        self.assertEqual(at.vwap_position, "AT")
        none = self.compute(timestamp=ts, future_bars_today=[])
        self.assertIsNone(none.futures_vwap)
        self.assertEqual(none.vwap_position, "UNAVAILABLE")

    def test_vwap_sigma(self):
        labels_target = (9, 44)
        history = []
        for i in range(20):
            d = DAY - timedelta(days=i + 1)
            for m in range(15, 45):
                history.append(minute_bar(d, 9, m, h=101, l=99, c=100 + i, v=100))
        today = [minute_bar(DAY, 9, m, v=100) for m in range(15, 45)]
        ts = datetime(2026, 9, 22, 9, 50, tzinfo=IST)
        frame = self.compute(
            timestamp=ts,
            future_bars_today=today,
            future_minute_history=history,
            future_price=200.0,
        )
        self.assertIsNotNone(frame.vwap_sigma)

    def test_first_30m(self):
        bars = [minute_bar(DAY, 9, 15 + i, o=24000 + i, c=24000 + i) for i in range(30)]
        bars[0] = minute_bar(DAY, 9, 15, o=24000.0, c=24000.0)
        bars[29] = minute_bar(DAY, 9, 44, o=24029.0, c=24240.0)
        ts = datetime(2026, 9, 22, 9, 50, tzinfo=IST)
        frame = self.compute(timestamp=ts, spot_bars_today=bars)
        self.assertAlmostEqual(
            frame.first_30m_return_pct, (24240.0 / 24000.0 - 1) * 100
        )
        early = self.compute(
            timestamp=datetime(2026, 9, 22, 9, 44, tzinfo=IST),
            spot_bars_today=bars,
        )
        self.assertIsNone(early.first_30m_return_pct)
        missing_bar = self.compute(
            timestamp=ts, spot_bars_today=bars[:29]
        )
        self.assertIsNone(missing_bar.first_30m_return_pct)

    def test_pcr_and_walls(self):
        rows = [
            chain_row(24000, call_oi=100, put_oi=300),
            chain_row(24050, call_oi=400, put_oi=500),
            chain_row(24100, call_oi=200, put_oi=100),
        ]
        frame = self.compute(chain_rows=rows)
        self.assertAlmostEqual(frame.pcr, 900.0 / 700.0)
        self.assertEqual(frame.call_oi_walls, ((24050.0, 400.0), (24100.0, 200.0)))
        self.assertEqual(frame.put_oi_walls, ((24050.0, 500.0), (24000.0, 300.0)))

    def test_synthetic_basis(self):
        rows = [
            chain_row(24000, call_bid=199, call_ask=200, put_bid=49.5, put_ask=50),
            chain_row(24050, call_bid=149, call_ask=150, put_bid=99.5, put_ask=100),
            chain_row(24100, call_bid=99, call_ask=100, put_bid=149.5, put_ask=150),
        ]
        frame = self.compute(
            chain_rows=rows, atm_strike=24050.0, future_price=24080.0
        )
        forwards = [24000 + 199.5 - 49.75, 24050 + 149.5 - 99.75, 24100 + 99.5 - 149.75]
        import statistics
        self.assertAlmostEqual(
            frame.synthetic_fwd_basis, statistics.median(forwards) - 24080.0
        )

    def test_synthetic_basis_filters_wide(self):
        rows = [
            chain_row(24000, call_bid=50, call_ask=200),
            chain_row(24050, call_bid=149, call_ask=150, put_bid=99.5, put_ask=100),
            chain_row(24100, call_bid=99, call_ask=100, put_bid=149.5, put_ask=150),
        ]
        frame = self.compute(
            chain_rows=rows, atm_strike=24050.0, future_price=24080.0
        )
        import statistics
        forwards = [24050 + 149.5 - 99.75, 24100 + 99.5 - 149.75]
        self.assertAlmostEqual(
            frame.synthetic_fwd_basis, statistics.median(forwards) - 24080.0
        )
        no_fut = self.compute(
            chain_rows=rows, atm_strike=24050.0, future_price=None
        )
        self.assertIsNone(no_fut.synthetic_fwd_basis)

    def test_gex_and_selector(self):
        rows = [chain_row(24000 + i * 50) for i in range(12)]
        frame = self.compute(chain_rows=rows)
        self.assertIsNotNone(frame.local_gex)
        self.assertIn(frame.local_gex_sign, ("POSITIVE", "NEGATIVE", "NEUTRAL"))
        self.assertEqual(
            frame.momentum_reversion_selector,
            "REVERSION_BIAS"
            if frame.local_gex_sign == "POSITIVE"
            else "NEUTRAL",
        )
        empty = self.compute(chain_rows=[])
        self.assertIsNone(empty.local_gex)
        self.assertEqual(empty.local_gex_sign, "UNAVAILABLE")
        self.assertEqual(empty.momentum_reversion_selector, "NEUTRAL")

    def test_greeks_extraction(self):
        frame = self.compute()
        self.assertEqual(frame.atm_call_delta, 0.55)
        self.assertEqual(frame.atm_put_delta, -0.45)
        self.assertEqual(frame.atm_call_theta, -3.0)
        self.assertEqual(frame.atm_put_theta, -2.0)

    def test_missing_fields(self):
        frame = self.compute(
            spot_price=None,
            vix=None,
            future_price=None,
            chain_rows=[],
            spot_bars_today=[],
            spot_daily_history=[],
            timestamp=datetime(2026, 9, 22, 10, 0, tzinfo=IST),
        )
        self.assertIn("atm_iv", frame.missing)
        self.assertIn("pcr", frame.missing)
        self.assertIn("vwap_position", frame.missing)
        self.assertIn("opening_range_state", frame.missing)
        self.assertEqual(tuple(sorted(frame.missing)), frame.missing)


def tod_history(days, start=(10, 0), day_ranges=None):
    bars = []
    for i in range(days):
        d = DAY - timedelta(days=i + 1)
        rng = (
            day_ranges[i]
            if day_ranges is not None and i < len(day_ranges)
            else 20.0
        )
        if rng is None:
            continue
        for j in range(30):
            minute = start[0] * 60 + start[1] + j
            bars.append(
                minute_bar(
                    d, minute // 60, minute % 60,
                    o=100.0, h=100.0 + rng, l=100.0, c=100.5,
                )
            )
    return bars


class TodMedianRangeTests(unittest.TestCase):
    def setUp(self):
        self.engine = FeatureEngine()

    def compute(self, **overrides):
        return self.engine.compute(base_inputs(**overrides))

    def test_exact_median(self):
        history = tod_history(10, day_ranges=[10, 20, 30] * 3 + [20])
        frame = self.compute(spot_minute_history=history)
        self.assertEqual(frame.tod_median_30m_range, 20.0)

    def test_incomplete_sessions_skipped(self):
        history = tod_history(11)
        dropped = [
            bar
            for bar in history
            if not (
                bar.time.date() == DAY - timedelta(days=1)
                and bar.time.hour == 10
                and bar.time.minute == 29
            )
        ]
        frame = self.compute(spot_minute_history=dropped)
        self.assertEqual(frame.tod_median_30m_range, 20.0)

    def test_insufficient_sessions(self):
        frame = self.compute(spot_minute_history=tod_history(9))
        self.assertIsNone(frame.tod_median_30m_range)
        self.assertIn("tod_median_30m_range", frame.missing)

    def test_current_day_and_future_bars_not_used(self):
        history = tod_history(10)
        for j in range(30):
            history.append(
                minute_bar(DAY, 10, j, o=100.0, h=1000.0, l=100.0, c=100.5)
            )
        frame = self.compute(spot_minute_history=history)
        self.assertEqual(frame.tod_median_30m_range, 20.0)

    def test_late_session_unavailable(self):
        bars = []
        for i in range(15):
            d = DAY - timedelta(days=i + 1)
            for j in range(25):
                bars.append(
                    minute_bar(d, 15, j, o=100.0, h=120.0, l=100.0, c=100.5)
                )
        frame = self.compute(
            spot_minute_history=bars,
            timestamp=datetime(2026, 9, 22, 15, 5, tzinfo=IST),
        )
        self.assertIsNone(frame.tod_median_30m_range)


if __name__ == "__main__":
    unittest.main()
