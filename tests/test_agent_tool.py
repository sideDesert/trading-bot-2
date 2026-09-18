import io
import json
import tempfile
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from trading_bot.advisory import PROMPT_SHA256, PROMPT_VERSION
from trading_bot.agent_tool import (
    BOUNDARY,
    AgentToolError,
    AgentToolResult,
    AgentToolService,
    _result_payload,
    run,
)
from trading_bot.storage import DuckDBStore, MarketDataRow, ModelAdviceRow

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 9, 22, 10, 0, 0, tzinfo=IST)

CANDIDATE = {
    "action": "LONG_CALL",
    "instrument_key": "NSE_FO|C24050",
    "strike": 24050.0,
    "entry_price": 100.0,
    "stop_price": 86.8,
    "provisional_target_price": 113.2,
    "risk_per_unit": 13.2,
    "provisional_reward_per_unit": 13.2,
    "quoted_spread": 1.0,
    "level_source": "PROVISIONAL_OR_WIDTH",
    "calibration_sample_size": 0,
    "theta_decay_per_unit": 0.23,
    "theta_required_underlying_move": 2.0,
    "cost_1_lot": {"per_unit": 0.7, "breakeven_ticks": 14.0},
    "cost_5_lots": {"per_unit": 0.6, "breakeven_ticks": 12.0},
}

CHAIN_WINDOW = [
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
    }
]


def valid_advice(**kw):
    payload = {
        "action": "LONG_CALL",
        "confidence": 0.7,
        "setup_quality": "B",
        "entry_price": 100.0,
        "stop_price": 86.8,
        "target_price": 113.2,
        "idea_fails_if": "Invalid below 86.8.",
        "data_conflict": False,
        "reason": "ORB breakout.",
    }
    payload.update(kw)
    return json.dumps(payload)


class _StoreView:
    def __init__(self, store, overrides):
        self._store = store
        self._overrides = overrides

    def latest_market_data(self):
        row = dict(self._store.latest_market_data())
        row.update(self._overrides)
        return row

    def __getattr__(self, name):
        return getattr(self._store, name)


class AgentToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.duckdb"
        self.request_dir = Path(self.tmp.name) / "requests"
        self.now = NOW
        self.store = DuckDBStore(self.db_path).initialize()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _service(self):
        return AgentToolService(
            self.store, self.request_dir, now=lambda: self.now
        )

    def _seed_row(self, **kw):
        values = dict(
            time=NOW,
            nifty_price=24005.0,
            india_vix=13.5,
            expiry_date=NOW.date(),
            atm_strike=24000.0,
            atm_call_instrument_key="NSE_FO|C24000",
            atm_put_instrument_key="NSE_FO|P24000",
            atm_call_price=101.0,
            atm_put_price=91.0,
            captured_at=NOW,
            session_state="PRIME",
            data_is_stale=False,
            shadow_candidate=json.dumps(CANDIDATE),
            chain_window=json.dumps(CHAIN_WINDOW),
            gate_reasons=json.dumps(["SHADOW_MODE"]),
        )
        values.update(kw)
        row = MarketDataRow(**values)
        self.store.upsert_market_data(row)
        return row

    def _prepare(self, **kw):
        self._seed_row(**kw)
        return self._service().prepare_latest()

    def test_no_market_data(self):
        result = self._service().prepare_latest()
        self.assertEqual(result.status, "SKIPPED")
        self.assertEqual(result.reason, "NO_MARKET_DATA")

    def test_no_shadow_candidate(self):
        result = self._prepare(shadow_candidate=None)
        self.assertEqual(result.status, "SKIPPED")
        self.assertEqual(result.reason, "NO_SHADOW_CANDIDATE")

    def test_now_ist_stamped_from_tool_clock(self):
        result = self._prepare(shadow_candidate=None)
        self.assertEqual(result.status, "SKIPPED")
        self.assertEqual(result.now_ist, NOW.isoformat())
        payload = _result_payload(result)
        self.assertEqual(payload["now_ist"], NOW.isoformat())

    def test_hard_blockers_no_artifact(self):
        result = self._prepare(
            gate_reasons=json.dumps(["SHADOW_MODE", "STALE_DATA"])
        )
        self.assertEqual(result.status, "NO_TRADE")
        self.assertEqual(result.reason, "ENGINE_BLOCK:STALE_DATA")
        self.assertFalse(self.request_dir.exists())

    def test_cost_and_risk_size_block_paper_trade(self):
        result = self._prepare(
            gate_reasons=json.dumps(
                [
                    "SHADOW_MODE",
                    "COST_INEFFICIENT_SIZE",
                    "RISK_BUDGET_TOO_SMALL",
                ]
            )
        )
        self.assertEqual(result.status, "NO_TRADE")
        self.assertEqual(
            result.reason,
            "ENGINE_BLOCK:COST_INEFFICIENT_SIZE,RISK_BUDGET_TOO_SMALL",
        )
        self.assertFalse(self.request_dir.exists())

    def test_gate_reasons_malformed_json(self):
        self._seed_row()
        service = AgentToolService(
            _StoreView(self.store, {"gate_reasons": "{not json"}),
            self.request_dir,
            now=lambda: self.now,
        )
        result = service.prepare_latest()
        self.assertEqual(result.status, "NO_TRADE")
        self.assertEqual(result.reason, "ENGINE_BLOCK:GATE_STATE_INVALID")
        self.assertFalse(self.request_dir.exists())

    def test_gate_reasons_dict(self):
        result = self._prepare(gate_reasons=json.dumps({"gate": "x"}))
        self.assertEqual(result.status, "NO_TRADE")
        self.assertEqual(result.reason, "ENGINE_BLOCK:GATE_STATE_INVALID")

    def test_gate_reasons_numeric_list(self):
        result = self._prepare(gate_reasons=json.dumps([1, 2]))
        self.assertEqual(result.status, "NO_TRADE")
        self.assertEqual(result.reason, "ENGINE_BLOCK:GATE_STATE_INVALID")

    def test_stale_flag_adds_hard_blocker(self):
        result = self._prepare(
            data_is_stale=True, gate_reasons=json.dumps(["SHADOW_MODE"])
        )
        self.assertEqual(result.status, "NO_TRADE")
        self.assertEqual(result.reason, "ENGINE_BLOCK:STALE_DATA")
        self.assertFalse(self.request_dir.exists())

    def test_boundary_present_for_all_statuses(self):
        for status in (
            "SKIPPED",
            "NO_TRADE",
            "READY",
            "ADVISED",
            "FALLBACK",
            "RETRY",
        ):
            result = AgentToolResult(
                status,
                "req",
                None,
                None,
                "reason",
                request={"request_id": "req"} if status == "READY" else None,
            )
            payload = _result_payload(result)
            self.assertEqual(payload["boundary"], BOUNDARY)
            self.assertEqual(
                payload["boundary"], "SHADOW ONLY - DO NOT EXECUTE"
            )

    def test_submit_recovers_preexisting_db_advice(self):
        result = self._prepare()
        self.assertEqual(result.status, "READY")
        existing_id = str(uuid.uuid4())
        self.store.insert_model_advice(
            ModelAdviceRow(
                advice_id=existing_id,
                advice_at=NOW,
                context_from=NOW,
                context_to=NOW,
                prompt_version=PROMPT_VERSION,
                model_name="other-agent",
                action="NO_TRADE",
                confidence=0.0,
                setup_quality="C",
                entry_price=None,
                stop_price=None,
                target_price=None,
                idea_fails_if="n/a",
                data_conflict=True,
                reason="recovered",
                exact_model_input="{}",
                exact_model_output="{}",
                source="shadow-harness",
                prompt_hash=PROMPT_SHA256,
                fallback_reason="ENGINE_FALLBACK",
            )
        )
        resubmit = self._service().submit(result.request_id, valid_advice())
        self.assertEqual(resubmit.status, "SKIPPED")
        self.assertEqual(resubmit.reason, "ALREADY_SUBMITTED")
        self.assertEqual(resubmit.advice_id, existing_id)
        self.assertEqual(resubmit.advice.action, "NO_TRADE")
        self.assertEqual(self.store.count("model_advice"), 1)
        artifact = json.loads(
            (self.request_dir / f"{result.request_id}.json").read_text()
        )
        self.assertEqual(artifact["status"], "SUBMITTED")
        self.assertEqual(artifact["advice_id"], existing_id)
        self.assertEqual(artifact["fallback_reason"], "ENGINE_FALLBACK")

    def test_ready_artifact_fields(self):
        result = self._prepare()
        self.assertEqual(result.status, "READY")
        self.assertIsNotNone(result.request_id)
        artifact = json.loads(
            (self.request_dir / f"{result.request_id}.json").read_text()
        )
        self.assertEqual(
            set(artifact),
            {
                "request_id", "status", "created_at", "expires_at",
                "prompt_version", "prompt_hash", "system_prompt",
                "output_schema", "snapshot", "context_from",
                "context_to", "exact_model_input", "attempts",
            },
        )
        self.assertEqual(artifact["status"], "PENDING")
        self.assertEqual(artifact["prompt_hash"], PROMPT_SHA256)
        self.assertEqual(artifact["prompt_version"], PROMPT_VERSION)
        self.assertEqual(artifact["attempts"], [])
        expires = datetime.fromisoformat(artifact["expires_at"])
        created = datetime.fromisoformat(artifact["created_at"])
        self.assertEqual((expires - created).total_seconds(), 90)
        self.assertIn("+05:30", artifact["created_at"])
        with mock.patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-secret-123"}
        ):
            self.assertNotIn(
                "sk-secret-123", json.dumps(artifact)
            )

    def test_stale_snapshot(self):
        self._seed_row(captured_at=NOW - timedelta(seconds=3))
        result = self._service().prepare_latest()
        self.assertEqual(result.status, "SKIPPED")
        self.assertTrue(result.reason.startswith("SNAPSHOT:"))

    def test_valid_long_persists(self):
        result = self._prepare()
        submit = self._service().submit(result.request_id, valid_advice())
        self.assertEqual(submit.status, "ADVISED")
        self.assertIsNone(submit.reason)
        row = self.store.get_model_advice(submit.advice_id)
        self.assertEqual(row["source"], "shadow-harness")
        self.assertEqual(row["model_name"], "harness-current-session")
        self.assertEqual(row["action"], "LONG_CALL")
        self.assertEqual(row["exact_model_output"], valid_advice())
        self.assertEqual(row["instrument_key"], "NSE_FO|C24050")

    def test_valid_no_trade(self):
        result = self._prepare()
        submit = self._service().submit(
            result.request_id,
            valid_advice(
                action="NO_TRADE",
                entry_price=None,
                stop_price=None,
                target_price=None,
            ),
        )
        self.assertEqual(submit.status, "ADVISED")
        self.assertEqual(submit.advice.action, "NO_TRADE")

    def test_confidence_and_conflict_demotions(self):
        result = self._prepare()
        submit = self._service().submit(
            result.request_id, valid_advice(confidence=0.5)
        )
        self.assertEqual(submit.status, "FALLBACK")
        self.assertEqual(submit.reason, "BORDERLINE_CONFIDENCE")
        self.assertEqual(submit.advice.action, "NO_TRADE")
        self.assertIsNone(submit.advice.entry_price)

        self.tearDown()
        self.setUp()
        result = self._prepare()
        submit = self._service().submit(
            result.request_id, valid_advice(data_conflict=True)
        )
        self.assertEqual(submit.status, "FALLBACK")
        self.assertEqual(submit.reason, "DATA_CONFLICT")

    def test_retry_then_valid(self):
        result = self._prepare()
        bad = self._service().submit(
            result.request_id, valid_advice(stop_price=50.0)
        )
        self.assertEqual(bad.status, "RETRY")
        self.assertEqual(bad.reason, "LEVEL_MISMATCH")
        self.assertEqual(self.store.count("model_advice"), 0)
        artifact = json.loads(
            (self.request_dir / f"{result.request_id}.json").read_text()
        )
        self.assertEqual(len(artifact["attempts"]), 1)
        self.assertEqual(artifact["attempts"][0]["error"], "LEVEL_MISMATCH")
        good = self._service().submit(result.request_id, valid_advice())
        self.assertEqual(good.status, "ADVISED")
        row = self.store.get_model_advice(good.advice_id)
        self.assertTrue(row["reask_used"])

    def test_second_invalid_fallback(self):
        result = self._prepare()
        self._service().submit(result.request_id, valid_advice(stop_price=50.0))
        final = self._service().submit(
            result.request_id, valid_advice(stop_price=51.0)
        )
        self.assertEqual(final.status, "FALLBACK")
        self.assertEqual(
            final.reason, "HARNESS_VALIDATION:LEVEL_MISMATCH"
        )
        row = self.store.get_model_advice(final.advice_id)
        self.assertEqual(row["action"], "NO_TRADE")
        self.assertEqual(row["source"], "shadow-harness")

    def test_stale_response_falls_back(self):
        result = self._prepare()
        self.now = NOW + timedelta(seconds=120)
        submit = self._service().submit(result.request_id, valid_advice())
        self.assertEqual(submit.status, "FALLBACK")
        self.assertEqual(submit.reason, "HARNESS_RESPONSE_STALE")
        row = self.store.get_model_advice(submit.advice_id)
        self.assertEqual(row["action"], "NO_TRADE")

    def test_prompt_changed(self):
        result = self._prepare()
        path = self.request_dir / f"{result.request_id}.json"
        artifact = json.loads(path.read_text())
        artifact["prompt_hash"] = "tampered"
        path.write_text(json.dumps(artifact))
        with self.assertRaises(AgentToolError) as ctx:
            self._service().submit(result.request_id, valid_advice())
        self.assertEqual(str(ctx.exception), "PROMPT_CHANGED")

    def test_request_id_validation(self):
        for bad in ("not-a-uuid", "../etc", str(NOW), ""):
            with self.assertRaises(AgentToolError):
                self._service().submit(bad, valid_advice())
        with self.assertRaises(AgentToolError):
            self._service().submit(
                "12345678-1234-1234-1234-1234567890ab", valid_advice()
            )

    def test_size_and_name_validation(self):
        result = self._prepare()
        with self.assertRaises(AgentToolError):
            self._service().submit(result.request_id, "x" * 20001)
        with self.assertRaises(AgentToolError):
            self._service().submit(result.request_id, "")
        with self.assertRaises(AgentToolError):
            self._service().submit(
                result.request_id, valid_advice(), agent_name=" " 
            )
        with self.assertRaises(AgentToolError):
            self._service().submit(
                result.request_id, valid_advice(), agent_name="a" * 101
            )

    def test_already_submitted_idempotent(self):
        result = self._prepare()
        first = self._service().submit(result.request_id, valid_advice())
        second = self._service().submit(result.request_id, valid_advice())
        self.assertEqual(second.status, "SKIPPED")
        self.assertEqual(second.reason, "ALREADY_SUBMITTED")
        self.assertEqual(second.advice_id, first.advice_id)
        self.assertEqual(second.advice.action, "LONG_CALL")
        self.assertEqual(self.store.count("model_advice"), 1)

    def test_prepare_after_submit_skips(self):
        result = self._prepare()
        self._service().submit(result.request_id, valid_advice())
        again = self._service().prepare_latest()
        self.assertEqual(again.status, "SKIPPED")
        self.assertEqual(again.reason, "ALREADY_ADVISED")


class AgentToolCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "t.duckdb"
        self.request_dir = Path(self.tmp.name) / "requests"
        self.env_file = Path(self.tmp.name) / "missing.env"

    def _argv(self, *extra):
        return [
            "--db-path", str(self.db_path),
            "--request-dir", str(self.request_dir),
            *extra,
        ]

    def test_prepare_cli_inserts_row_first(self):
        seen = {}

        class FakeCollector:
            def __init__(self, client, store, config):
                seen["client"] = client
                self.store = store

            def run_once(self):
                self.store.upsert_market_data(
                    MarketDataRow(
                        time=datetime.now(IST).replace(
                            second=0, microsecond=0
                        ),
                        nifty_price=24005.0,
                        india_vix=13.5,
                        expiry_date=datetime.now(IST).date(),
                        atm_strike=24000.0,
                        atm_call_instrument_key="NSE_FO|C24000",
                        atm_put_instrument_key="NSE_FO|P24000",
                        atm_call_price=101.0,
                        atm_put_price=91.0,
                        captured_at=datetime.now(IST),
                        session_state="PRIME",
                        data_is_stale=False,
                        shadow_candidate=json.dumps(CANDIDATE),
                        chain_window=json.dumps(CHAIN_WINDOW),
                        gate_reasons=json.dumps(["SHADOW_MODE"]),
                    )
                )
                seen["row_count"] = self.store.count("market_data")

        out = io.StringIO()
        with redirect_stdout(out):
            code = run(
                self._argv("prepare", "--env-file", str(self.env_file)),
                upstox_client_factory=lambda: "fake-client",
                collector_factory=FakeCollector,
            )
        self.assertEqual(code, 0)
        self.assertEqual(seen["client"], "fake-client")
        self.assertEqual(seen["row_count"], 1)
        payload = json.loads(out.getvalue())
        self.assertTrue(payload["ok"])
        self.assertIn(payload["status"], ("READY", "NO_TRADE", "SKIPPED"))
        if payload["status"] == "READY":
            self.assertIn("submit_example", payload)
            self.assertIn("ADVICE_JSON", payload["submit_example"])

    def test_submit_cli_stdin(self):
        store = DuckDBStore(self.db_path).initialize()
        store.upsert_market_data(
            MarketDataRow(
                time=datetime.now(IST).replace(second=0, microsecond=0),
                nifty_price=24005.0,
                india_vix=13.5,
                expiry_date=datetime.now(IST).date(),
                atm_strike=24000.0,
                atm_call_instrument_key="NSE_FO|C24000",
                atm_put_instrument_key="NSE_FO|P24000",
                atm_call_price=101.0,
                atm_put_price=91.0,
                captured_at=datetime.now(IST),
                session_state="PRIME",
                data_is_stale=False,
                shadow_candidate=json.dumps(CANDIDATE),
                chain_window=json.dumps(CHAIN_WINDOW),
                gate_reasons=json.dumps(["SHADOW_MODE"]),
            )
        )
        service = AgentToolService(store, self.request_dir)
        result = service.prepare_latest()
        store.close()
        self.assertEqual(result.status, "READY")
        out = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(valid_advice())):
            with redirect_stdout(out):
                code = run(
                    self._argv(
                        "submit",
                        "--request-id", result.request_id,
                        "--agent-name", "test-agent",
                    )
                )
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"], "ADVISED")
        self.assertEqual(payload["advice"]["action"], "LONG_CALL")
        store = DuckDBStore(self.db_path).initialize()
        row = store.get_model_advice(payload["advice_id"])
        self.assertEqual(row["model_name"], "test-agent")
        self.assertEqual(row["source"], "shadow-harness")
        store.close()


if __name__ == "__main__":
    unittest.main()
