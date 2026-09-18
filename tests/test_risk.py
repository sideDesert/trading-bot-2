import unittest
from datetime import date, datetime, time

from trading_bot.features import IST, FeatureFrame, FeatureInputs
from trading_bot.market_rules import TradingCalendar
from trading_bot.risk import (
    CostConfig,
    RiskConfig,
    RiskEngine,
    calculate_round_trip_cost,
)


def make_frame(**overrides):
    values = dict(
        timestamp=datetime(2026, 9, 22, 10, 0, tzinfo=IST),
        session_state="PRIME",
        is_expiry_day=False,
        minutes_to_derivatives_close=340,
        lot_size=75,
        future_price=24080.0,
        synthetic_fwd_basis=5.0,
        atm_iv=10.0,
        atm_expected_move=150.0,
        opening_straddle=200.0,
        expected_move_consumed_pct=30.0,
        iv_percentile=40.0,
        realized_vol_10d=12.0,
        vrp_ratio=0.8,
        opening_range_high=24024.0,
        opening_range_low=23995.0,
        opening_range_width=24.0,
        narrow_range_threshold=20.0,
        opening_range_is_narrow=False,
        opening_range_state="BREAKOUT_UP",
        relative_volume=2.0,
        relative_volume_spike=True,
        futures_vwap=24060.0,
        vwap_position="ABOVE",
        vwap_sigma=0.5,
        first_30m_return_pct=0.3,
        pcr=1.1,
        call_oi_walls=(),
        put_oi_walls=(),
        local_gex=1e6,
        local_gex_sign="POSITIVE",
        momentum_reversion_selector="REVERSION_BIAS",
        atm_call_delta=0.55,
        atm_put_delta=-0.45,
        atm_call_theta=-3.0,
        atm_put_theta=-2.0,
        tod_median_30m_range=50.0,
        missing=(),
    )
    values.update(overrides)
    return FeatureFrame(**values)


def make_inputs(**overrides):
    chain = [
        {
            "strike_price": 24050.0,
            "call_options": {
                "instrument_key": "NSE_FO|C24050",
                "market_data": {"bid_price": 99.0, "ask_price": 100.0, "oi": 500},
                "option_greeks": {"delta": 0.55},
            },
            "put_options": {
                "instrument_key": "NSE_FO|P24050",
                "market_data": {"bid_price": 89.0, "ask_price": 90.0, "oi": 700},
                "option_greeks": {"delta": -0.45},
            },
        }
    ]
    values = dict(
        timestamp=datetime(2026, 9, 22, 10, 0, tzinfo=IST),
        spot_price=24050.0,
        vix=13.5,
        future_price=24080.0,
        expiry_date=date(2026, 9, 29),
        atm_strike=24050.0,
        lot_size=65,
        chain_rows=chain,
        quotes_by_token={},
        spot_bars_today=[],
        future_bars_today=[],
        spot_minute_history=[],
        future_minute_history=[],
        spot_daily_history=[],
        data_is_stale=False,
    )
    values.update(overrides)
    return FeatureInputs(**values)


