import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from trading_bot.advisory import (
    ADVICE_SCHEMA,
    ENGINE_VERSION,
    PROMPT_SHA256,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    TOLERATED_SHADOW_BLOCKERS,
    Advice,
    AdviceRunResult,
    AdviceService,
    AdviceValidationError,
    SnapshotBuilder,
    SnapshotError,
    advice_payload,
    format_shadow_alert,
    validate_advice,
)
from trading_bot.llm import LLMTransportError
from trading_bot.storage import DuckDBStore, MarketDataRow

IST = ZoneInfo("Asia/Kolkata")
CAPTURED = datetime(2026, 9, 22, 10, 0, 0, tzinfo=IST)

CANDIDATE = {
    "action": "LONG_CALL",
    "instrument_key": "NSE_FO|C24050",
    "strike": 24050.0,
    "entry_price": 100.0,
    "stop_price": 86.8,
    "provisional_target_price": 113.2,
    "risk_per_unit": 13.2,
    "provisional_reward_per_unit": 13.2,
    "risk_budget_inr": 2500.0,
    "lots": 2,
    "quoted_spread": 1.0,
    "cost_1_lot": {"per_unit": 0.7, "breakeven_ticks": 14.0, "total": 45.5},
    "cost_5_lots": {"per_unit": 0.6, "breakeven_ticks": 12.0},
    "sized_cost": {"per_unit": 0.68, "breakeven_ticks": 13.6},
    "level_source": "CALIBRATED_MAE_MFE",
    "calibration_sample_size": 60,
    "theta_decay_per_unit": 0.23377,
    "theta_required_underlying_move": 2.12345,
}


def market_row(**overrides):
    row = dict(
        time=CAPTURED,
        captured_at=CAPTURED,
        shadow_candidate=json.dumps(CANDIDATE),
        chain_window=json.dumps(
            [
                {
                    "strike": 24050.0,
                    "ce_mid": 100.5,
                    "pe_mid": 89.5,
                    "ce_oi": 500,
                    "pe_oi": 700,
                    "ce_iv": 11.5,
                    "pe_iv": 12.0,
                    "ce_delta": 0.55,
                    "pe_delta": -0.45,
                },
                {"strike": 24100.0, "ce_mid": None},
            ]
        ),
        session_state="PRIME",
        is_expiry_day=False,
        minutes_to_derivatives_close=340,
        data_is_stale=False,
        gate_reasons=json.dumps(["SHADOW_MODE", "EXPECTED_MFE_UNAVAILABLE"]),
        gate_warnings=json.dumps(["VWAP_IS_MINUTE_BAR_PROXY"]),
        bar_time=CAPTURED,
        spot_bar_open=24000.04,
        spot_bar_high=24010.0,
        spot_bar_low=23990.0,
        spot_bar_close=24005.0,
        nifty_future_price=24080.0,
        atm_iv=11.756789,
        spread=0.01,
        iv_percentile=40.0,
        call_oi_walls=json.dumps([[24100.0, 900]]),
    )
    row.update(overrides)
    return row


def advice_json(**overrides):
    payload = {
        "action": "LONG_CALL",
        "confidence": 0.7,
        "setup_quality": "B",
        "entry_price": 100.0,
        "stop_price": 86.8,
        "target_price": 113.2,
        "idea_fails_if": "Invalid below 86.8.",
        "data_conflict": False,
        "reason": "ORB breakout with clean gates.",
    }
    payload.update(overrides)
    return json.dumps(payload)


def snapshot():
    return SnapshotBuilder().build(
        market_row(), [market_row()], CAPTURED + timedelta(milliseconds=500)
    )


class FakeStore:
    def __init__(self, latest=None, recent=None):
        self.latest = latest
        self.recent = recent if recent is not None else ([latest] if latest else [])
        self.advice = []

    def latest_market_data(self):
        return self.latest

    def recent_market_data(self, limit=15, through=None):
        return self.recent

    def model_advice_exists(self, context_to, prompt_hash):
        return any(
            row.context_to == context_to and row.prompt_hash == prompt_hash
            for row in self.advice
        )

    def insert_model_advice(self, row):
        self.advice.append(row)


class FakeLLM:
    model = "test-model"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def generate(self, system_prompt, snapshot_json, output_schema, repair_error=None):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "snapshot": snapshot_json,
                "schema": output_schema,
                "repair_error": repair_error,
            }
        )
        item = self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]
        if isinstance(item, Exception):
            raise item
        return item


