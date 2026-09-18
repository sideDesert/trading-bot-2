import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb

from trading_bot.storage import (
    DuckDBStore,
    MarketDataRow,
    ModelAdviceRow,
    TradeFeedbackRow,
)


def make_row(time_value=None, **overrides):
    values = dict(
        time=time_value or datetime(2026, 9, 22, 9, 15, tzinfo=timezone.utc),
        nifty_price=24000.5,
        india_vix=13.2,
        expiry_date=date(2026, 9, 22),
        atm_strike=24000.0,
        atm_call_instrument_key="NSE_FO|111",
        atm_put_instrument_key="NSE_FO|222",
        atm_call_price=120.5,
        atm_put_price=110.25,
        pcr=0.9,
        call_oi_wall=24500.0,
        put_oi_wall=23500.0,
        spread=0.02,
        source_age_seconds=1.5,
        data_is_stale=False,
        trading_is_blocked=True,
        block_reason="SHADOW_MODE",
    )
    values.update(overrides)
    return MarketDataRow(**values)


class DuckDBStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "sub" / "dir" / "test.duckdb"

    def tearDown(self):
        self.tmp.cleanup()

    def test_initialize_creates_parent_dirs_and_tables(self):
        with DuckDBStore(self.db_path) as store:
            self.assertTrue(self.db_path.exists())
            for table in ("market_data", "model_advice", "trade_feedback"):
                self.assertEqual(store.count(table), 0)

    def test_upsert_and_latest(self):
        with DuckDBStore(self.db_path) as store:
            row = make_row()
            store.upsert_market_data(row)
            latest = store.latest_market_data()
            self.assertEqual(latest["atm_strike"], 24000.0)
            self.assertEqual(latest["atm_call_instrument_key"], "NSE_FO|111")
            self.assertEqual(latest["block_reason"], "SHADOW_MODE")
            self.assertEqual(store.count("market_data"), 1)

    def test_upsert_replaces_same_timestamp(self):
        with DuckDBStore(self.db_path) as store:
            store.upsert_market_data(make_row(nifty_price=1.0))
            store.upsert_market_data(make_row(nifty_price=2.0))
            self.assertEqual(store.count("market_data"), 1)
            self.assertEqual(store.latest_market_data()["nifty_price"], 2.0)

    def test_latest_ordering(self):
        with DuckDBStore(self.db_path) as store:
            store.upsert_market_data(
                make_row(datetime(2026, 9, 22, 9, 16, tzinfo=timezone.utc))
            )
            store.upsert_market_data(
                make_row(
                    datetime(2026, 9, 22, 9, 15, tzinfo=timezone.utc),
                    nifty_price=111.0,
                )
            )
            self.assertEqual(store.count("market_data"), 2)
            self.assertNotEqual(
                store.latest_market_data()["nifty_price"], 111.0
            )

    def test_nullable_prices_persist_as_none(self):
        with DuckDBStore(self.db_path) as store:
            store.upsert_market_data(
                make_row(
                    nifty_price=None,
                    india_vix=None,
                    atm_call_price=None,
                    atm_put_price=None,
                    source_age_seconds=None,
                    chain_age_seconds=7.5,
                    data_is_stale=True,
                    block_reason="STALE_DATA",
                )
            )
            latest = store.latest_market_data()
            self.assertIsNone(latest["nifty_price"])
            self.assertIsNone(latest["india_vix"])
            self.assertIsNone(latest["atm_call_price"])
            self.assertIsNone(latest["atm_put_price"])
            self.assertIsNone(latest["source_age_seconds"])
            self.assertEqual(latest["chain_age_seconds"], 7.5)
            self.assertEqual(latest["block_reason"], "STALE_DATA")

    def test_count_rejects_unknown_table(self):
        with DuckDBStore(self.db_path) as store:
            for bad in ("users", "market_data; DROP TABLE market_data", ""):
                with self.assertRaises(ValueError):
                    store.count(bad)

    def test_use_after_close_raises(self):
        store = DuckDBStore(self.db_path).initialize()
        store.close()
        with self.assertRaises(RuntimeError):
            store.count("market_data")

    def test_json_fields_and_bar_time_roundtrip(self):
        with DuckDBStore(self.db_path) as store:
            row = make_row(
                bar_time=datetime(2026, 9, 22, 9, 14, tzinfo=timezone.utc),
                call_oi_walls=json.dumps([[24100.0, 900], [24000.0, 500]]),
                put_oi_walls=json.dumps([[24000.0, 700]]),
                gate_reasons=json.dumps(["SHADOW_MODE", "STALE_DATA"]),
                gate_warnings=json.dumps(["VWAP_IS_MINUTE_BAR_PROXY"]),
                shadow_candidate=json.dumps({"action": "LONG_CALL", "lots": 2}),
                lot_size=65,
                session_state="OPENING_RANGE",
                is_expiry_day=True,
            )
            store.upsert_market_data(row)
            latest = store.latest_market_data()
            self.assertEqual(
                latest["bar_time"],
                datetime(2026, 9, 22, 9, 14, tzinfo=timezone.utc),
            )
            self.assertEqual(
                json.loads(latest["call_oi_walls"]), [[24100.0, 900], [24000.0, 500]]
            )
            self.assertEqual(json.loads(latest["put_oi_walls"]), [[24000.0, 700]])
            self.assertEqual(
                json.loads(latest["gate_reasons"]), ["SHADOW_MODE", "STALE_DATA"]
            )
            self.assertEqual(
                json.loads(latest["shadow_candidate"]),
                {"action": "LONG_CALL", "lots": 2},
            )
            self.assertEqual(latest["lot_size"], 65)
            self.assertEqual(latest["session_state"], "OPENING_RANGE")
            self.assertTrue(latest["is_expiry_day"])

    def test_migration_adds_new_columns_to_old_table(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(self.db_path))
        conn.execute(
            """
            CREATE TABLE market_data (
              time TIMESTAMPTZ PRIMARY KEY,
              nifty_price DOUBLE,
              india_vix DOUBLE,
              expiry_date DATE,
              atm_strike DOUBLE,
              atm_call_instrument_key VARCHAR,
              atm_put_instrument_key VARCHAR,
              atm_call_price DOUBLE,
              atm_put_price DOUBLE,
              iv_percentile DOUBLE,
              pcr DOUBLE,
              relative_volume DOUBLE,
              vwap_position VARCHAR,
              opening_range_state VARCHAR,
              call_oi_wall DOUBLE,
              put_oi_wall DOUBLE,
              spread DOUBLE,
              source_age_seconds DOUBLE,
              chain_age_seconds DOUBLE,
              data_is_stale BOOLEAN NOT NULL,
              trading_is_blocked BOOLEAN NOT NULL,
              block_reason VARCHAR NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO market_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                datetime(2026, 9, 21, 9, 15, tzinfo=timezone.utc),
                24000.0, 13.0, date(2026, 9, 22), 24000.0,
                "NSE_FO|1", "NSE_FO|2", 100.0, 90.0,
                None, None, None, None, None, None, None,
                None, None, None, False, True, "X",
            ],
        )
        conn.close()
        with DuckDBStore(self.db_path) as store:
            store.upsert_market_data(make_row(lot_size=65, local_gex_sign="NEUTRAL"))
            self.assertEqual(store.count("market_data"), 2)
            latest = store.latest_market_data()
            self.assertEqual(latest["lot_size"], 65)
            self.assertEqual(latest["local_gex_sign"], "NEUTRAL")
            cols = {
                r[1]
                for r in store._connection().execute(
                    "PRAGMA table_info('market_data')"
                ).fetchall()
            }
            for name in (
                "bar_time", "atm_iv", "call_oi_walls", "gate_reasons",
                "shadow_candidate", "bar_age_seconds",
            ):
                self.assertIn(name, cols)

    def test_atm_iv_history_latest_per_day_and_limit(self):
        with DuckDBStore(self.db_path) as store:
            base = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
            store.upsert_market_data(make_row(base, atm_iv=10.0))
            store.upsert_market_data(
                make_row(base + timedelta(hours=1), atm_iv=11.5)
            )
            store.upsert_market_data(
                make_row(base + timedelta(days=1), atm_iv=None)
            )
            store.upsert_market_data(
                make_row(base + timedelta(days=2), atm_iv=-3.0)
            )
            store.upsert_market_data(
                make_row(base + timedelta(days=3), atm_iv=12.5)
            )
            boundary = base + timedelta(days=4)
            store.upsert_market_data(make_row(boundary, atm_iv=99.0))
            history = store.atm_iv_history(before=boundary)
            self.assertEqual(history, [11.5, 12.5])
            with self.assertRaises(ValueError):
                store.atm_iv_history(before=boundary, limit=0)
            capped = store.atm_iv_history(before=boundary, limit=1)
            self.assertEqual(capped, [12.5])

    def test_atm_iv_history_excludes_same_ist_day(self):
        with DuckDBStore(self.db_path) as store:
            prior = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
            same_day_early = datetime(2026, 9, 22, 4, 0, tzinfo=timezone.utc)
            same_day_late = datetime(2026, 9, 22, 5, 0, tzinfo=timezone.utc)
            before = datetime(2026, 9, 22, 6, 0, tzinfo=timezone.utc)
            store.upsert_market_data(make_row(prior, atm_iv=12.5))
            store.upsert_market_data(
                make_row(prior + timedelta(hours=1), atm_iv=13.5)
            )
            store.upsert_market_data(make_row(same_day_early, atm_iv=20.0))
            store.upsert_market_data(make_row(same_day_late, atm_iv=21.0))
            self.assertEqual(store.atm_iv_history(before=before), [13.5])

    def test_shadow_candidate_none_persists_as_null(self):
        with DuckDBStore(self.db_path) as store:
            store.upsert_market_data(make_row(shadow_candidate=None))
            self.assertIsNone(store.latest_market_data()["shadow_candidate"])

    def _advice_row(self, advice_id, **kw):
        values = dict(
            advice_id=advice_id,
            advice_at=datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc),
            context_from=datetime(2026, 9, 22, 9, 45, tzinfo=timezone.utc),
            context_to=datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc),
            prompt_version="v1",
            model_name="agent",
            action="NO_TRADE",
            confidence=0.0,
            setup_quality="C",
            entry_price=None,
            stop_price=None,
            target_price=None,
            idea_fails_if="n/a",
            data_conflict=True,
            reason="r",
            exact_model_input="{}",
            exact_model_output="{}",
            prompt_hash="hash-1",
        )
        values.update(kw)
        return ModelAdviceRow(**values)

    def test_advice_context_unique_index_on_clean_db(self):
        with DuckDBStore(self.db_path) as store:
            self.assertTrue(store._advice_context_unique)
            store.insert_model_advice(self._advice_row("a1"))
            with self.assertRaises(duckdb.ConstraintException):
                store.insert_model_advice(self._advice_row("a2"))
            self.assertEqual(store.count("model_advice"), 1)

    def test_advice_context_legacy_duplicates_preserved(self):
        store = DuckDBStore(self.db_path).initialize()
        store._conn.execute(
            "DROP INDEX IF EXISTS model_advice_context_prompt_idx"
        )
        store._conn.execute(
            "CREATE INDEX model_advice_context_prompt_idx "
            "ON model_advice(context_to, prompt_hash)"
        )
        store.insert_model_advice(self._advice_row("a1"))
        store.insert_model_advice(self._advice_row("a2"))
        store.close()
        with DuckDBStore(self.db_path) as reopened:
            self.assertFalse(reopened._advice_context_unique)
            self.assertEqual(reopened.count("model_advice"), 2)
            reopened.insert_model_advice(self._advice_row("a3"))
            self.assertEqual(reopened.count("model_advice"), 3)

    def test_get_model_advice_for_context(self):
        with DuckDBStore(self.db_path) as store:
            target = datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc)
            store.insert_model_advice(
                self._advice_row("a1", context_to=target)
            )
            store.insert_model_advice(
                self._advice_row("a2", prompt_hash="other-hash")
            )
            found = store.get_model_advice_for_context(target, "hash-1")
            self.assertEqual(found["advice_id"], "a1")
            self.assertIsNone(
                store.get_model_advice_for_context(target, "nope")
            )

    def test_trade_feedback_composite_key_migration(self):
        base = datetime(2026, 9, 22, 4, 0, tzinfo=timezone.utc)
        with DuckDBStore(self.db_path) as store:
            for advice_id in ("old1", "old2", "old3", "old4"):
                store.insert_model_advice(
                    self._advice_row(
                        advice_id, prompt_hash=f"h-{advice_id}"
                    )
                )
        conn = duckdb.connect(str(self.db_path))
        conn.execute("DROP TABLE trade_feedback")
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
        legacy_rows = [
            ("old1", base, True, base, base + timedelta(minutes=5),
             100.0, 110.0, 1, "WORKED", 1.0, 10.0, "ok"),
            ("old2", base, False, base, base + timedelta(minutes=30),
             100.0, 103.0, 2, "NOT_TAKEN", 2.0, 5.0,
             "Automated 30-minute shadow outcome."),
            ("old3", base, False, None, None,
             None, None, None, "NOT_TAKEN", None, None, None),
            ("old4", base, False, None, None,
             None, None, None, "WORKED", None, None, None),
        ]
        conn.executemany(
            "INSERT INTO trade_feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            legacy_rows,
        )
        conn.close()

        with DuckDBStore(self.db_path) as store:
            info = store._connection().execute(
                "PRAGMA table_info('trade_feedback')"
            ).fetchall()
            keys = {r[1] for r in info if r[5]}
            self.assertEqual(keys, {"advice_id", "evaluation_mode"})
            self.assertEqual(store.count("trade_feedback"), 4)

            old1 = store.get_trade_feedback("old1", "USER")
            self.assertTrue(old1["trade_was_taken"])
            self.assertEqual(old1["entered_at"], base)
            self.assertEqual(old1["actual_entry_price"], 100.0)
            self.assertEqual(old1["actual_exit_price"], 110.0)
            self.assertEqual(old1["lots"], 1)
            self.assertEqual(old1["user_verdict"], "WORKED")
            self.assertEqual(old1["mae"], 1.0)
            self.assertEqual(old1["user_notes"], "ok")

            old2 = store.get_trade_feedback("old2", "SHADOW_30M")
            self.assertFalse(old2["trade_was_taken"])
            self.assertEqual(old2["lots"], 2)
            self.assertIsNone(store.get_trade_feedback("old2", "USER"))

            old3 = store.get_trade_feedback("old3", "USER")
            self.assertEqual(old3["user_verdict"], "NOT_TAKEN")
            self.assertIsNone(old3["entered_at"])

            old4 = store.get_trade_feedback("old4", "USER")
            self.assertEqual(old4["user_verdict"], "WORKED")

            store.insert_trade_feedback(
                TradeFeedbackRow(
                    advice_id="old1",
                    feedback_at=base + timedelta(minutes=32),
                    trade_was_taken=False,
                    entered_at=base,
                    exited_at=base + timedelta(minutes=30),
                    actual_entry_price=100.0,
                    actual_exit_price=103.0,
                    lots=2,
                    user_verdict="NOT_TAKEN",
                    mae=2.0,
                    mfe=5.0,
                    user_notes="Automated 30-minute shadow outcome.",
                    evaluation_mode="SHADOW_30M",
                    price_basis="SHADOW_QUOTE_MODEL",
                    result_status="HORIZON_EXIT",
                    lot_size=65,
                    quoted_spread=1.0,
                    excursion_source="OPTION_1M_LTP_PROXY",
                )
            )
            self.assertEqual(store.count("trade_feedback"), 5)
            with self.assertRaises(duckdb.ConstraintException):
                store.insert_trade_feedback(
                    TradeFeedbackRow(
                        advice_id="old1",
                        feedback_at=base + timedelta(minutes=40),
                        trade_was_taken=False,
                        entered_at=None,
                        exited_at=None,
                        actual_entry_price=None,
                        actual_exit_price=None,
                        lots=None,
                        user_verdict="NOT_TAKEN",
                        mae=None,
                        mfe=None,
                        user_notes="dupe",
                        evaluation_mode="USER",
                        price_basis="ACTUAL_FILL",
                        result_status="NOT_TAKEN",
                    )
                )

        with DuckDBStore(self.db_path) as reopened:
            self.assertEqual(reopened.count("trade_feedback"), 5)
            rows = reopened.get_trade_feedback_rows("old1")
            self.assertEqual(
                {r["evaluation_mode"] for r in rows},
                {"USER", "SHADOW_30M"},
            )
            self.assertIsNone(
                reopened.get_trade_feedback("old5", "USER")
            )


if __name__ == "__main__":
    unittest.main()
