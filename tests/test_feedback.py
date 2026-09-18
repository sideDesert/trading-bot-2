import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

from trading_bot.features import Candle
from trading_bot.feedback import (
    FeedbackService,
    FeedbackValidationError,
    OutcomeDataError,
    build_evaluation_report,
    build_excursion_calibration,
    calculate_excursion,
    daily_user_net_pnl,
    deflated_sharpe_ratio,
)
from trading_bot.feedback import run as feedback_run
from trading_bot.storage import (
    DuckDBStore,
    MarketDataRow,
    ModelAdviceRow,
    TradeFeedbackRow,
)
from trading_bot.upstox.client import UpstoxTransportError

IST = ZoneInfo("Asia/Kolkata")
T0 = datetime(2026, 9, 22, 10, 0, 30, tzinfo=IST)


def candle(minute, o, h, l, c, day=T0):
    return Candle(
        time=day.replace(minute=minute, second=0, microsecond=0),
        open=o, high=h, low=l, close=c,
    )


def candidate(lots=2, spread=1.0):
    return {
        "action": "LONG_CALL",
        "instrument_key": "NSE_FO|C24050",
        "strike": 24050.0,
        "entry_price": 100.0,
        "stop_price": 86.8,
        "provisional_target_price": 113.2,
        "risk_per_unit": 13.2,
        "provisional_reward_per_unit": 13.2,
        "risk_budget_inr": 2500.0,
        "lots": lots,
        "quoted_spread": spread,
    }


def seed_store(db_path, lot_size=65, session_state="REGULAR"):
    store = DuckDBStore(db_path).initialize()
    row = MarketDataRow(
        time=T0,
        nifty_price=24005.0,
        india_vix=13.5,
        expiry_date=T0.date(),
        atm_strike=24000.0,
        atm_call_instrument_key="NSE_FO|C24000",
        atm_put_instrument_key="NSE_FO|P24000",
        atm_call_price=101.0,
        atm_put_price=91.0,
        captured_at=T0,
        lot_size=lot_size,
        session_state=session_state,
        shadow_candidate=json.dumps(candidate()),
    )
    store.upsert_market_data(row)
    advice = ModelAdviceRow(
        advice_id="adv1",
        advice_at=T0,
        context_from=T0 - timedelta(minutes=5),
        context_to=T0,
        prompt_version="v1",
        model_name="m",
        action="LONG_CALL",
        confidence=0.7,
        setup_quality="B",
        entry_price=100.0,
        stop_price=86.8,
        target_price=113.2,
        idea_fails_if="Invalid below 86.8.",
        data_conflict=False,
        reason="ORB breakout.",
        exact_model_input="{}",
        exact_model_output="{}",
        source="shadow",
        instrument_key="NSE_FO|C24050",
        strike=24050.0,
        prompt_hash="h",
        latency_ms=1.0,
    )
    store.insert_model_advice(advice)
    return store


