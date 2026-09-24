import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from trading_bot.features import IST
from trading_bot.kite.client import KiteInstrument
from trading_bot.paper import (
    PaperConfig,
    PaperEngine,
    PaperStore,
    PaperTrade,
    day_net_pnl,
    run_loop,
    format_status,
    risk_budget,
    size_lots,
    top_of_book,
)

KEY = "NSE_FO|73904"
T0 = datetime(2026, 9, 25, 10, 0, 0, tzinfo=IST)


class FakeUpstox:
    def __init__(self):
        self.book = {}

    def set(self, bid, ask):
        self.book[KEY] = (bid, ask)

    def market_quotes(self, keys):
        out = {}
        for key in keys:
            if key in self.book:
                bid, ask = self.book[key]
                out["NSE_FO:" + key] = {
                    "instrument_token": key,
                    "depth": {"buy": [{"price": bid, "quantity": 500}], "sell": [{"price": ask, "quantity": 500}]},
                }
        return out


class FakeKite:
    def __init__(self):
        self.calls = []

    def nifty_options(self):
        from datetime import date

        return [KiteInstrument("NIFTY26SEP23050CE", date(2026, 9, 29), 23050.0, "CE", 65)]

    def order_margin(self, symbol, qty, price):
        self.calls.append(("margin", symbol, qty, price))
        return qty * price

    def available_equity_margin(self):
        return -928.1

    def round_trip_charges(self, symbol, qty, buy, sell):
        self.calls.append(("charges", symbol, qty, buy, sell))
        return 123.45


def payload(decision_id="d1", decided_at=T0, **kw):
    p = {
        "decision_id": decision_id,
        "decided_at": decided_at.isoformat(),
        "action": "LONG_CALL",
        "instrument_key": KEY,
        "strike": 23050.0,
        "entry_price": 150.0,
        "stop_price": 130.0,
        "target_price": 190.0,
        "lot_size": 65,
        "expiry_date": "2026-09-29",
        "india_vix": 13.0,
    }
    p.update(kw)
    return p


class EngineTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.inbox = root / "paper-inbox"
        self.inbox.mkdir()
        self.store = PaperStore(root / "paper.duckdb")
        self.upstox = FakeUpstox()
        self.logs = []
        self.engine = PaperEngine(self.store, self.upstox, self.inbox, log=self.logs.append)

    def tearDown(self):
        self.tmp.cleanup()

    def drop(self, p):
        (self.inbox / f"{p['decision_id']}.json").write_text(json.dumps(p))

    def trade(self, decision_id="d1") -> PaperTrade:
        return self.store.get(decision_id)


class SizingTests(unittest.TestCase):
    def test_risk_budget_halves_on_high_or_unknown_vix(self):
        cfg = PaperConfig()
        self.assertEqual(risk_budget(13.0, cfg), 10000.0)
        self.assertEqual(risk_budget(16.0, cfg), 10000.0)
        self.assertEqual(risk_budget(16.5, cfg), 5000.0)
        self.assertEqual(risk_budget(None, cfg), 5000.0)

    def test_size_lots_floors_to_budget(self):
        self.assertEqual(size_lots(150.0, 130.0, 65, 10000.0), 7)  # 20*65=1300/lot
        self.assertEqual(size_lots(150.0, 130.0, 65, 1000.0), 0)
        self.assertEqual(size_lots(150.0, 150.0, 65, 10000.0), 0)

    def test_top_of_book_rejects_bad_depth(self):
        self.assertIsNone(top_of_book(None))
        self.assertIsNone(top_of_book({"depth": {"buy": [], "sell": []}}))
        self.assertIsNone(top_of_book({"depth": {"buy": [{"price": 0}], "sell": [{"price": 5}]}}))
        self.assertIsNone(top_of_book({"depth": {"buy": [{"price": 6}], "sell": [{"price": 5}]}}))
        self.assertEqual(top_of_book({"depth": {"buy": [{"price": 5}], "sell": [{"price": 5.1}]}}), (5.0, 5.1))