class CostTests(unittest.TestCase):
    def test_exact_components(self):
        cost = calculate_round_trip_cost(100.0, 100.0, 1, 65, 1.0)
        units = 65
        self.assertEqual(cost.brokerage, 40.0)
        self.assertAlmostEqual(cost.stt, units * 0.0015 * 100)
        self.assertAlmostEqual(cost.transaction, units * 0.0003553 * 200)
        self.assertAlmostEqual(cost.sebi, units * 0.000001 * 200)
        self.assertAlmostEqual(cost.stamp, units * 0.00003 * 100)
        self.assertAlmostEqual(
            cost.gst, 0.18 * (40.0 + cost.transaction + cost.sebi)
        )
        self.assertAlmostEqual(cost.slippage, units * 0.5 * 2)
        expected_total = (
            40.0 + cost.stt + cost.transaction + cost.sebi + cost.stamp + cost.gst + cost.slippage
        )
        self.assertAlmostEqual(cost.total, expected_total)
        self.assertAlmostEqual(cost.per_unit, cost.total / units)
        self.assertAlmostEqual(cost.breakeven_ticks, cost.per_unit / 0.05)

    def test_lot_size_changes_total(self):
        c65 = calculate_round_trip_cost(100, 100, 1, 65, 1.0)
        c75 = calculate_round_trip_cost(100, 100, 1, 75, 1.0)
        self.assertGreater(c75.total, c65.total)
        c2 = calculate_round_trip_cost(100, 100, 2, 65, 1.0)
        self.assertGreater(c2.total, c65.total)

    def test_slippage_tick_floor(self):
        cost = calculate_round_trip_cost(100, 100, 1, 65, 0.02)
        self.assertAlmostEqual(cost.slippage, 65 * 0.05 * 2)

    def test_validation(self):
        for args in (
            (0, 100, 1, 65, 1.0),
            (100, 0, 1, 65, 1.0),
            (100, 100, 0, 65, 1.0),
            (100, 100, 1, 0, 1.0),
            (100, 100, 1, 65, -1.0),
        ):
            with self.assertRaises(ValueError):
                calculate_round_trip_cost(*args)
        with self.assertRaises(ValueError):
            calculate_round_trip_cost(
                100, 100, 1, 65, 1.0, CostConfig(tick_size=0)
            )
        with self.assertRaises(ValueError):
            calculate_round_trip_cost(
                100, 100, 1, 65, 1.0, CostConfig(gst_rate=-0.1)
            )