class ExcursionTests(unittest.TestCase):
    def test_stop_hit_conservative_extremes(self):
        candles = [
            candle(1, 100, 105, 98, 100.5),
            candle(2, 100.5, 101, 85.0, 86.0),
            candle(3, 86, 300, 86, 119),
        ]
        exc = calculate_excursion(
            candles, 100.0, T0, T0 + timedelta(minutes=30),
            stop_price=86.8, target_price=113.2,
        )
        self.assertEqual(exc.result_status, "STOP_HIT")
        self.assertEqual(exc.exit_price, 86.8)
        self.assertEqual(exc.exited_at, candles[1].time)
        self.assertAlmostEqual(exc.mae, 100.0 - 86.8)
        self.assertAlmostEqual(exc.mfe, 105.0 - 100.0)

    def test_first_bar_target_stop_and_ambiguous(self):
        target = calculate_excursion(
            [candle(1, 100, 114.0, 99.0, 113.5)],
            100.0, T0, T0 + timedelta(minutes=30),
            stop_price=86.8, target_price=113.2,
        )
        self.assertEqual(target.result_status, "TARGET_HIT")
        self.assertEqual(target.exit_price, 113.2)
        self.assertAlmostEqual(target.mae, 0.0)
        self.assertAlmostEqual(target.mfe, 13.2)

        stop = calculate_excursion(
            [candle(1, 100, 101.0, 85.0, 86.0)],
            100.0, T0, T0 + timedelta(minutes=30),
            stop_price=86.8, target_price=113.2,
        )
        self.assertEqual(stop.result_status, "STOP_HIT")
        self.assertAlmostEqual(stop.mae, 13.2)
        self.assertAlmostEqual(stop.mfe, 0.0)

        ambiguous = calculate_excursion(
            [candle(1, 100, 120.0, 80.0, 100.0), candle(2, 1, 999, 1, 1)],
            100.0, T0, T0 + timedelta(minutes=30),
            stop_price=86.8, target_price=113.2,
        )
        self.assertEqual(ambiguous.result_status, "STOP_HIT_AMBIGUOUS")
        self.assertEqual(ambiguous.exit_price, 86.8)
        self.assertAlmostEqual(ambiguous.mae, 13.2)
        self.assertAlmostEqual(ambiguous.mfe, 0.0)

    def test_boundaries_and_horizon_exit(self):
        candles = [
            candle(0, 1, 999, 1, 1),
            candle(1, 100, 105, 98, 104),
            candle(29, 104, 106, 103, 105.5),
            candle(30, 104, 114, 103, 113),
            candle(31, 1, 999, 1, 1),
        ]
        exc = calculate_excursion(
            candles, 100.0, T0, T0 + timedelta(minutes=30),
            stop_price=86.8, target_price=113.2,
        )
        self.assertEqual(exc.result_status, "HORIZON_EXIT")
        self.assertEqual(exc.exit_price, 105.5)
        self.assertEqual(exc.exited_at, candles[2].time)
        self.assertAlmostEqual(exc.mae, 2.0)
        self.assertAlmostEqual(exc.mfe, 6.0)

    def test_empty_missing_and_validation(self):
        exc = calculate_excursion(
            [], 100.0, T0, T0 + timedelta(minutes=30)
        )
        self.assertEqual(exc.result_status, "MISSING_DATA")
        self.assertIsNone(exc.exit_price)
        with self.assertRaises(OutcomeDataError):
            calculate_excursion([], 0.0, T0, T0 + timedelta(minutes=30))
        with self.assertRaises(OutcomeDataError):
            calculate_excursion([], 100.0, T0, T0)
        with self.assertRaises(OutcomeDataError):
            calculate_excursion(
                [], 100.0, T0, T0 + timedelta(minutes=30), stop_price=110.0
            )
        with self.assertRaises(OutcomeDataError):
            calculate_excursion(
                [], 100.0, T0, T0 + timedelta(minutes=30), target_price=90.0
            )


class FakeUpstox:
    def __init__(self, intraday=None, historical=None):
        self.intraday = intraday if intraday is not None else {"candles": []}
        self.historical = (
            historical if historical is not None else {"candles": []}
        )
        self.calls = []

    def intraday_candles(self, key, unit="minutes", interval=1):
        self.calls.append(("intraday", key, unit, interval))
        if isinstance(self.intraday, Exception):
            raise self.intraday
        return self.intraday

    def historical_candles(self, key, from_date, to_date, unit="minutes", interval=1):
        self.calls.append(("historical", key, from_date, to_date, unit))
        if isinstance(self.historical, Exception):
            raise self.historical
        return self.historical


class FeedbackServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.duckdb"
        self.store = seed_store(self.db_path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_record_not_taken_and_duplicate(self):
        service = FeedbackService(self.store, now=lambda: T0)
        row = service.record_not_taken("adv1", notes="skip")
        self.assertEqual(row.result_status, "NOT_TAKEN")
        self.assertFalse(row.trade_was_taken)
        got = self.store.get_trade_feedback("adv1", "USER")
        self.assertEqual(got["evaluation_mode"], "USER")
        with self.assertRaises(FeedbackValidationError):
            service.record_not_taken("adv1")
        with self.assertRaises(FeedbackValidationError):
            service.record_not_taken("nope")

    def test_record_user_trade_validation_and_success(self):
        service = FeedbackService(self.store, now=lambda: T0)
        with self.assertRaises(FeedbackValidationError):
            service.record_user_trade(
                "adv1", T0, T0, 100.0, 110.0, 1, "WORKED"
            )
        with self.assertRaises(FeedbackValidationError):
            service.record_user_trade(
                "adv1", T0, T0 + timedelta(minutes=5), 0.0, 110.0, 1, "WORKED"
            )
        with self.assertRaises(FeedbackValidationError):
            service.record_user_trade(
                "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
                0, "WORKED",
            )
        with self.assertRaises(FeedbackValidationError):
            service.record_user_trade(
                "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
                1, "MAYBE",
            )
        with self.assertRaises(FeedbackValidationError):
            service.record_user_trade(
                "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
                1, "WORKED", mae=1.0,
            )
        row = service.record_user_trade(
            "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
            2, "WORKED", mae=0.5, mfe=12.0,
        )
        self.assertEqual(row.excursion_source, "USER_PROVIDED")
        self.assertEqual(row.lot_size, 65)
        self.assertEqual(row.quoted_spread, 1.0)
        self.assertEqual(row.result_status, "USER_RECORDED")
        got = self.store.get_trade_feedback("adv1", "USER")
        self.assertEqual(got["lots"], 2)
        with self.assertRaises(Exception):
            self.store.insert_trade_feedback(row)

    def test_record_user_trade_no_excursion(self):
        service = FeedbackService(self.store, now=lambda: T0)
        row = service.record_user_trade(
            "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
            1, "DID_NOT_WORK",
        )
        self.assertIsNone(row.mae)
        self.assertEqual(row.excursion_source, "UNAVAILABLE")

    def test_settle_pending_intraday_path(self):
        candles = {
            "candles": [
                [f"2026-09-22T10:{m:02d}:00+05:30", 100.0, 105.0, 99.0, 103.0, 1, 0]
                for m in range(1, 30)
            ]
        }
        client = FakeUpstox(intraday=candles)
        now = T0 + timedelta(minutes=45)
        service = FeedbackService(self.store, client, now=lambda: now)
        batch = service.settle_pending()
        self.assertEqual(len(batch.settled), 1)
        self.assertEqual(batch.failures, ())
        row = batch.settled[0]
        self.assertEqual(row.result_status, "HORIZON_EXIT")
        self.assertEqual(row.evaluation_mode, "SHADOW_30M")
        self.assertEqual(row.price_basis, "SHADOW_QUOTE_MODEL")
        self.assertEqual(row.excursion_source, "OPTION_1M_LTP_PROXY")
        self.assertEqual(row.lots, 2)
        self.assertEqual(row.lot_size, 65)
        self.assertEqual(row.quoted_spread, 1.0)
        self.assertAlmostEqual(row.actual_exit_price, 103.0)
        self.assertEqual(
            row.user_notes, "Automated 30-minute shadow outcome."
        )
        self.assertEqual(client.calls[0][0], "intraday")
        pending = self.store.pending_shadow_advice(now, 20)
        self.assertEqual(pending, [])

    def test_settle_pending_historical_path_for_past_day(self):
        candles = {
            "candles": [
                ["2026-09-22T10:05:00+05:30", 100.0, 105.0, 99.0, 103.0, 1, 0]
            ]
        }
        client = FakeUpstox(historical=candles)
        past_now = T0 + timedelta(days=2)
        service = FeedbackService(self.store, client, now=lambda: past_now)
        batch = service.settle_pending()
        self.assertEqual(client.calls[0][0], "historical")
        self.assertEqual(client.calls[0][2], "2026-09-22")
        self.assertEqual(len(batch.settled), 1)
        self.assertEqual(batch.settled[0].result_status, "HORIZON_EXIT")

    def test_settle_failure_leaves_pending_and_retries(self):
        client = FakeUpstox(intraday=UpstoxTransportError("down"))
        now = T0 + timedelta(minutes=45)
        service = FeedbackService(self.store, client, now=lambda: now)
        batch = service.settle_pending()
        self.assertEqual(batch.settled, ())
        self.assertEqual(len(batch.failures), 1)
        self.assertEqual(batch.failures[0].advice_id, "adv1")
        self.assertEqual(batch.failures[0].error_type, "UpstoxTransportError")
        self.assertIsNone(self.store.get_trade_feedback("adv1", "SHADOW_30M"))
        self.assertEqual(len(self.store.pending_shadow_advice(now, 20)), 1)

        client.intraday = {
            "candles": [
                ["2026-09-22T10:05:00+05:30", 100.0, 105.0, 99.0, 103.0, 1, 0]
            ]
        }
        retry = service.settle_pending()
        self.assertEqual(len(retry.settled), 1)
        self.assertEqual(retry.settled[0].result_status, "HORIZON_EXIT")
        self.assertIsNotNone(
            self.store.get_trade_feedback("adv1", "SHADOW_30M")
        )

    def test_settle_empty_candles_failure_not_inserted(self):
        client = FakeUpstox(intraday={"candles": []})
        now = T0 + timedelta(minutes=45)
        service = FeedbackService(self.store, client, now=lambda: now)
        batch = service.settle_pending()
        self.assertEqual(batch.settled, ())
        self.assertEqual(batch.failures[0].error_type, "OutcomeDataError")
        self.assertIsNone(self.store.get_trade_feedback("adv1", "SHADOW_30M"))
        self.assertEqual(len(self.store.pending_shadow_advice(now, 20)), 1)

    def test_settle_requires_client_and_validates(self):
        service = FeedbackService(self.store)
        with self.assertRaises(FeedbackValidationError):
            service.settle_pending()
        client = FakeUpstox()
        service = FeedbackService(self.store, client, now=lambda: T0)
        with self.assertRaises(FeedbackValidationError):
            service.settle_pending(horizon_minutes=0)
        with self.assertRaises(FeedbackValidationError):
            service.settle_pending(horizon_minutes=15)
        with self.assertRaises(FeedbackValidationError):
            service.settle_pending(limit=0)

    def _horizon_candles(self):
        return {
            "candles": [
                ["2026-09-22T10:05:00+05:30", 100.0, 105.0, 99.0, 103.0, 1, 0]
            ]
        }

    def test_shadow_then_user_results_coexist(self):
        now = T0 + timedelta(minutes=45)
        client = FakeUpstox(intraday=self._horizon_candles())
        service = FeedbackService(self.store, client, now=lambda: now)
        batch = service.settle_pending()
        self.assertEqual(len(batch.settled), 1)

        row = FeedbackService(self.store, now=lambda: now).record_user_trade(
            "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
            1, "WORKED",
        )
        self.assertEqual(row.evaluation_mode, "USER")
        shadow = self.store.get_trade_feedback("adv1", "SHADOW_30M")
        user = self.store.get_trade_feedback("adv1", "USER")
        self.assertEqual(shadow["result_status"], "HORIZON_EXIT")
        self.assertEqual(user["actual_exit_price"], 110.0)
        rows = self.store.get_trade_feedback_rows("adv1")
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            {r["evaluation_mode"] for r in rows}, {"USER", "SHADOW_30M"}
        )

    def test_user_record_does_not_block_shadow_settlement(self):
        FeedbackService(self.store, now=lambda: T0).record_user_trade(
            "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
            1, "WORKED",
        )
        now = T0 + timedelta(minutes=45)
        pending = self.store.pending_shadow_advice(now, 20)
        self.assertEqual([row["advice_id"] for row in pending], ["adv1"])

        client = FakeUpstox(intraday=self._horizon_candles())
        service = FeedbackService(self.store, client, now=lambda: now)
        batch = service.settle_pending()
        self.assertEqual(len(batch.settled), 1)
        self.assertEqual(batch.settled[0].evaluation_mode, "SHADOW_30M")
        self.assertEqual(len(self.store.get_trade_feedback_rows("adv1")), 2)
        self.assertEqual(self.store.pending_shadow_advice(now, 20), [])

    def test_not_taken_then_user_trade_still_blocked(self):
        service = FeedbackService(self.store, now=lambda: T0)
        service.record_not_taken("adv1")
        with self.assertRaises(FeedbackValidationError):
            service.record_user_trade(
                "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
                1, "WORKED",
            )

    def test_get_trade_feedback_validates_mode(self):
        service = FeedbackService(self.store, now=lambda: T0)
        service.record_not_taken("adv1")
        with self.assertRaises(ValueError):
            self.store.get_trade_feedback("adv1", "BOGUS")
        self.assertIsNone(self.store.get_trade_feedback("adv1", "SHADOW_30M"))


class StorageJoinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.duckdb"
        self.store = seed_store(self.db_path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_pending_shadow_advice_join(self):
        pending = self.store.pending_shadow_advice(
            T0 + timedelta(minutes=31)
        )
        self.assertEqual(len(pending), 1)
        row = pending[0]
        self.assertEqual(row["advice_id"], "adv1")
        self.assertEqual(row["market_lot_size"], 65)
        self.assertEqual(json.loads(row["market_shadow_candidate"])["lots"], 2)
        self.assertEqual(row["market_session_state"], "REGULAR")
        self.assertIsInstance(row["advice_at"], datetime)
        not_yet = self.store.pending_shadow_advice(
            T0 - timedelta(minutes=1)
        )
        self.assertEqual(not_yet, [])

    def test_evaluation_rows_join(self):
        FeedbackService(self.store, now=lambda: T0).record_user_trade(
            "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
            1, "WORKED",
        )
        rows = self.store.evaluation_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["advice_id"], "adv1")
        self.assertEqual(row["action"], "LONG_CALL")
        self.assertEqual(row["market_session_state"], "REGULAR")
        self.assertIsInstance(row["feedback_at"], datetime)

    def test_market_data_at_exact_lookup(self):
        row = self.store.market_data_at(T0)
        self.assertIsNotNone(row)
        self.assertEqual(row["lot_size"], 65)
        self.assertIsNone(
            self.store.market_data_at(T0 + timedelta(minutes=1))
        )