class LifecycleTests(EngineTestBase):
    def test_limit_entry_then_target_exit(self):
        self.drop(payload())
        self.upstox.set(151.0, 152.0)
        self.engine.tick(T0 + timedelta(seconds=5))
        t = self.trade()
        self.assertEqual((t.status, t.lots, t.quantity, t.risk_budget_inr), ("PENDING_ENTRY", 7, 455, 10000.0))
        self.assertTrue((self.inbox / "processed" / "d1.json").exists())

        self.upstox.set(149.0, 149.5)
        self.engine.tick(T0 + timedelta(seconds=10))
        t = self.trade()
        self.assertEqual((t.status, t.entry_fill), ("OPEN", 149.5))

        self.upstox.set(140.0, 141.0)
        self.engine.tick(T0 + timedelta(seconds=15))
        self.upstox.set(191.0, 192.0)
        self.engine.tick(T0 + timedelta(seconds=20))
        t = self.trade()
        self.assertEqual((t.status, t.exit_reason, t.exit_fill), ("CLOSED", "TARGET_HIT", 190.0))
        self.assertAlmostEqual(t.mae, -9.5)
        self.assertAlmostEqual(t.gross_pnl, (190.0 - 149.5) * 455)
        self.assertEqual(t.charges_source, "LOCAL_MODEL")
        self.assertAlmostEqual(t.net_pnl, t.gross_pnl - t.charges)
        self.assertGreater(t.charges, 0)

    def test_stop_exits_at_bid_below_stop(self):
        self.drop(payload())
        self.upstox.set(149.0, 150.0)
        self.engine.tick(T0)
        self.upstox.set(127.0, 128.0)
        self.engine.tick(T0 + timedelta(seconds=5))
        t = self.trade()
        self.assertEqual((t.status, t.exit_reason, t.exit_fill), ("CLOSED", "STOP_HIT", 127.0))
        self.assertAlmostEqual(t.gross_pnl, (127.0 - 150.0) * 455)

    def test_unfilled_entry_cancels_after_window(self):
        self.drop(payload())
        self.upstox.set(155.0, 156.0)
        self.engine.tick(T0)
        self.engine.tick(T0 + timedelta(minutes=10, seconds=1))
        t = self.trade()
        self.assertEqual((t.status, t.exit_reason), ("CANCELLED", "ENTRY_NOT_FILLED"))

    def test_square_off_at_1520(self):
        at = T0.replace(hour=15, minute=0)
        self.drop(payload(decided_at=at))
        self.upstox.set(149.0, 150.0)
        self.engine.tick(at)
        self.upstox.set(160.0, 161.0)
        self.engine.tick(at.replace(minute=20))
        t = self.trade()
        self.assertEqual((t.status, t.exit_reason, t.exit_fill), ("CLOSED", "SQUARE_OFF", 160.0))

    def test_missing_quote_does_not_fill_or_exit(self):
        self.drop(payload())
        self.engine.tick(T0)
        self.assertEqual(self.trade().status, "PENDING_ENTRY")

    def test_status_formatting(self):
        self.drop(payload())
        self.upstox.set(149.0, 150.0)
        self.engine.tick(T0)
        text = format_status(self.store.for_day(T0.date()))
        self.assertIn("LONG_CALL 23050 OPEN", text)
        self.assertIn("unrealised", text)