class RiskEngineTests(unittest.TestCase):
    def setUp(self):
        # Pin sizing config so these arithmetic assertions test the logic
        # independent of the production defaults in RiskConfig.
        self.engine = RiskEngine(
            RiskConfig(max_trade_risk_inr=2500.0, minimum_cost_efficient_lots=5)
        )

    def evaluate(self, frame_kw=None, input_kw=None, **kwargs):
        return self.engine.evaluate(
            make_frame(**(frame_kw or {})),
            make_inputs(**(input_kw or {})),
            **kwargs,
        )

    def test_shadow_candidate_retained_with_blockers(self):
        decision = self.evaluate()
        self.assertIsNotNone(decision.candidate)
        self.assertTrue(decision.shadow_candidate)
        self.assertFalse(decision.execution_allowed)
        self.assertIn("SHADOW_MODE", decision.blockers)
        self.assertIn("COST_INEFFICIENT_SIZE", decision.blockers)
        self.assertIn("EXPECTED_MFE_UNAVAILABLE", decision.blockers)
        self.assertIn("PROVISIONAL_OR_WIDTH_LEVELS", decision.warnings)
        self.assertIn("GEX_ASSUMPTION_UNVERIFIED", decision.warnings)
        self.assertIn("VWAP_IS_MINUTE_BAR_PROXY", decision.warnings)

    def test_candidate_details(self):
        decision = self.evaluate(expected_mfe_per_unit=1000.0)
        c = decision.candidate
        self.assertEqual(c.action, "LONG_CALL")
        self.assertEqual(c.instrument_key, "NSE_FO|C24050")
        self.assertEqual(c.entry_price, 100.0)
        self.assertEqual(c.quoted_spread, 1.0)
        self.assertAlmostEqual(c.provisional_reward_per_unit, 24.0 * 0.55)
        self.assertAlmostEqual(c.stop_price, 100.0 - 13.2)
        self.assertAlmostEqual(c.risk_per_unit, 13.2)
        self.assertEqual(c.risk_budget_inr, 2500.0)
        self.assertEqual(c.lots, int(2500.0 // (13.2 * 65)))
        self.assertIsNotNone(c.sized_cost)
        self.assertAlmostEqual(c.provisional_target_price, 100.0 + 13.2)

    def test_levels_on_tick_grid_exact(self):
        decision = self.evaluate()
        c = decision.candidate
        self.assertAlmostEqual(c.entry_price, 100.0)
        self.assertAlmostEqual(c.stop_price, 86.8)
        self.assertAlmostEqual(c.provisional_target_price, 113.2)
        self.assertAlmostEqual(c.risk_per_unit, 13.2)
        self.assertAlmostEqual(c.provisional_reward_per_unit, 13.2)
        self.assertEqual(c.lots, 2)

    def test_non_grid_levels_round_to_tick(self):
        decision = self.evaluate(
            frame_kw={"opening_range_width": 24.37, "atm_call_delta": 0.53}
        )
        c = decision.candidate
        self.assertAlmostEqual(c.stop_price, 87.10)
        self.assertAlmostEqual(c.provisional_target_price, 112.90)
        self.assertAlmostEqual(c.risk_per_unit, 12.90)
        self.assertAlmostEqual(c.provisional_reward_per_unit, 12.90)
        self.assertEqual(c.lots, int(2500.0 // (12.90 * 65)))

    def test_candidate_levels_on_tick(self):
        for width, delta in (
            (24.0, 0.55),
            (24.37, 0.53),
            (7.77, 0.91),
            (50.0, 0.40),
        ):
            decision = self.evaluate(
                frame_kw={
                    "opening_range_width": width,
                    "atm_call_delta": delta,
                }
            )
            c = decision.candidate
            self.assertIsNotNone(c)
            for price in (
                c.entry_price, c.stop_price, c.provisional_target_price
            ):
                self.assertAlmostEqual(
                    price / 0.05, round(price / 0.05), places=6
                )

    def test_non_grid_ask_rejected_without_spread_unavailable(self):
        chain = make_inputs().chain_rows
        chain[0]["call_options"]["market_data"]["ask_price"] = 100.03
        decision = self.evaluate(input_kw={"chain_rows": chain})
        self.assertIsNone(decision.candidate)
        self.assertIn("CANDIDATE_DATA_MISSING", decision.blockers)
        self.assertNotIn("SPREAD_UNAVAILABLE", decision.blockers)

    def test_custom_tick_size(self):
        engine = RiskEngine(cost_config=CostConfig(tick_size=0.10))
        decision = engine.evaluate(
            make_frame(opening_range_width=24.03, atm_call_delta=0.55),
            make_inputs(),
        )
        c = decision.candidate
        self.assertIsNotNone(c)
        self.assertAlmostEqual(c.stop_price, 86.8)
        self.assertAlmostEqual(c.provisional_target_price, 113.2)
        self.assertAlmostEqual(c.risk_per_unit, 13.2)

    def test_breakout_down_put(self):
        decision = self.evaluate(
            frame_kw={"opening_range_state": "BREAKOUT_DOWN"}
        )
        self.assertEqual(decision.candidate.action, "LONG_PUT")
        self.assertEqual(decision.candidate.instrument_key, "NSE_FO|P24050")

    def test_no_orb_breakout(self):
        for state in ("INSIDE", "FORMING", "UNAVAILABLE"):
            decision = self.evaluate(frame_kw={"opening_range_state": state})
            self.assertIsNone(decision.candidate)
            self.assertFalse(decision.shadow_candidate)
            self.assertIn("NO_ORB_BREAKOUT", decision.blockers)

    def test_candidate_data_missing(self):
        decision = self.evaluate(input_kw={"chain_rows": []})
        self.assertIsNone(decision.candidate)
        self.assertIn("CANDIDATE_DATA_MISSING", decision.blockers)
        self.assertIn("SPREAD_UNAVAILABLE", decision.blockers)
        no_delta = self.evaluate(frame_kw={"atm_call_delta": None})
        self.assertIn("CANDIDATE_DATA_MISSING", no_delta.blockers)
        self.assertNotIn("SPREAD_UNAVAILABLE", no_delta.blockers)
        no_key = make_inputs().chain_rows
        no_key[0]["call_options"].pop("instrument_key")
        missing_key = self.evaluate(input_kw={"chain_rows": no_key})
        self.assertIn("CANDIDATE_DATA_MISSING", missing_key.blockers)
        self.assertNotIn("SPREAD_UNAVAILABLE", missing_key.blockers)

    def test_time_blocks(self):
        def at(tod, expiry=False):
            ts = datetime(
                2026, 9, 22, tod.hour, tod.minute, tod.second, tzinfo=IST
            )
            return self.evaluate(
                frame_kw={"timestamp": ts, "is_expiry_day": expiry}
            ).blockers

        self.assertIn("OPEN_BLOCK", at(time(9, 44)))
        self.assertNotIn("OPEN_BLOCK", at(time(9, 45)))
        self.assertIn("MIDDAY_BLOCK", at(time(11, 30)))
        self.assertNotIn("MIDDAY_BLOCK", at(time(11, 29)))
        self.assertIn("MIDDAY_BLOCK", at(time(13, 29, 59)))
        self.assertNotIn("MIDDAY_BLOCK", at(time(13, 30)))
        self.assertNotIn("MIDDAY_BLOCK", at(time(11, 45), expiry=True))
        self.assertIn("MIDDAY_BLOCK", at(time(12, 30), expiry=True))
        self.assertNotIn("MIDDAY_BLOCK", at(time(14, 0), expiry=True))
        self.assertIn("EXPIRY_ENTRY_CUTOFF", at(time(13, 15), expiry=True))
        self.assertNotIn("EXPIRY_ENTRY_CUTOFF", at(time(13, 15), expiry=False))
        self.assertIn("EXPIRY_FLAT_TIME", at(time(14, 45), expiry=True))
        self.assertIn("LATE_ENTRY_BLOCK", at(time(15, 15)))
        self.assertNotIn("LATE_ENTRY_BLOCK", at(time(15, 14, 59)))
        self.assertIn("OUTSIDE_MARKET_HOURS", at(time(15, 40)))
        self.assertIn("OUTSIDE_MARKET_HOURS", at(time(9, 0)))

    def test_unsupported_and_closed_sessions(self):
        ts = datetime(2025, 9, 22, 10, 0, tzinfo=IST)
        decision = self.evaluate(frame_kw={"timestamp": ts})
        self.assertIn("UNSUPPORTED_OR_CLOSED_SESSION", decision.blockers)
        holiday = datetime(2026, 1, 26, 10, 0, tzinfo=IST)
        decision = self.evaluate(frame_kw={"timestamp": holiday})
        self.assertIn("UNSUPPORTED_OR_CLOSED_SESSION", decision.blockers)
        special = datetime(2026, 2, 1, 10, 0, tzinfo=IST)
        decision = self.evaluate(frame_kw={"timestamp": special})
        self.assertNotIn("UNSUPPORTED_OR_CLOSED_SESSION", decision.blockers)
        self.assertNotIn("OUTSIDE_MARKET_HOURS", decision.blockers)

    def test_health_blockers(self):
        self.assertIn(
            "STALE_DATA", self.evaluate(input_kw={"data_is_stale": True}).blockers
        )
        self.assertIn(
            "KILL_SWITCH", self.evaluate(kill_switch_active=True).blockers
        )
        self.assertIn(
            "DAILY_LOSS_LIMIT", self.evaluate(daily_net_pnl=-5000.0).blockers
        )
        self.assertNotIn(
            "DAILY_LOSS_LIMIT", self.evaluate(daily_net_pnl=-4999.99).blockers
        )

    def test_quality_blockers(self):
        self.assertIn(
            "NARROW_OPENING_RANGE",
            self.evaluate(frame_kw={"opening_range_is_narrow": True}).blockers,
        )
        self.assertIn(
            "OR_HISTORY_INSUFFICIENT",
            self.evaluate(frame_kw={"opening_range_is_narrow": None}).blockers,
        )
        self.assertIn(
            "RELVOL_HISTORY_INSUFFICIENT",
            self.evaluate(frame_kw={"relative_volume": None}).blockers,
        )
        self.assertIn(
            "LOW_RELATIVE_VOLUME",
            self.evaluate(frame_kw={"relative_volume": 1.49}).blockers,
        )
        self.assertIn(
            "IVP_HISTORY_INSUFFICIENT",
            self.evaluate(frame_kw={"iv_percentile": None}).blockers,
        )
        self.assertIn(
            "IVP_TOO_HIGH",
            self.evaluate(frame_kw={"iv_percentile": 65.01}).blockers,
        )
        self.assertNotIn(
            "IVP_TOO_HIGH",
            self.evaluate(frame_kw={"iv_percentile": 65.0}).blockers,
        )

    def test_custom_minimum_relative_volume(self):
        engine = RiskEngine(RiskConfig(minimum_relative_volume=3.0))
        decision = engine.evaluate(
            make_frame(relative_volume=2.0), make_inputs()
        )
        self.assertIn("LOW_RELATIVE_VOLUME", decision.blockers)

    def test_vix_half_risk_sizing(self):
        low = self.evaluate(input_kw={"vix": 16.0})
        high = self.evaluate(input_kw={"vix": 16.01})
        self.assertEqual(low.candidate.risk_budget_inr, 2500.0)
        self.assertEqual(high.candidate.risk_budget_inr, 1250.0)
        self.assertEqual(low.candidate.lots, int(2500.0 // (13.2 * 65)))
        self.assertEqual(high.candidate.lots, int(1250.0 // (13.2 * 65)))
        self.assertLess(high.candidate.lots, low.candidate.lots)
        self.assertIn("VIX_ABOVE_16", high.warnings)
        self.assertNotIn("VIX_ABOVE_16", low.warnings)
        self.assertIsNotNone(high.candidate.sized_cost)
        sized = high.candidate.sized_cost
        self.assertAlmostEqual(sized.per_unit, sized.total / (high.candidate.lots * 65))

    def test_spread_too_wide(self):
        chain = make_inputs().chain_rows
        chain[0]["call_options"]["market_data"]["ask_price"] = 104.0
        decision = self.evaluate(input_kw={"chain_rows": chain})
        self.assertIn("SPREAD_TOO_WIDE", decision.blockers)

    def test_strike_too_far(self):
        decision = self.evaluate(input_kw={"spot_price": 1000.0})
        self.assertIn("STRIKE_TOO_FAR", decision.blockers)

    def test_risk_budget_and_cost_efficiency(self):
        engine = RiskEngine(RiskConfig(shadow_mode=False, max_trade_risk_inr=10.0))
        decision = engine.evaluate(make_frame(), make_inputs())
        self.assertIn("RISK_BUDGET_TOO_SMALL", decision.blockers)
        self.assertIn("COST_INEFFICIENT_SIZE", decision.blockers)
        self.assertIsNotNone(decision.candidate)

    def test_expected_edge_below_cost(self):
        engine = RiskEngine(RiskConfig(shadow_mode=False))
        decision = engine.evaluate(
            make_frame(), make_inputs(), expected_mfe_per_unit=0.0
        )
        self.assertIn("EXPECTED_EDGE_BELOW_COST", decision.blockers)

    def test_fully_eligible_executes(self):
        engine = RiskEngine(
            RiskConfig(
                shadow_mode=False,
                minimum_cost_efficient_lots=1,
                max_trade_risk_inr=2500.0,
            )
        )
        frame = make_frame(
            atm_call_delta=1.0,
            opening_range_width=4.0,
            iv_percentile=40.0,
            relative_volume=2.0,
            opening_range_is_narrow=False,
        )
        inputs = make_inputs(
            chain_rows=[
                {
                    "strike_price": 24050.0,
                    "call_options": {
                        "instrument_key": "NSE_FO|C24050",
                        "market_data": {"bid_price": 4.95, "ask_price": 5.0, "oi": 500},
                        "option_greeks": {"delta": 1.0},
                    },
                    "put_options": {
                        "instrument_key": "NSE_FO|P24050",
                        "market_data": {"bid_price": 4.95, "ask_price": 5.0, "oi": 700},
                        "option_greeks": {"delta": -1.0},
                    },
                }
            ],
            lot_size=10,
        )
        decision = engine.evaluate(
            frame,
            inputs,
            expected_mfe_per_unit=1000.0,
            calibrated_mae_per_unit=2.0,
            calibrated_mfe_per_unit=4.0,
            calibration_sample_size=60,
        )
        self.assertIsNotNone(decision.candidate)
        self.assertEqual(decision.candidate.lots, 125)
        self.assertEqual(decision.blockers, ())
        self.assertTrue(decision.execution_allowed)

    def test_calibrated_levels_on_tick(self):
        decision = self.evaluate(
            calibrated_mae_per_unit=2.35,
            calibrated_mfe_per_unit=4.10,
            calibration_sample_size=60,
        )
        c = decision.candidate
        self.assertEqual(c.level_source, "CALIBRATED_MAE_MFE")
        self.assertEqual(c.calibration_sample_size, 60)
        self.assertAlmostEqual(c.stop_price, 97.65)
        self.assertAlmostEqual(c.provisional_target_price, 104.10)
        self.assertAlmostEqual(c.risk_per_unit, 2.35)
        self.assertAlmostEqual(c.provisional_reward_per_unit, 4.10)
        self.assertIn("CALIBRATED_MAE_MFE_LEVELS", decision.warnings)
        self.assertNotIn("PROVISIONAL_OR_WIDTH_LEVELS", decision.warnings)
        self.assertNotIn(
            "CALIBRATION_HISTORY_INSUFFICIENT", decision.blockers
        )

    def test_provisional_levels_when_calibration_insufficient(self):
        for kwargs in (
            {},
            {"calibrated_mae_per_unit": 2.0, "calibrated_mfe_per_unit": 4.0,
             "calibration_sample_size": 49},
            {"calibrated_mae_per_unit": 2.0,
             "calibration_sample_size": 60},
            {"calibrated_mae_per_unit": -1.0, "calibrated_mfe_per_unit": 4.0,
             "calibration_sample_size": 60},
        ):
            decision = self.evaluate(**kwargs)
            c = decision.candidate
            self.assertEqual(c.level_source, "PROVISIONAL_OR_WIDTH")
            self.assertAlmostEqual(c.risk_per_unit, 13.2)
            self.assertIn(
                "CALIBRATION_HISTORY_INSUFFICIENT", decision.blockers
            )
            self.assertIn(
                "PROVISIONAL_OR_WIDTH_LEVELS", decision.warnings
            )

    def test_theta_formula_hand_computed(self):
        decision = self.evaluate()
        c = decision.candidate
        self.assertAlmostEqual(
            c.theta_decay_per_unit, abs(-3.0) * 30 / 385
        )
        expected_required = (
            c.theta_decay_per_unit + c.sized_cost.per_unit
        ) / 0.55
        self.assertAlmostEqual(
            c.theta_required_underlying_move, expected_required
        )
        self.assertNotIn("THETA_CLOCK_BLOCK", decision.blockers)
        self.assertNotIn("THETA_CLOCK_UNAVAILABLE", decision.blockers)

    def test_theta_boundary_and_block(self):
        decision = self.evaluate()
        required = decision.candidate.theta_required_underlying_move
        at_boundary = self.evaluate(
            frame_kw={"tod_median_30m_range": required}
        )
        self.assertNotIn("THETA_CLOCK_BLOCK", at_boundary.blockers)
        below = self.evaluate(
            frame_kw={"tod_median_30m_range": required - 0.01}
        )
        self.assertIn("THETA_CLOCK_BLOCK", below.blockers)

    def test_theta_unavailable(self):
        for kw in (
            {"tod_median_30m_range": None},
            {"tod_median_30m_range": 0.0},
            {"atm_call_theta": None},
        ):
            decision = self.evaluate(frame_kw=kw)
            self.assertIn("THETA_CLOCK_UNAVAILABLE", decision.blockers)
            self.assertNotIn("THETA_CLOCK_BLOCK", decision.blockers)
        put = self.evaluate(
            frame_kw={
                "opening_range_state": "BREAKOUT_DOWN",
                "atm_put_theta": None,
            }
        )
        self.assertIsNotNone(put.candidate)
        self.assertIsNone(put.candidate.theta_decay_per_unit)
        self.assertIn("THETA_CLOCK_UNAVAILABLE", put.blockers)

    def test_daily_pnl_unavailable_hard_blocker(self):
        decision = self.evaluate(daily_pnl_available=False)
        self.assertIn("DAILY_PNL_UNAVAILABLE", decision.blockers)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            RiskEngine(RiskConfig(max_trade_risk_inr=0))
        with self.assertRaises(ValueError):
            RiskEngine(
                RiskConfig(
                    earliest_entry=time(15, 0), latest_entry=time(10, 0)
                )
            )
        with self.assertRaises(ValueError):
            RiskEngine(
                RiskConfig(
                    expiry_entry_cutoff=time(15, 0),
                    expiry_flat_time=time(14, 0),
                )
            )


if __name__ == "__main__":
    unittest.main()