class ReportTests(unittest.TestCase):
    def _feedback_row(self, **kw):
        base = dict(
            advice_id="a",
            feedback_at=T0,
            trade_was_taken=True,
            entered_at=T0,
            exited_at=T0 + timedelta(minutes=5),
            actual_entry_price=100.0,
            actual_exit_price=110.0,
            lots=1,
            user_verdict="WORKED",
            mae=1.0,
            mfe=12.0,
            user_notes=None,
            evaluation_mode="SHADOW_30M",
            price_basis="SHADOW_QUOTE_MODEL",
            result_status="HORIZON_EXIT",
            lot_size=65,
            quoted_spread=1.0,
            excursion_source="OPTION_1M_LTP_PROXY",
            action="LONG_CALL",
            prompt_version="v1",
            market_session_state="REGULAR",
        )
        base.update(kw)
        return base

    def test_empty_report(self):
        report = build_evaluation_report([])
        self.assertEqual(report["total_feedback"], 0)
        self.assertEqual(report["costed_records"], 0)
        self.assertIsNone(report["objective_win_rate"])
        self.assertIsNone(report["expectancy_inr"])
        self.assertIn("SAMPLE_BELOW_100", report["graduation"]["blocked_by"])
        self.assertIn("DSR_UNAVAILABLE", report["graduation"]["blocked_by"])
        self.assertIn(
            "CAPTURE_RATIO_UNAVAILABLE", report["graduation"]["blocked_by"]
        )
        self.assertFalse(report["graduation"]["ready"])

    def test_hand_computed_cost_report(self):
        row = self._feedback_row()
        report = build_evaluation_report([row])
        units = 65
        brokerage = 40.0
        stt = units * 0.0015 * 110.0
        transaction = units * 0.0003553 * 210.0
        sebi = units * 0.000001 * 210.0
        stamp = units * 0.00003 * 100.0
        gst = 0.18 * (brokerage + transaction + sebi)
        slippage = units * 0.5 * 2
        expected_cost = (
            brokerage + stt + transaction + sebi + stamp + gst + slippage
        )
        gross = 10.0 * 65
        self.assertAlmostEqual(report["gross_pnl_inr"], gross, places=2)
        self.assertAlmostEqual(
            report["costs_inr"], round(expected_cost, 2), places=2
        )
        self.assertAlmostEqual(
            report["net_pnl_inr"], round(gross - expected_cost, 2), places=2
        )
        self.assertEqual(report["objective_wins"], 1)
        self.assertEqual(report["objective_win_rate"], 1.0)
        self.assertEqual(report["capture_ratio"], round(10.0 / 12.0, 4))
        self.assertEqual(report["mean_mae"], 1.0)
        self.assertEqual(report["mean_mfe"], 12.0)
        self.assertIn(
            "LONG_CALL", report["by_action"]
        )
        self.assertEqual(report["by_action"]["LONG_CALL"]["count"], 1)
        self.assertIn("v1", report["by_prompt_version"])
        self.assertIn("REGULAR", report["by_session_state"])

    def test_losing_trade_and_graduation_reasons(self):
        row = self._feedback_row(
            actual_exit_price=90.0, user_verdict="DID_NOT_WORK",
            action="LONG_PUT", mfe=5.0,
        )
        report = build_evaluation_report([row])
        self.assertEqual(report["objective_wins"], 0)
        self.assertLess(report["net_pnl_inr"], 0)
        blocked = report["graduation"]["blocked_by"]
        self.assertIn("EXPECTANCY_NOT_POSITIVE", blocked)
        self.assertNotIn("CAPTURE_RATIO_BELOW_0_70", blocked)

    def test_capture_ratio_below_triggers_blocker(self):
        row = self._feedback_row(actual_exit_price=103.5, mfe=10.0)
        report = build_evaluation_report([row])
        self.assertLess(report["capture_ratio"], 0.70)
        self.assertIn(
            "CAPTURE_RATIO_BELOW_0_70", report["graduation"]["blocked_by"]
        )


