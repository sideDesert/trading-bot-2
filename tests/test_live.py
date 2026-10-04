import copy
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from trading_bot.features import IST
from trading_bot.kite.client import KiteInstrument, KiteError
from trading_bot.kite.execution import AmbiguousOrderError
from trading_bot.live_engine import LiveConfig, LiveEngine, LiveHalt
from trading_bot.live_store import LiveStore, runner_lock

NOW = datetime(2026, 10, 5, 10, 0, tzinfo=IST)


def decision():
    return dict(decision_id='decision-1', decided_at=NOW.isoformat(), action='LONG_CALL',
        expiry_date='2026-10-06', strike=25000, lot_size=65, india_vix=14,
        instrument_key='NSE_FO|1', entry_price=100, stop_price=90, target_price=120)


class Broker:
    def __init__(self):
        self.book = []
        self.calls = []
        self.cash = 20000
        self.fail_place = None
        self.auto_modify = True
        self.extra_positions = []
        self.user_id = 'AB1234'
    def profile(self): return {'user_id': self.user_id}
    def nifty_options(self):
        return [KiteInstrument('NIFTY26OCT25000CE', date(2026, 10, 6), 25000, 'CE', 65)]
    def orders(self): return copy.deepcopy(self.book)
    def positions(self):
        quantity = sum(o['filled_quantity'] * (1 if o['transaction_type'] == 'BUY' else -1) for o in self.book)
        return self.extra_positions + ([dict(exchange='NFO', product='NRML',
            tradingsymbol='NIFTY26OCT25000CE', quantity=quantity)] if quantity else [])
    def cash_available(self): return self.cash
    def order_margin(self, *args): return args[1] * args[2]
    def round_trip_charges(self, *args): return 60
    def trades(self):
        return [dict(order_id=o['order_id'], quantity=o['filled_quantity'], price=o['average_price'])
            for o in self.book if o['filled_quantity']]
    def execution_charges(self, orders): return 60
    def place_order(self, params):
        self.calls.append(('place', copy.deepcopy(params)))
        if self.fail_place == 'reject': raise KiteError('rejected')
        order = dict(params, order_id=str(len(self.book)+1), exchange='NFO', product='NRML',
            filled_quantity=0, average_price=0, status='OPEN' if params['order_type']=='LIMIT' else 'TRIGGER PENDING',
            exchange_order_id='exchange1')
        if self.fail_place != 'lost': self.book.append(order)
        if self.fail_place in ('accepted_timeout', 'lost'): raise AmbiguousOrderError('timeout')
        return order['order_id']
    def modify_order(self, order_id, **params):
        self.calls.append(('modify', order_id, params))
        if self.auto_modify:
            order = next(o for o in self.book if o['order_id']==order_id)
            order.update(params)
            order['status'] = 'TRIGGER PENDING' if params['order_type']=='SL' else 'OPEN'
    def cancel_order(self, order_id):
        self.calls.append(('cancel', order_id))
        next(o for o in self.book if o['order_id']==order_id)['status'] = 'CANCELLED'
    def fill(self, index, quantity, status='COMPLETE', price=100):
        self.book[index].update(filled_quantity=quantity, status=status, average_price=price)


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = LiveStore(Path(self.tmp.name)/'live.sqlite3')
        self.broker = Broker()
        self.config = LiveConfig('AB1234', 1000, 10000, 2000, 1.0, 200)
        self.engine = LiveEngine(self.store, self.broker, self.config)
    def step(self, bid=100, now=NOW):
        self.engine.step(now, bid=bid)
    def enter(self, quantity=65, status='COMPLETE'):
        self.engine.accept(decision(), NOW)
        self.broker.fill(0, quantity, status)
        self.step()
        self.step()
    def test_entry_is_ioc_and_live_risk_is_explicit(self):
        self.engine.accept(decision(), NOW)
        params = self.broker.calls[0][1]
        self.assertEqual((params['quantity'], params['validity']), (65, 'IOC'))
        with self.assertRaises(ValueError): LiveConfig('AB1234', 10000, 10000, 20000, 1, 200)
    def test_approved_daily_loss_limit_preserves_separate_trade_limit(self):
        config=LiveConfig('AB1234',10000,10000,10000,1,200)
        self.assertEqual(config.daily_loss_limit_inr,10000)
        with self.assertRaises(ValueError): LiveConfig('AB1234',2500,10000,10001,1,200)
        with self.assertRaises(ValueError): LiveConfig('AB1234',10001,10000,10000,1,200)
        with self.assertRaisesRegex(ValueError,'Explicit positive finite'):
            LiveConfig('AB1234',None,10000,10000,1,200)
    def test_total_loss_trade_limit_does_not_reserve_unspent_risk(self):
        self.engine=LiveEngine(self.engine.store,self.broker,LiveConfig('AB1234',10000,10000,10000,1,200))
        self.engine.accept(decision(),NOW)
        self.assertEqual(len(self.broker.book),1)
    def test_partial_entry_is_protected_then_remainder_cancelled(self):
        self.enter(30, 'OPEN')
        sells = [c for c in self.broker.calls if c[0]=='place' and c[1]['transaction_type']=='SELL']
        self.assertEqual(sells[0][1]['quantity'], 30)
        self.assertEqual(sells[0][1]['order_type'], 'SL')
        self.assertIn(('cancel', '1'), self.broker.calls)
    def test_late_entry_fill_resizes_same_stop(self):
        self.enter(30, 'OPEN')
        self.broker.fill(0, 65)
        self.step()
        self.assertEqual(self.broker.calls[-1][0], 'modify')
        self.assertEqual(self.broker.calls[-1][2]['quantity'], 65)
        self.assertEqual(len(self.broker.book), 2)
    def test_target_converts_same_sell_and_never_competes(self):
        self.enter()
        self.step(bid=121)
        self.assertEqual(self.broker.calls[-1][0:2], ('modify', '2'))
        self.assertEqual(self.broker.calls[-1][2]['order_type'], 'LIMIT')
        self.broker.fill(1, 65, price=121)
        self.step()
        self.assertEqual(self.store.get('decision-1')['status'], 'CLOSED')
        self.assertEqual(len(self.broker.book), 2)
    def test_stop_fills_during_target_race_no_new_sell(self):
        self.enter()
        self.broker.fill(1, 65, price=89)
        self.step(bid=121)
        self.assertEqual(len(self.broker.book), 2)
        self.assertEqual(self.store.get('decision-1')['status'], 'CLOSED')
    def test_timeout_recovered_by_tag_after_restart(self):
        self.broker.fail_place = 'accepted_timeout'
        self.engine.accept(decision(), NOW)
        engine = LiveEngine(self.store, self.broker, self.config)
        self.broker.fail_place = None
        engine.step(NOW, bid=100)
        self.assertEqual(len(self.broker.book), 1)
        self.assertEqual(self.store.get('decision-1')['entry_id'], '1')
    def test_unknown_placement_is_not_retried(self):
        self.broker.fail_place = 'lost'
        self.engine.accept(decision(), NOW)
        with self.assertRaises(LiveHalt): self.step(now=NOW+timedelta(seconds=40))
        self.assertEqual(len(self.broker.calls), 1)
        self.assertFalse(self.engine.accept(decision(), NOW))
    def test_duplicate_decision_is_not_submitted(self):
        self.engine.accept(decision(), NOW)
        self.assertFalse(self.engine.accept(decision(), NOW))
        self.assertEqual(len(self.broker.book), 1)
    def test_rejected_stop_cancels_entry_and_exits_only_confirmed_exposure(self):
        self.engine.accept(decision(), NOW)
        self.broker.fill(0, 30, 'OPEN')
        self.broker.fail_place = 'reject'
        self.step()
        self.broker.fail_place = None
        self.step()
        self.step()
        self.assertIn(('cancel', '1'), self.broker.calls)
        self.assertEqual(self.broker.book[-1]['order_type'], 'LIMIT')
        self.assertEqual(self.broker.book[-1]['quantity'], 30)
        self.assertTrue(self.store.get('decision-1')['halted'])
    def test_rejected_stop_in_orderbook_triggers_exit(self):
        self.enter()
        self.broker.book[1]['status'] = 'REJECTED'
        self.step()
        self.step()
        self.assertEqual(self.broker.book[-1]['order_type'], 'LIMIT')
    def test_partial_exit_replacement_after_terminal_only(self):
        self.enter()
        self.broker.fill(1, 20, 'OPEN', 89)
        self.step(bid=89)
        self.assertEqual(len(self.broker.book), 2)
        self.broker.book[1]['status'] = 'CANCELLED'
        self.step(bid=89)
        self.step(bid=89)
        self.assertEqual(self.broker.book[-1]['quantity'], 45)
    def test_funds_stale_prices_and_foreign_positions_fail_closed(self):
        self.broker.cash = 100
        with self.assertRaises(LiveHalt): self.engine.accept(decision(), NOW)
        self.assertEqual(self.broker.calls, [])
        self.broker.cash = 20000
        with self.assertRaises(LiveHalt): self.engine.accept(decision(), NOW+timedelta(minutes=2))
        self.broker.extra_positions = [dict(exchange='NFO', product='NRML', tradingsymbol='OTHER', quantity=1)]
        with self.assertRaises(LiveHalt): self.engine.accept(decision(), NOW)
        self.assertEqual(self.broker.calls, [])
    def test_account_change_and_overnight_fail_closed(self):
        self.engine.accept(decision(), NOW)
        self.broker.user_id = 'OTHER'
        with self.assertRaises(LiveHalt): self.step()
        self.broker.user_id = 'AB1234'
        with self.assertRaises(LiveHalt): self.step(now=NOW+timedelta(days=1))
    def test_squareoff_and_kill_convert_protection(self):
        self.enter()
        self.engine.step(NOW.replace(hour=15, minute=20), bid=99)
        self.assertEqual(self.broker.calls[-1][2]['order_type'], 'LIMIT')
    def test_agent_quantity_must_fit_both_caps(self):
        from dataclasses import replace
        engine = LiveEngine(self.store, self.broker, replace(self.config, max_lots=2))
        p = dict(decision(), proposed_lots=2, entry_price=40, stop_price=35, target_price=50)
        self.assertTrue(engine.accept(p, NOW))
        self.assertEqual(self.broker.book[0]['quantity'], 130)

    def test_protection_must_be_exchange_confirmed(self):
        self.enter()
        self.broker.book[1]['exchange_order_id'] = None
        with self.assertRaises(LiveHalt): self.step()
        self.assertNotEqual(self.store.get('decision-1')['status'], 'PROTECTED')

    def test_stop_quantity_cannot_exceed_confirmed_entry(self):
        self.enter()
        self.broker.book[1]['quantity'] = 130
        with self.assertRaises(LiveHalt): self.step()
        self.assertEqual(len(self.broker.book), 2)

    def test_daily_loss_and_cumulative_capital_gates(self):
        self.enter()
        self.broker.fill(1, 65, price=1)
        self.step()
        p = dict(decision(), decision_id='second')
        with self.assertRaises(LiveHalt): self.engine.accept(p, NOW)
        self.assertEqual(len(self.broker.book), 2)

    def test_bounded_rejected_exit_attempts(self):
        self.enter()
        for _ in range(4):
            self.broker.book[-1]['status'] = 'REJECTED'
            try: self.step()
            except LiveHalt: pass
        self.assertLessEqual(len(self.broker.book), 4) # entry + at most 3 sell attempts

    def test_ioc_entry_stuck_open_is_cancelled(self):
        self.engine.accept(decision(), NOW)
        self.step(now=NOW+timedelta(seconds=31))
        self.assertIn(('cancel', '1'), self.broker.calls)

    def test_rejected_modification_preserves_stop_and_never_adds_sell(self):
        self.enter()
        self.broker.auto_modify = False
        self.step(bid=121)
        with self.assertRaises(LiveHalt): self.step(bid=121, now=NOW+timedelta(seconds=40))
        self.assertEqual(len(self.broker.book), 2)
        self.assertEqual(self.broker.book[1]['order_type'], 'SL')

    def test_realized_net_profit_grows_capital_and_restart_restores_it(self):
        self.enter()
        self.broker.fill(1, 65, price=120)
        self.step()
        restored = LiveEngine(LiveStore(self.store.path), self.broker, self.config)
        self.assertEqual(restored.capital_status()['allocation_inr'], 11240)
        self.broker.cash = 9000
        self.assertEqual(restored.capital_status()['available_for_new_trade_inr'], 9000)

    def test_loss_shrinks_capital_and_unrealized_profit_is_not_budget(self):
        self.enter()
        self.assertEqual(self.engine.capital_status()['allocation_inr'], 10000)
        self.broker.fill(1, 65, price=95)
        self.step()
        self.assertEqual(self.engine.capital_status()['allocation_inr'], 9615)

    def test_closed_ledger_is_immutable_and_missing_charges_fail_closed(self):
        self.enter()
        self.broker.fill(1, 65, price=120)
        self.step()
        trade = self.store.get('decision-1')
        trade['net_pnl'] = 99999
        with self.assertRaises(LiveHalt): self.store.save(trade)

    def test_starting_allocation_cannot_be_reset_on_restart(self):
        from dataclasses import replace
        with self.assertRaises(LiveHalt):
            LiveEngine(self.store, self.broker, replace(self.config, capital_limit_inr=20000))

    def test_missing_cost_evidence_blocks_allocation(self):
        self.enter()
        self.broker.fill(1, 65, price=120)
        self.step()
        import sqlite3, json
        conn = sqlite3.connect(self.store.path)
        trade = self.store.get('decision-1')
        trade['charges'] = None
        conn.execute('UPDATE live_trade SET state=?', (json.dumps(trade),))
        conn.commit()
        conn.close()
        with self.assertRaises(LiveHalt): self.engine.capital_status()

    def test_profits_can_fund_a_larger_trade_with_unchanged_risk(self):
        self.enter()
        self.broker.fill(1, 65, price=130)
        self.step()
        p = dict(decision(), decision_id='second', entry_price=170, stop_price=160, target_price=190)
        # Premium + fees 11250 exceeds initial 10000, fits realized allocation 11890.
        self.assertTrue(self.engine.accept(p, NOW))
        self.assertEqual(self.broker.book[-1]['quantity'], 65)

    def test_profit_does_not_override_available_broker_cash(self):
        self.enter()
        self.broker.fill(1, 65, price=130)
        self.step()
        self.broker.cash = 10000
        p = dict(decision(), decision_id='second', entry_price=170, stop_price=160, target_price=190)
        with self.assertRaises(LiveHalt): self.engine.accept(p, NOW)
        self.assertEqual(len(self.broker.book), 2)

    def test_unconfirmed_stop_still_cancels_partial_entry_on_kill(self):
        self.engine.accept(decision(), NOW)
        self.broker.fill(0, 30, 'OPEN')
        self.step()
        self.broker.book[1]['exchange_order_id'] = None
        try: self.engine.step(NOW, bid=100, kill=True)
        except LiveHalt: pass
        self.assertIn(('cancel', '1'), self.broker.calls)
        self.assertEqual(len(self.broker.book), 2)

    def test_entry_rechecks_session_after_slow_preflight(self):
        with self.assertRaises(LiveHalt):
            self.engine.accept(decision(), NOW, clock=lambda: NOW.replace(hour=15, minute=16))
        self.assertEqual(self.broker.calls, [])

    def test_expired_bid_after_reads_does_not_remove_stop(self):
        self.enter()
        self.engine.step(NOW, bid=121, quote_provider=lambda: None, clock=lambda: NOW+timedelta(seconds=20))
        self.assertEqual(self.broker.book[1]['order_type'], 'SL')
        self.assertEqual(len(self.broker.book), 2)

    def test_single_runner_lock(self):
        path = Path(self.tmp.name)/'runner.lock'
        with runner_lock(path):
            with self.assertRaises(LiveHalt):
                with runner_lock(path): pass