def make_service(store, outputs, now=None):
    return AdviceService(
        store, FakeLLM(outputs), now=now or (lambda: CAPTURED + timedelta(milliseconds=500))
    )


class PromptTests(unittest.TestCase):
    def test_prompt_hash_and_version(self):
        self.assertEqual(PROMPT_VERSION, "v1")
        self.assertEqual(ENGINE_VERSION, "0.2.0")
        self.assertEqual(
            PROMPT_SHA256,
            "88847bbecb7351bdb316705461c90705ef4a901f1baad230e131d25c3cebb2c5",
        )
        self.assertIn("LONG_CALL", SYSTEM_PROMPT)


class SnapshotBuilderTests(unittest.TestCase):
    def test_snapshot_structure(self):
        snap = snapshot()
        self.assertEqual(snap["meta"]["engine_version"], "0.2.0")
        self.assertEqual(snap["meta"]["trigger"], "periodic")
        self.assertTrue(snap["meta"]["shadow_mode"])
        self.assertEqual(snap["meta"]["snapshot_age_ms"], 500)
        self.assertEqual(snap["regime"]["session_state"], "PRIME")
        self.assertTrue(snap["regime"]["data_ok"])
        self.assertEqual(
            snap["gates"]["blockers"],
            ["SHADOW_MODE", "EXPECTED_MFE_UNAVAILABLE"],
        )
        self.assertEqual(
            snap["spot_1m_csv"],
            "ts,o,h,l,c\n10:00,24000.0,24010.0,23990.0,24005.0",
        )
        self.assertEqual(
            snap["chain_csv"].splitlines()[0],
            "strike,ce_mid,pe_mid,ce_oi,pe_oi,ce_iv,pe_iv,ce_delta,pe_delta",
        )
        self.assertEqual(
            snap["chain_csv"].splitlines()[1],
            "24050.0,100.50,89.50,500,700,11.50,12.00,0.55,-0.45",
        )
        self.assertEqual(
            snap["chain_csv"].splitlines()[2],
            "24100.0,null,null,null,null,null,null,null,null",
        )
        self.assertEqual(snap["features"]["atm_iv"], 11.7568)
        self.assertEqual(snap["features"]["call_oi_walls"], [[24100.0, 900]])

    def test_candidate_redaction_and_cost_summary(self):
        cand = snapshot()["candidate"]
        self.assertEqual(
            set(cand),
            {
                "action", "instrument_key", "strike", "entry_price",
                "stop_price", "provisional_target_price", "risk_per_unit",
                "provisional_reward_per_unit", "cost_1_lot", "cost_5_lots",
                "level_source", "calibration_sample_size",
                "theta_decay_per_unit", "theta_required_underlying_move",
            },
        )
        self.assertEqual(cand["entry_price"], 100.0)
        self.assertEqual(cand["level_source"], "CALIBRATED_MAE_MFE")
        self.assertEqual(cand["calibration_sample_size"], 60)
        self.assertEqual(cand["theta_decay_per_unit"], 0.23377)
        self.assertEqual(cand["theta_required_underlying_move"], 2.12345)
        self.assertEqual(
            cand["cost_1_lot"], {"per_unit": 0.7, "breakeven_ticks": 14.0}
        )
        self.assertNotIn("lots", cand)
        self.assertNotIn("risk_budget_inr", cand)
        self.assertNotIn("sized_cost", cand)
        serialized = json.dumps(snapshot())
        self.assertNotIn("24080.0", serialized.replace("risk_per_unit", ""))
        self.assertNotIn("nifty_future_price", serialized)

    def test_calibration_context_in_features(self):
        snap = SnapshotBuilder().build(
            market_row(
                tod_median_30m_range=55.55555,
                daily_net_pnl=-120.5,
                expected_mfe_per_unit=12.34567,
                calibration_sample_size=60,
                calibrated_mae_p90=2.34567,
            ),
            [market_row()],
            CAPTURED + timedelta(milliseconds=100),
        )
        features = snap["features"]
        self.assertEqual(features["tod_median_30m_range"], 55.5555)
        self.assertEqual(features["daily_net_pnl"], -120.5)
        self.assertEqual(features["expected_mfe_per_unit"], 12.3457)
        self.assertEqual(features["calibration_sample_size"], 60)
        self.assertEqual(features["calibrated_mae_p90"], 2.3457)

    def test_no_forbidden_keys_recursively(self):
        forbidden = {
            "lots", "risk_budget_inr", "sized_cost", "nifty_future_price"
        }

        def keys_of(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertNotIn(key, forbidden)
                    keys_of(item)
            elif isinstance(value, list):
                for item in value:
                    keys_of(item)

        keys_of(snapshot())

    def test_snapshot_size_still_bounded(self):
        serialized = json.dumps(snapshot(), separators=(",", ":"))
        self.assertLess(len(serialized.encode("utf-8")), 12000)

    def test_snapshot_age_and_missing_inputs(self):
        with self.assertRaises(SnapshotError):
            SnapshotBuilder().build(
                market_row(), [], CAPTURED + timedelta(seconds=3)
            )
        with self.assertRaises(SnapshotError):
            SnapshotBuilder().build(
                market_row(captured_at=None), [], CAPTURED
            )
        with self.assertRaises(SnapshotError):
            SnapshotBuilder().build(
                market_row(shadow_candidate=None), [], CAPTURED
            )
        with self.assertRaises(SnapshotError):
            SnapshotBuilder().build(
                market_row(chain_window=None), [], CAPTURED
            )

    def test_recent_rows_max15_and_incomplete_skipped(self):
        rows = []
        for i in range(20):
            rows.append(
                market_row(
                    bar_time=CAPTURED - timedelta(minutes=20 - i),
                    spot_bar_open=float(i),
                )
            )
        rows.append(market_row(bar_time=CAPTURED + timedelta(minutes=1),
                               spot_bar_open=None))
        snap = SnapshotBuilder().build(
            market_row(), rows, CAPTURED + timedelta(milliseconds=100)
        )
        lines = snap["spot_1m_csv"].splitlines()
        self.assertEqual(len(lines), 15)

    def test_chain_window_max9(self):
        window = [
            {
                "strike": 24000.0 + i * 50,
                "ce_mid": 1.0, "pe_mid": 1.0, "ce_oi": 1, "pe_oi": 1,
                "ce_iv": 1.0, "pe_iv": 1.0, "ce_delta": 0.1, "pe_delta": -0.1,
            }
            for i in range(12)
        ]
        snap = SnapshotBuilder().build(
            market_row(chain_window=json.dumps(window)),
            [market_row()],
            CAPTURED + timedelta(milliseconds=100),
        )
        self.assertEqual(len(snap["chain_csv"].splitlines()), 10)


class ValidateAdviceTests(unittest.TestCase):
    def test_theta_and_calibration_numbers_pass_provenance(self):
        advice = validate_advice(
            advice_json(
                reason="Theta 0.23377 manageable with 2.12345 required move."
            ),
            snapshot(),
        )
        self.assertEqual(advice.action, "LONG_CALL")
        advice = validate_advice(
            advice_json(reason="Calibration sample 60 supports 0.23377."),
            snapshot(),
        )
        self.assertEqual(advice.action, "LONG_CALL")

    def test_valid_long_call(self):
        advice = validate_advice(advice_json(), snapshot())
        self.assertEqual(advice.action, "LONG_CALL")
        self.assertEqual(advice.entry_price, 100.0)
        self.assertEqual(advice.stop_price, 86.8)
        self.assertEqual(advice.target_price, 113.2)

    def test_invalid_json_and_schema(self):
        for raw, code in (
            ("not json", "INVALID_JSON"),
            ("[]", "SCHEMA"),
            (json.dumps({}), "SCHEMA"),
            (advice_json(extra=1), "SCHEMA"),
            (advice_json(confidence=True), "SCHEMA"),
            (advice_json(confidence=1.5), "SCHEMA"),
            (advice_json(setup_quality="D"), "SCHEMA"),
            (advice_json(reason="  "), "SCHEMA"),
        ):
            with self.assertRaises(AdviceValidationError) as ctx:
                validate_advice(raw, snapshot())
            self.assertEqual(ctx.exception.code, code)

    def test_reason_too_long(self):
        with self.assertRaises(AdviceValidationError) as ctx:
            validate_advice(
                advice_json(reason=" ".join(["word"] * 26)), snapshot()
            )
        self.assertEqual(ctx.exception.code, "REASON_TOO_LONG")

    def test_action_and_level_checks(self):
        snap = snapshot()
        with self.assertRaises(AdviceValidationError) as ctx:
            validate_advice(advice_json(action="LONG_PUT"), snap)
        self.assertEqual(ctx.exception.code, "ACTION_MISMATCH")
        with self.assertRaises(AdviceValidationError) as ctx:
            validate_advice(advice_json(stop_price=87.0), snap)
        self.assertEqual(ctx.exception.code, "LEVEL_MISMATCH")
        with self.assertRaises(AdviceValidationError) as ctx:
            validate_advice(
                advice_json(stop_price=100.0, target_price=113.2), snap
            )
        self.assertEqual(ctx.exception.code, "LEVEL_MISMATCH")
        with self.assertRaises(AdviceValidationError) as ctx:
            validate_advice(
                advice_json(action="NO_TRADE", entry_price=100.0), snap
            )
        self.assertEqual(ctx.exception.code, "LEVEL_MISMATCH")

    def test_no_trade_valid(self):
        advice = validate_advice(
            advice_json(
                action="NO_TRADE",
                entry_price=None,
                stop_price=None,
                target_price=None,
                idea_fails_if="No trade was authorized.",
            ),
            snapshot(),
        )
        self.assertEqual(advice.action, "NO_TRADE")
        self.assertIsNone(advice.entry_price)

    def test_numeric_provenance(self):
        snap = snapshot()
        with self.assertRaises(AdviceValidationError) as ctx:
            validate_advice(
                advice_json(idea_fails_if="Invalid below 99.9."), snap
            )
        self.assertEqual(ctx.exception.code, "NUMERIC_PROVENANCE")
        self.assertTrue(ctx.exception.hallucination_event)
        advice = validate_advice(
            advice_json(idea_fails_if="Invalid below 86.8 at 100.0."), snap
        )
        self.assertEqual(advice.action, "LONG_CALL")

    def test_provenance_allows_csv_numbers(self):
        snap = snapshot()
        advice = validate_advice(
            advice_json(idea_fails_if="Invalid below 86.8 near 24005.0."),
            snap,
        )
        self.assertEqual(advice.action, "LONG_CALL")
        advice2 = validate_advice(
            advice_json(reason="Chain mid 100.5 confirms.", ), snap
        )
        self.assertEqual(advice2.action, "LONG_CALL")

    def test_strict_json_and_prohibited_language(self):
        snap = snapshot()
        for bad in ("NaN", "Infinity", "-Infinity"):
            with self.assertRaises(AdviceValidationError) as ctx:
                validate_advice(
                    advice_json().replace("0.7", bad), snap
                )
            self.assertEqual(ctx.exception.code, "INVALID_JSON")
        for phrase in (
            "guaranteed move",
            "Sure breakout",
            "this is certain",
            "price must rise",
            "price must fall",
            "buy 2 lots",
            "use leverage",
            "position size small",
        ):
            with self.assertRaises(AdviceValidationError) as ctx:
                validate_advice(
                    advice_json(idea_fails_if=phrase + " below 86.8."), snap
                )
            self.assertEqual(ctx.exception.code, "PROHIBITED_LANGUAGE")
        advice = validate_advice(
            advice_json(
                reason="ORB breakout, buying pressure evident, call held."
            ),
            snap,
        )
        self.assertEqual(advice.action, "LONG_CALL")


class AdviceServiceTests(unittest.TestCase):
    def test_no_market_data(self):
        store = FakeStore(latest=None)
        result = make_service(store, [advice_json()]).run_once()
        self.assertEqual(result.status, "SKIPPED")
        self.assertEqual(result.fallback_reason, "NO_MARKET_DATA")
        self.assertEqual(store.advice, [])

    def test_no_shadow_candidate(self):
        store = FakeStore(latest=market_row(shadow_candidate=None))
        clientless = AdviceService(
            store, FakeLLM([advice_json()]),
            now=lambda: CAPTURED + timedelta(milliseconds=100),
        )
        result = clientless.run_once()
        self.assertEqual(result.status, "SKIPPED")
        self.assertEqual(result.fallback_reason, "NO_SHADOW_CANDIDATE")

    def test_hard_blockers_skip_without_model_call(self):
        store = FakeStore(
            latest=market_row(
                gate_reasons=json.dumps(["SHADOW_MODE", "STALE_DATA"])
            )
        )
        client = FakeLLM([advice_json()])
        service = AdviceService(
            store, client, now=lambda: CAPTURED + timedelta(milliseconds=100)
        )
        result = service.run_once()
        self.assertEqual(result.status, "SKIPPED")
        self.assertEqual(result.fallback_reason, "ENGINE_BLOCK:STALE_DATA")
        self.assertEqual(client.calls, [])
        self.assertEqual(store.advice, [])
        self.assertIn("STALE_DATA", result.fallback_reason)
        self.assertTrue(
            TOLERATED_SHADOW_BLOCKERS.issuperset({"SHADOW_MODE"})
        )

    def test_snapshot_error_skips(self):
        store = FakeStore(latest=market_row(chain_window=None))
        client = FakeLLM([advice_json()])
        service = AdviceService(
            store, client, now=lambda: CAPTURED + timedelta(milliseconds=100)
        )
        result = service.run_once()
        self.assertEqual(result.status, "SKIPPED")
        self.assertTrue(result.fallback_reason.startswith("SNAPSHOT:"))
        self.assertEqual(client.calls, [])

    def test_advised_persists(self):
        store = FakeStore(latest=market_row())
        service = make_service(store, [advice_json()])
        result = service.run_once()
        self.assertEqual(result.status, "ADVISED")
        self.assertIsNotNone(result.advice_id)
        self.assertEqual(result.advice.action, "LONG_CALL")
        self.assertIsNone(result.fallback_reason)
        self.assertEqual(len(store.advice), 1)
        row = store.advice[0]
        self.assertEqual(row.action, "LONG_CALL")
        self.assertEqual(row.model_name, "test-model")
        self.assertEqual(row.source, "shadow")
        self.assertEqual(row.instrument_key, "NSE_FO|C24050")
        self.assertEqual(row.strike, 24050.0)
        self.assertEqual(row.prompt_hash, PROMPT_SHA256)
        self.assertFalse(row.reask_used)
        self.assertFalse(row.hallucination_event)
        self.assertEqual(row.exact_model_output, advice_json())
        self.assertIn("system_prompt", row.exact_model_input)
        self.assertEqual(len(json.loads(row.model_attempts)), 1)

    def test_validation_error_reasks_once(self):
        store = FakeStore(latest=market_row())
        client = FakeLLM(["garbage", advice_json()])
        service = AdviceService(
            store, client, now=lambda: CAPTURED + timedelta(milliseconds=100)
        )
        result = service.run_once()
        self.assertEqual(result.status, "ADVISED")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[1]["repair_error"], "INVALID_JSON")
        row = store.advice[0]
        self.assertTrue(row.reask_used)
        self.assertEqual(len(json.loads(row.model_attempts)), 2)

    def test_second_validation_failure_falls_back(self):
        store = FakeStore(latest=market_row())
        client = FakeLLM(["garbage", "still bad"])
        service = AdviceService(
            store, client, now=lambda: CAPTURED + timedelta(milliseconds=100)
        )
        result = service.run_once()
        self.assertEqual(result.status, "FALLBACK")
        self.assertEqual(result.fallback_reason, "INVALID_JSON")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(result.advice.action, "NO_TRADE")
        self.assertEqual(result.advice.confidence, 0.0)
        self.assertIsNone(result.advice.entry_price)

    def test_transport_error_no_reask(self):
        store = FakeStore(latest=market_row())
        client = FakeLLM([LLMTransportError("timeout")])
        service = AdviceService(
            store, client, now=lambda: CAPTURED + timedelta(milliseconds=100)
        )
        result = service.run_once()
        self.assertEqual(result.status, "FALLBACK")
        self.assertEqual(result.fallback_reason, "LLMTransportError")
        self.assertEqual(len(client.calls), 1)
        row = store.advice[0]
        self.assertFalse(row.reask_used)
        self.assertEqual(row.exact_model_output, "")

    def test_borderline_confidence_and_conflict_demotions(self):
        store = FakeStore(latest=market_row())
        service = make_service(store, [advice_json(confidence=0.5)])
        result = service.run_once()
        self.assertEqual(result.status, "ADVISED")
        self.assertEqual(result.advice.action, "NO_TRADE")
        self.assertIsNone(result.advice.entry_price)
        self.assertEqual(result.fallback_reason, "BORDERLINE_CONFIDENCE")

        store2 = FakeStore(latest=market_row())
        service2 = make_service(store2, [advice_json(data_conflict=True)])
        result2 = service2.run_once()
        self.assertEqual(result2.advice.action, "NO_TRADE")
        self.assertEqual(result2.fallback_reason, "DATA_CONFLICT")
        self.assertTrue(result2.advice.data_conflict)

    def test_duplicate_run_skips_already_advised(self):
        store = FakeStore(latest=market_row())
        service = make_service(store, [advice_json()])
        first = service.run_once()
        self.assertEqual(first.status, "ADVISED")
        client2 = FakeLLM([advice_json()])
        service2 = AdviceService(
            store, client2,
            now=lambda: CAPTURED + timedelta(milliseconds=100),
        )
        second = service2.run_once()
        self.assertEqual(second.status, "SKIPPED")
        self.assertEqual(second.fallback_reason, "ALREADY_ADVISED")
        self.assertEqual(client2.calls, [])
        self.assertEqual(len(store.advice), 1)


class StorageAdviceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.duckdb"

    def tearDown(self):
        self.tmp.cleanup()

    def _market_row(self):
        from tests.test_storage import make_row
        return make_row(
            captured_at=CAPTURED,
            chain_window=json.dumps([{"strike": 24050.0, "ce_mid": 100.5}]),
        )

    def test_captured_at_and_chain_window_roundtrip(self):
        with DuckDBStore(self.db_path) as store:
            store.upsert_market_data(self._market_row())
            latest = store.latest_market_data()
            self.assertEqual(latest["captured_at"], CAPTURED)
            self.assertEqual(
                json.loads(latest["chain_window"]),
                [{"strike": 24050.0, "ce_mid": 100.5}],
            )

    def test_recent_market_data_chronological_and_through(self):
        with DuckDBStore(self.db_path) as store:
            for i in range(3):
                store.upsert_market_data(self._recent_row(i))
            rows = store.recent_market_data(limit=10)
            self.assertEqual(
                [r["time"] for r in rows],
                [
                    CAPTURED - timedelta(minutes=2),
                    CAPTURED - timedelta(minutes=1),
                    CAPTURED,
                ],
            )
            through = CAPTURED - timedelta(minutes=1)
            rows2 = store.recent_market_data(limit=10, through=through)
            self.assertEqual(len(rows2), 2)
            with self.assertRaises(ValueError):
                store.recent_market_data(limit=0)

    def _recent_row(self, i):
        from tests.test_storage import make_row
        return make_row(
            time_value=CAPTURED - timedelta(minutes=i),
            captured_at=CAPTURED,
        )

    def test_model_advice_insert_get_recent_and_migration(self):
        import duckdb
        from trading_bot.storage import ModelAdviceRow

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(self.db_path))
        conn.execute(
            """
            CREATE TABLE model_advice (
              advice_id VARCHAR PRIMARY KEY,
              advice_at TIMESTAMPTZ NOT NULL,
              context_from TIMESTAMPTZ NOT NULL,
              context_to TIMESTAMPTZ NOT NULL,
              prompt_version VARCHAR NOT NULL,
              model_name VARCHAR NOT NULL,
              action VARCHAR NOT NULL,
              confidence DOUBLE NOT NULL,
              setup_quality VARCHAR NOT NULL,
              entry_price DOUBLE,
              stop_price DOUBLE,
              target_price DOUBLE,
              idea_fails_if VARCHAR NOT NULL,
              data_conflict BOOLEAN NOT NULL,
              reason VARCHAR NOT NULL,
              exact_model_input JSON NOT NULL,
              exact_model_output JSON NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO model_advice VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                "old1", CAPTURED, CAPTURED, CAPTURED, "v0", "m", "NO_TRADE",
                0.0, "C", None, None, None, "n", True, "r", "{}", '{"x":1}',
            ],
        )
        conn.execute(
            """
            CREATE TABLE trade_feedback (
              advice_id VARCHAR PRIMARY KEY REFERENCES model_advice(advice_id),
              feedback_at TIMESTAMPTZ NOT NULL,
              trade_was_taken BOOLEAN NOT NULL,
              entered_at TIMESTAMPTZ,
              exited_at TIMESTAMPTZ,
              actual_entry_price DOUBLE,
              actual_exit_price DOUBLE,
              lots INTEGER,
              user_verdict VARCHAR NOT NULL,
              mae DOUBLE,
              mfe DOUBLE,
              user_notes VARCHAR
            )
            """
        )
        conn.execute(
            "INSERT INTO trade_feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                "old1", CAPTURED, True, CAPTURED, CAPTURED,
                100.0, 110.0, 1, "WORKED", 1.0, 10.0, "ok",
            ],
        )
        conn.close()
        with DuckDBStore(self.db_path) as store:
            info = {
                r[1]: r[2]
                for r in store._connection()
                .execute("PRAGMA table_info('model_advice')")
                .fetchall()
            }
            self.assertEqual(info["exact_model_output"], "JSON")
            self.assertEqual(info["exact_model_output_raw"], "VARCHAR")
            for name in (
                "source", "prompt_hash", "latency_ms", "fallback_reason",
                "model_attempts", "hallucination_event",
            ):
                self.assertIn(name, info)
            old = store.get_model_advice("old1")
            self.assertEqual(old["exact_model_output"], '{"x":1}')
            self.assertEqual(json.loads(old["model_attempts"]), [])
            feedback = store._connection().execute(
                "SELECT advice_id, user_verdict FROM trade_feedback"
            ).fetchall()
            self.assertEqual(feedback, [("old1", "WORKED")])
            tables = {
                r[0]
                for r in store._connection()
                .execute("SHOW TABLES")
                .fetchall()
            }
            self.assertNotIn("trade_feedback_backup", tables)
            self.assertTrue(
                store.model_advice_exists(CAPTURED, "v0") is False
            )

            row = ModelAdviceRow(
                advice_id="a1",
                advice_at=CAPTURED + timedelta(minutes=1),
                context_from=CAPTURED - timedelta(minutes=5),
                context_to=CAPTURED,
                prompt_version="v1",
                model_name="m",
                action="LONG_CALL",
                confidence=0.7,
                setup_quality="B",
                entry_price=100.0,
                stop_price=86.8,
                target_price=113.2,
                idea_fails_if="x",
                data_conflict=False,
                reason="r",
                exact_model_input="{}",
                exact_model_output="{malformed raw",
                source="shadow",
                instrument_key="NSE_FO|C24050",
                strike=24050.0,
                prompt_hash="h",
                latency_ms=12.5,
                fallback_reason=None,
                validation_events="[]",
                reask_used=False,
                hallucination_event=False,
                model_attempts='[{"raw":"{malformed raw"}]',
            )
            store.insert_model_advice(row)
            got = store.get_model_advice("a1")
            self.assertEqual(got["exact_model_output"], "{malformed raw")
            self.assertEqual(got["advice_at"], CAPTURED + timedelta(minutes=1))
            self.assertEqual(
                got["context_from"], CAPTURED - timedelta(minutes=5)
            )
            self.assertIsNone(got["fallback_reason"])
            recent = store.recent_model_advice(limit=10)
            self.assertEqual(recent[0]["advice_id"], "a1")
            self.assertEqual(recent[1]["advice_id"], "old1")
            self.assertTrue(store.model_advice_exists(CAPTURED, "h"))
            self.assertFalse(store.model_advice_exists(CAPTURED, "other"))
            self.assertFalse(
                store.model_advice_exists(
                    CAPTURED - timedelta(days=1), "h"
                )
            )
            with self.assertRaises(ValueError):
                store.model_advice_exists(CAPTURED, "  ")

        fresh_path = Path(self.tmp.name) / "fresh.duckdb"
        with DuckDBStore(fresh_path) as store:
            info = {
                r[1]: r[2]
                for r in store._connection()
                .execute("PRAGMA table_info('model_advice')")
                .fetchall()
            }
            self.assertEqual(info["exact_model_output"], "VARCHAR")
            self.assertEqual(info["exact_model_output_raw"], "VARCHAR")


class ShadowAlertTests(unittest.TestCase):
    def test_format_advised_exact(self):
        result = AdviceRunResult(
            status="ADVISED",
            advice_id="id1",
            advice=Advice(
                "LONG_CALL", 0.7, "B", 100.0, 86.8, 113.2,
                "Invalid below 86.8.", False, "ORB breakout.",
            ),
            fallback_reason=None,
            snapshot={
                "candidate": {"strike": 24050.0},
                "meta": {"ts_ist": "2026-09-22T10:00:00+05:30"},
            },
        )
        self.assertEqual(
            format_shadow_alert(result),
            "PAPER TRADE TEST\n"
            "Time: 2026-09-22T10:00:00+05:30\n"
            "Decision ID: id1\n"
            "Decision: BUY A CALL\n"
            "Option: NIFTY 24050.00 CALL\n"
            "Buy price: ₹100.00\n"
            "Stop price: ₹86.80\n"
            "Sell target: ₹113.20\n"
            "Setup quality: B\n"
            "Confidence label: 0.70\n"
            "Reason: ORB breakout.\n"
            "Invalid if: Invalid below 86.8.\n"
            "Paper trade only. Do not place a real order.\n"
            "SHADOW ONLY - DO NOT EXECUTE",
        )
        text = format_shadow_alert(result)
        self.assertNotIn("lot", text.lower())
        self.assertNotIn("risk_budget", text.lower())

    def test_format_fallback_no_trade(self):
        result = AdviceRunResult(
            status="FALLBACK",
            advice_id="id2",
            advice=Advice(
                "NO_TRADE", 0.0, "C", None, None, None,
                "No trade was authorized.", True,
                "Deterministic safety fallback.",
            ),
            fallback_reason="BORDERLINE_CONFIDENCE",
            snapshot={"candidate": {}},
        )
        text = format_shadow_alert(result)
        self.assertIn("Decision: DO NOT BUY", text)
        self.assertNotIn("Buy price:", text)
        self.assertNotIn("Stop price:", text)
        self.assertNotIn("Sell target:", text)
        self.assertIn("System stop reason: BORDERLINE_CONFIDENCE", text)
        self.assertTrue(text.endswith("SHADOW ONLY - DO NOT EXECUTE"))

    def test_format_skipped_empty(self):
        result = AdviceRunResult(
            status="SKIPPED",
            advice_id=None,
            advice=None,
            fallback_reason="NO_MARKET_DATA",
        )
        self.assertEqual(format_shadow_alert(result), "")
        payload = advice_payload(result)
        self.assertEqual(payload["status"], "SKIPPED")
        self.assertIsNone(payload["advice"])
        self.assertEqual(payload["fallback_reason"], "NO_MARKET_DATA")

    def test_cli_once_text_and_json_skipped(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock

        from trading_bot.advisory import run

        class FakeClient:
            model = "m"

        with mock.patch(
            "trading_bot.advisory.OpenAIResponsesClient.from_env",
            return_value=FakeClient(),
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                code = run(
                    [
                        "--db-path", str(self.db_path),
                        "--env-file", str(self.db_path) + ".missing",
                        "--once",
                        "--output", "text",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue().strip(), "SKIPPED: NO_MARKET_DATA")
            out = io.StringIO()
            with redirect_stdout(out):
                code = run(
                    [
                        "--db-path", str(self.db_path),
                        "--env-file", str(self.db_path) + ".missing",
                        "--once",
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["status"], "SKIPPED")
            self.assertEqual(payload["fallback_reason"], "NO_MARKET_DATA")

    @property
    def db_path(self):
        if not hasattr(self, "_db_path"):
            self._tmp = tempfile.TemporaryDirectory()
            self._db_path = Path(self._tmp.name) / "t.duckdb"
        return self._db_path


class ConfigAllowlistTests(unittest.TestCase):
    def test_allowlist_names_and_no_overwrite(self):
        import os
        from unittest import mock

        from trading_bot.config import load_env_file

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                "OPENAI_API_KEY=k1\nTRADING_BOT_LLM_MODEL=m1\n"
                "UPSTOX_ACCESS_TOKEN=tok\n"
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertTrue(
                    load_env_file(
                        path,
                        names=("OPENAI_API_KEY", "TRADING_BOT_LLM_MODEL"),
                    )
                )
                self.assertEqual(os.environ["OPENAI_API_KEY"], "k1")
                self.assertEqual(os.environ["TRADING_BOT_LLM_MODEL"], "m1")
                self.assertNotIn("UPSTOX_ACCESS_TOKEN", os.environ)
            with mock.patch.dict(
                os.environ, {"OPENAI_API_KEY": "existing"}, clear=True
            ):
                load_env_file(
                    path,
                    names=("OPENAI_API_KEY", "TRADING_BOT_LLM_MODEL"),
                )
                self.assertEqual(os.environ["OPENAI_API_KEY"], "existing")
                self.assertEqual(os.environ["TRADING_BOT_LLM_MODEL"], "m1")


class ToleratedBlockerTests(unittest.TestCase):
    def test_research_blockers_tolerated_not_hard(self):
        from trading_bot.advisory import TOLERATED_SHADOW_BLOCKERS

        self.assertIn(
            "CALIBRATION_HISTORY_INSUFFICIENT", TOLERATED_SHADOW_BLOCKERS
        )
        self.assertIn(
            "THETA_CLOCK_UNAVAILABLE", TOLERATED_SHADOW_BLOCKERS
        )
        self.assertNotIn(
            "DAILY_PNL_UNAVAILABLE", TOLERATED_SHADOW_BLOCKERS
        )
        self.assertNotIn(
            "RISK_BUDGET_TOO_SMALL", TOLERATED_SHADOW_BLOCKERS
        )
        self.assertNotIn(
            "COST_INEFFICIENT_SIZE", TOLERATED_SHADOW_BLOCKERS
        )
        self.assertNotIn("THETA_CLOCK_BLOCK", TOLERATED_SHADOW_BLOCKERS)


if __name__ == "__main__":
    unittest.main()