class DSRTests(unittest.TestCase):
    def test_hand_computed_trial1(self):
        import math
        import statistics
        from statistics import NormalDist

        returns = [1.0, 2.0, 3.0, 4.0, 5.0]
        dsr = deflated_sharpe_ratio(returns, 1)
        mean = 3.0
        stdev = statistics.stdev(returns)
        sr = mean / stdev
        m2 = 2.0
        skew = 0.0
        kurt = 34.0 / 5.0 / 4.0
        se = math.sqrt((1 - skew * sr + ((kurt - 1) / 4) * sr * sr) / 4)
        expected = NormalDist().cdf(sr / se)
        self.assertEqual(dsr["sample_size"], 5)
        self.assertEqual(dsr["trial_count"], 1)
        self.assertAlmostEqual(dsr["sharpe_per_trade"], sr)
        self.assertAlmostEqual(dsr["standard_error"], se)
        self.assertAlmostEqual(dsr["kurtosis"], kurt)
        self.assertAlmostEqual(dsr["benchmark_sharpe"], 0.0)
        self.assertAlmostEqual(dsr["value"], expected)

    def test_multi_trial_benchmark(self):
        from statistics import NormalDist

        dsr = deflated_sharpe_ratio([1.0, 2.0, 3.0, 4.0, 5.0], 10)
        gamma = 0.5772156649015329
        expected_benchmark = dsr["standard_error"] * (
            (1 - gamma) * NormalDist().inv_cdf(1 - 1 / 10)
            + gamma * NormalDist().inv_cdf(1 - 1 / (10 * 2.718281828459045))
        )
        self.assertAlmostEqual(dsr["benchmark_sharpe"], expected_benchmark)
        self.assertLess(dsr["value"], 1.0)

    def test_invalid_and_degenerate(self):
        with self.assertRaises(ValueError):
            deflated_sharpe_ratio([1, 2, 3], 0)
        with self.assertRaises(ValueError):
            deflated_sharpe_ratio([1, 2, 3], True)
        dsr = deflated_sharpe_ratio([1.0, 2.0], 1)
        self.assertIsNone(dsr["value"])
        self.assertEqual(dsr["sample_size"], 2)
        dsr = deflated_sharpe_ratio([5.0, 5.0, 5.0, 5.0], 1)
        self.assertIsNone(dsr["value"])
        dsr = deflated_sharpe_ratio([1.0, None, True, float("nan"), 2.0, 3.0], 1)
        self.assertEqual(dsr["sample_size"], 3)

    def test_report_dsr_and_ready_gates(self):
        import random

        rng = random.Random(7)
        rows = []
        for index in range(120):
            exit_price = 100.0 + rng.uniform(4.0, 9.0)
            rows.append(
                self._feedback_row(
                    advice_id=f"a{index}",
                    actual_exit_price=exit_price,
                    mfe=exit_price - 100.0 + 0.5,
                )
            )
        report = build_evaluation_report(rows)
        self.assertEqual(report["costed_records"], 120)
        self.assertIsNotNone(report["deflated_sharpe"]["value"])
        self.assertNotIn("DSR_UNAVAILABLE", report["graduation"]["blocked_by"])
        if report["deflated_sharpe"]["value"] > 0.95:
            self.assertTrue(report["graduation"]["ready"])
        else:
            self.assertIn(
                "DSR_BELOW_0_95", report["graduation"]["blocked_by"]
            )

    def _feedback_row(self, **kw):
        base = dict(
            advice_id="a",
            feedback_at=T0,
            trade_was_taken=True,
            entered_at=T0,
            exited_at=T0 + timedelta(minutes=5),
            actual_entry_price=100.0,
            actual_exit_price=110.0,
            lots=1,
            user_verdict="WORKED",
            mae=1.0,
            mfe=12.0,
            user_notes=None,
            evaluation_mode="SHADOW_30M",
            price_basis="SHADOW_QUOTE_MODEL",
            result_status="HORIZON_EXIT",
            lot_size=65,
            quoted_spread=1.0,
            excursion_source="OPTION_1M_LTP_PROXY",
            action="LONG_CALL",
            prompt_version="v1",
            market_session_state="REGULAR",
        )
        base.update(kw)
        return base