class SkipTests(EngineTestBase):
    def status_reason(self, decision_id="d1"):
        t = self.trade(decision_id)
        return t.status, t.exit_reason

    def test_decision_too_old(self):
        self.drop(payload(decided_at=T0 - timedelta(minutes=11)))
        self.engine.tick(T0)
        self.assertEqual(self.status_reason(), ("SKIPPED", "DECISION_TOO_OLD"))

    def test_late_entry_cutoff(self):
        at = T0.replace(hour=15, minute=15)
        self.drop(payload(decided_at=at))
        self.engine.tick(at)
        self.assertEqual(self.status_reason(), ("SKIPPED", "LATE_ENTRY_CUTOFF"))

    def test_one_position_at_a_time(self):
        self.drop(payload("d1"))
        self.engine.tick(T0)
        self.drop(payload("d2"))
        self.engine.tick(T0 + timedelta(seconds=5))
        self.assertEqual(self.status_reason("d2"), ("SKIPPED", "ANOTHER_POSITION_ACTIVE"))

    def test_risk_budget_too_small(self):
        self.drop(payload(stop_price=1.0, entry_price=200.0, india_vix=20.0))
        self.engine.tick(T0)
        self.assertEqual(self.status_reason(), ("SKIPPED", "RISK_BUDGET_TOO_SMALL"))

    def test_daily_loss_limit_blocks_new_trades(self):
        loser = PaperTrade(
            decision_id="old", created_at=T0.isoformat(), decided_at=T0.isoformat(), status="CLOSED",
            action="LONG_PUT", instrument_key=KEY, strike=23050.0, limit_entry=100.0,
            stop_price=80.0, target_price=140.0, net_pnl=-20000.0,
        )
        self.store.upsert(loser)
        self.assertEqual(day_net_pnl(self.store.for_day(T0.date())), -20000.0)
        self.drop(payload())
        self.engine.tick(T0 + timedelta(minutes=1))
        self.assertEqual(self.status_reason(), ("SKIPPED", "DAILY_LOSS_LIMIT"))

    def test_duplicate_inbox_file_is_ignored(self):
        self.drop(payload())
        self.engine.tick(T0)
        self.drop(payload())
        self.engine.tick(T0 + timedelta(seconds=5))
        self.assertEqual(len(self.store.for_day(T0.date())), 1)


class RunLoopTests(EngineTestBase):
    def test_exits_on_non_session_day(self):
        sunday = datetime(2026, 9, 27, 10, 0, tzinfo=IST)
        self.assertEqual(run_loop(self.engine, now_fn=lambda: sunday, sleep=lambda s: None), 0)
        self.assertIn("No supported NSE session", self.logs[-1])

    def test_ticks_until_close_then_exits(self):
        clock = iter([T0, T0 + timedelta(seconds=5), T0.replace(hour=15, minute=40)])
        now = [T0]

        def now_fn():
            now[0] = next(clock, now[0])
            return now[0]

        self.drop(payload())
        self.upstox.set(155.0, 156.0)
        self.assertEqual(run_loop(self.engine, now_fn=now_fn, sleep=lambda s: None), 0)
        self.assertEqual(self.trade().status, "CANCELLED")
        self.assertIn("Session closed", self.logs[-1])

    def test_gives_up_on_unquoted_open_position_after_close(self):
        at = T0.replace(hour=15, minute=0)
        self.drop(payload(decided_at=at))
        self.upstox.set(149.0, 150.0)
        self.engine.tick(at)
        self.upstox.book.clear()
        clock = iter([at, at.replace(minute=45), at.replace(minute=51)])
        self.assertEqual(run_loop(self.engine, now_fn=lambda: next(clock), sleep=lambda s: None), 0)
        self.assertEqual(self.trade().status, "OPEN")
        self.assertTrue(any("still OPEN after close" in m for m in self.logs))


class KiteIntegrationTests(EngineTestBase):
    def test_kite_symbol_margin_and_charges(self):
        kite = FakeKite()
        self.engine.kite = kite
        self.drop(payload())
        self.upstox.set(149.0, 150.0)
        self.engine.tick(T0)
        t = self.trade()
        self.assertEqual(t.tradingsymbol, "NIFTY26SEP23050CE")
        self.assertEqual(t.margin_required, 455 * 150.0)
        self.assertIn("REAL_ACCOUNT_WOULD_LACK_MARGIN", t.notes)
        self.upstox.set(191.0, 192.0)
        self.engine.tick(T0 + timedelta(seconds=5))
        t = self.trade()
        self.assertEqual((t.charges, t.charges_source), (123.45, "KITE_CONTRACT_NOTE"))
        self.assertIn(("charges", "NIFTY26SEP23050CE", 455, 150.0, 190.0), kite.calls)


if __name__ == "__main__":
    unittest.main()
