import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from trading_bot.agent_brain import (
    AgentBrainError,
    build_context,
    build_parser,
    do_record,
)
from trading_bot.features import IST
from trading_bot.storage import DuckDBStore, MarketDataRow

NOW = datetime(2026, 9, 18, 12, 30, 0, tzinfo=IST)


def _seed_row(**kw):
    values = dict(
        time=NOW,
        nifty_price=23315.2,
        india_vix=13.5,
        expiry_date=date(2026, 9, 22),
        atm_strike=23300.0,
        atm_call_instrument_key="NSE_FO|56985",
        atm_put_instrument_key="NSE_FO|56994",
        atm_call_price=112.6,
        atm_put_price=88.4,
        data_is_stale=False,
        session_state="MIDDAY",
        relative_volume=1.8,
        opening_range_state="BREAKOUT_UP",
        opening_range_width=68.75,
        iv_percentile=None,
        bar_time=NOW,
        spot_bar_open=23300.0,
        spot_bar_high=23320.0,
        spot_bar_low=23298.0,
        spot_bar_close=23315.0,
        chain_window=json.dumps([{"strike": 23300, "ce_mid": 112.6}]),
        # Python decision artifacts — must NOT leak into the brief:
        gate_reasons=json.dumps(["SHADOW_MODE", "NO_ORB_BREAKOUT"]),
        shadow_candidate=json.dumps({"action": "LONG_CALL", "entry_price": 120.0}),
        block_reason="SHADOW_MODE",
    )
    values.update(kw)
    return MarketDataRow(**values)


class BuildContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "t.duckdb"

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_market_data(self):
        with DuckDBStore(self.db) as store:
            ctx = build_context(store, fetch_status="OK")
        self.assertEqual(ctx["status"], "NO_MARKET_DATA")

    def test_context_has_analytics_and_no_decision_fields(self):
        with DuckDBStore(self.db) as store:
            store.upsert_market_data(_seed_row())
            ctx = build_context(store, fetch_status="OK")

        self.assertEqual(ctx["status"], "CONTEXT")
        self.assertEqual(ctx["analytics"]["relative_volume"], 1.8)
        self.assertEqual(ctx["analytics"]["opening_range_state"], "BREAKOUT_UP")
        self.assertEqual(ctx["meta"]["nifty_spot"], 23315.2)
        self.assertEqual(ctx["options"]["atm_strike"], 23300.0)
        self.assertIsInstance(ctx["options"]["chain_window"], list)
        self.assertIn("23300", ctx["price_action"]["spot_1m_csv"])

        # The Python verdict must be entirely absent from the brief.
        blob = json.dumps(ctx, default=str)
        self.assertNotIn("gate_reasons", blob)
        self.assertNotIn("shadow_candidate", blob)
        self.assertNotIn("NO_ORB_BREAKOUT", blob)


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "t.duckdb"
        self.parser = build_parser()

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, argv):
        args = self.parser.parse_args(["record", *argv])
        with DuckDBStore(self.db) as store:
            result = do_record(store, args, NOW)
            recent = store.recent_agent_decisions(limit=5)
        return result, recent

    def test_valid_trade_recorded(self):
        result, recent = self._record(
            [
                "--action", "LONG_CALL",
                "--strike", "23300",
                "--instrument-key", "NSE_FO|56985",
                "--entry-price", "112.6",
                "--stop-price", "95.0",
                "--target-price", "150.0",
                "--confidence", "0.7",
                "--setup-quality", "B",
                "--source", "https://example.com/news",
                "--rationale", "Breakout up on strong volume.",
            ]
        )
        self.assertEqual(result["status"], "RECORDED")
        self.assertEqual(len(recent), 1)
        row = recent[0]
        self.assertEqual(row["action"], "LONG_CALL")
        self.assertEqual(row["entry_price"], 112.6)
        self.assertEqual(row["stop_price"], 95.0)
        self.assertEqual(row["target_price"], 150.0)
        self.assertEqual(json.loads(row["sources"]), ["https://example.com/news"])

    def test_no_trade_recorded(self):
        result, recent = self._record(
            ["--action", "NO_TRADE", "--rationale", "Chop, no edge."]
        )
        self.assertEqual(result["status"], "RECORDED")
        self.assertEqual(recent[0]["action"], "NO_TRADE")
        self.assertIsNone(recent[0]["entry_price"])

    def test_trade_queues_paper_order_with_market_context(self):
        inbox = Path(self.tmp.name) / "paper-inbox"
        args = self.parser.parse_args(
            [
                "record", "--action", "LONG_PUT", "--strike", "23300",
                "--instrument-key", "NSE_FO|56994", "--entry-price", "88.4",
                "--stop-price", "75.0", "--target-price", "115.0",
                "--rationale", "Breakdown.",
            ]
        )
        with DuckDBStore(self.db) as store:
            store.upsert_market_data(_seed_row(lot_size=65))
            result = do_record(store, args, NOW, inbox=inbox)
        self.assertTrue(result["paper_order_queued"])
        queued = json.loads((inbox / f"{result['decision_id']}.json").read_text())
        self.assertEqual(queued["action"], "LONG_PUT")
        self.assertEqual(queued["entry_price"], 88.4)
        self.assertEqual(queued["lot_size"], 65)
        self.assertEqual(queued["expiry_date"], "2026-09-22")
        self.assertEqual(queued["india_vix"], 13.5)
        self.assertEqual(datetime.fromisoformat(queued["decided_at"]), NOW)

    def test_no_trade_does_not_queue_paper_order(self):
        inbox = Path(self.tmp.name) / "paper-inbox"
        args = self.parser.parse_args(["record", "--action", "NO_TRADE", "--rationale", "Chop."])
        with DuckDBStore(self.db) as store:
            result = do_record(store, args, NOW, inbox=inbox)
        self.assertNotIn("paper_order_queued", result)
        self.assertFalse(inbox.exists())

    def test_no_trade_with_prices_rejected(self):
        with self.assertRaises(AgentBrainError):
            self._record(
                ["--action", "NO_TRADE", "--entry-price", "100",
                 "--rationale", "x"]
            )

    def test_bad_level_order_rejected(self):
        with self.assertRaises(AgentBrainError):
            self._record(
                [
                    "--action", "LONG_CALL", "--strike", "23300",
                    "--instrument-key", "K",
                    "--entry-price", "100", "--stop-price", "120",
                    "--target-price", "150", "--rationale", "x",
                ]
            )

    def test_trade_missing_strike_rejected(self):
        with self.assertRaises(AgentBrainError):
            self._record(
                [
                    "--action", "LONG_PUT",
                    "--entry-price", "100", "--stop-price", "90",
                    "--target-price", "130", "--rationale", "x",
                ]
            )


if __name__ == "__main__":
    unittest.main()