class DailyPnlTests(unittest.TestCase):
    def _row(self, **kw):
        base = dict(
            evaluation_mode="USER",
            trade_was_taken=True,
            exited_at=T0 + timedelta(minutes=5),
            actual_entry_price=100.0,
            actual_exit_price=110.0,
            lots=1,
            lot_size=65,
            quoted_spread=1.0,
        )
        base.update(kw)
        return base

    def test_hand_computed_user_day(self):
        rows = [self._row()]
        daily = daily_user_net_pnl(rows, T0.date())
        units = 65
        expected_cost = (
            40.0
            + units * 0.0015 * 110.0
            + units * 0.0003553 * 210.0
            + units * 0.000001 * 210.0
            + units * 0.00003 * 100.0
            + 0.18 * (40.0 + units * 0.0003553 * 210.0 + units * 0.000001 * 210.0)
            + units * 0.5 * 2
        )
        self.assertEqual(daily.costed_trades, 1)
        self.assertEqual(daily.uncosted_trades, 0)
        self.assertAlmostEqual(daily.value, 10.0 * 65 - expected_cost)

    def test_only_user_taken_rows_on_day(self):
        rows = [
            self._row(),
            self._row(evaluation_mode="SHADOW_30M", actual_exit_price=1.0),
            self._row(trade_was_taken=False),
            self._row(exited_at=T0 - timedelta(days=1)),
            self._row(evaluation_mode="USER", exited_at=None),
        ]
        daily = daily_user_net_pnl(rows, T0.date())
        self.assertEqual(daily.costed_trades, 1)
        self.assertEqual(daily.uncosted_trades, 0)
        self.assertGreater(daily.value, 0)

    def test_incomplete_row_uncosted(self):
        rows = [self._row(lots=None), self._row()]
        daily = daily_user_net_pnl(rows, T0.date())
        self.assertEqual(daily.costed_trades, 1)
        self.assertEqual(daily.uncosted_trades, 1)

    def test_empty(self):
        daily = daily_user_net_pnl([], T0.date())
        self.assertEqual(daily.value, 0.0)
        self.assertEqual(daily.costed_trades, 0)
        self.assertEqual(daily.uncosted_trades, 0)


class ExcursionCalibrationTests(unittest.TestCase):
    def _winner(self, mae=1.0, mfe=12.0, action="LONG_CALL", **kw):
        base = dict(
            action=action,
            actual_entry_price=100.0,
            actual_exit_price=110.0,
            lots=1,
            lot_size=65,
            quoted_spread=1.0,
            mae=mae,
            mfe=mfe,
        )
        base.update(kw)
        return base

    def test_hand_values(self):
        rows = [
            self._winner(mae=1.0, mfe=10.0),
            self._winner(mae=2.0, mfe=12.0),
            self._winner(mae=3.0, mfe=14.0),
        ]
        cal = build_excursion_calibration(rows, "LONG_CALL", min_samples=3)
        self.assertEqual(cal.sample_size, 3)
        self.assertAlmostEqual(cal.mae_p90, 2.8)
        self.assertEqual(cal.mfe_median, 12.0)

    def test_losers_and_other_action_excluded(self):
        rows = [
            self._winner(),
            self._winner(actual_exit_price=90.0),
            self._winner(action="LONG_PUT", mae=9.0),
        ]
        cal = build_excursion_calibration(rows, "LONG_CALL", min_samples=1)
        self.assertEqual(cal.sample_size, 1)
        self.assertEqual(cal.mae_p90, 1.0)

    def test_missing_cost_or_excursion_excluded(self):
        rows = [
            self._winner(),
            self._winner(quoted_spread=None),
            self._winner(mae=None),
            self._winner(mfe=0.0),
            self._winner(mae=-1.0),
        ]
        cal = build_excursion_calibration(rows, "LONG_CALL", min_samples=1)
        self.assertEqual(cal.sample_size, 1)

    def test_below_threshold_nulls(self):
        cal = build_excursion_calibration(
            [self._winner()] * 5, "LONG_CALL"
        )
        self.assertEqual(cal.sample_size, 5)
        self.assertIsNone(cal.mae_p90)
        self.assertIsNone(cal.mfe_median)

    def test_validation(self):
        with self.assertRaises(ValueError):
            build_excursion_calibration([], "NO_TRADE")
        with self.assertRaises(ValueError):
            build_excursion_calibration([], "LONG_CALL", min_samples=0)


class RecentAdviceCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.duckdb"
        self.store = seed_store(self.db_path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _cli(self, *argv):
        stream = io.StringIO()
        with redirect_stdout(stream):
            status = feedback_run(
                ["--db-path", str(self.db_path), *argv]
            )
        return status, json.loads(stream.getvalue())

    def test_recent_advice_lists_feedback_modes_and_derived_pnl(self):
        FeedbackService(self.store, now=lambda: T0).record_user_trade(
            "adv1", T0, T0 + timedelta(minutes=5), 100.0, 110.0,
            1, "WORKED",
        )
        self.store.close()

        status, payload = self._cli("recent-advice", "--limit", "5")
        self.assertEqual(status, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["advice"]), 1)
        advice = payload["advice"][0]
        self.assertEqual(advice["advice_id"], "adv1")
        self.assertEqual(advice["action"], "LONG_CALL")
        self.assertEqual(advice["entry_price"], 100.0)
        self.assertEqual(advice["stop_price"], 86.8)
        self.assertEqual(advice["target_price"], 113.2)
        self.assertTrue(advice["advice_at"].endswith("+05:30"))
        feedback = advice["feedback"]
        self.assertEqual(set(feedback), {"USER"})
        user = feedback["USER"]
        self.assertEqual(user["evaluation_mode"], "USER")
        self.assertEqual(user["result_status"], "USER_RECORDED")
        self.assertEqual(user["price_basis"], "ACTUAL_FILL")
        self.assertEqual(user["actual_entry_price"], 100.0)
        self.assertEqual(user["actual_exit_price"], 110.0)
        self.assertEqual(user["lots"], 1)
        self.assertEqual(user["lot_size"], 65)
        derived = user["derived"]
        self.assertEqual(derived["gross_pnl_inr"], 650.0)
        self.assertGreater(derived["costs_inr"], 0)
        self.assertLess(derived["net_pnl_inr"], 650.0)

    def test_recent_advice_without_feedback_and_bad_limit(self):
        self.store.close()
        status, payload = self._cli("recent-advice")
        self.assertEqual(status, 0)
        self.assertEqual(payload["advice"][0]["feedback"], {})
        with redirect_stdout(io.StringIO()):
            status = feedback_run(
                ["--db-path", str(self.db_path), "recent-advice", "--limit", "0"]
            )
        self.assertEqual(status, 1)

    def test_record_trade_cli_echoes_derived_pnl(self):
        self.store.close()
        status, payload = self._cli(
            "record-trade",
            "--advice-id", "adv1",
            "--entered-at", T0.isoformat(),
            "--exited-at", (T0 + timedelta(minutes=10)).isoformat(),
            "--entry-price", "100",
            "--exit-price", "110",
            "--lots", "1",
            "--verdict", "WORKED",
        )
        self.assertEqual(status, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["feedback"]["evaluation_mode"], "USER")
        self.assertEqual(payload["derived"]["gross_pnl_inr"], 650.0)
        with DuckDBStore(self.db_path) as store:
            row = store.get_trade_feedback("adv1", "USER")
            self.assertEqual(row["actual_exit_price"], 110.0)
            self.assertIsNone(store.get_trade_feedback("adv1", "SHADOW_30M"))


if __name__ == "__main__":
    unittest.main()
