import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from trading_bot.autopilot import CodexDecisionAgent, validate_proposal, decision_due, record_proposal
from trading_bot.live import fresh_book, validate_contract, read_settings
from trading_bot.live_store import LiveHalt
from test_live import NOW


class AutomationTests(unittest.TestCase):
    def brief(self):
        return dict(status='CONTEXT', fetch_status='OK', meta=dict(ts_ist=NOW.isoformat(),
            data_is_stale=False, expiry_date='2026-10-06', india_vix=14), analytics={}, options={'lot_size':65}, history={})
    def proposal(self):
        return dict(action='LONG_CALL', strike=25000, instrument_key='NSE_FO|1',
            entry_price=100, stop_price=90, target_price=120, proposed_lots=1, rationale='Breakout')
    def test_model_selects_direction_and_size(self):
        p = validate_proposal(self.proposal(), self.brief(), NOW)
        self.assertEqual(p['proposed_lots'], 1)
    def test_unknown_keys_nan_stale_context_and_no_trade_levels_rejected(self):
        for changes in ({'proposed_lots':True}, {'entry_price':float('nan')}, {'extra':'unsafe'},
                        {'action':'NO_TRADE'}):
            with self.assertRaises(LiveHalt):
                validate_proposal(dict(self.proposal(), **changes), self.brief(), NOW)
        with self.assertRaises(LiveHalt):
            validate_proposal(self.proposal(), self.brief(), NOW+timedelta(minutes=2))
    def test_agent_runs_without_broker_environment_and_tools(self):
        def execute(command, **kwargs):
            self.assertNotIn('KITE_ACCESS_TOKEN', kwargs['env'])
            self.assertIn('features.shell_tool=false', command)
            self.assertIn('--ignore-user-config', command)
            path = Path(command[command.index('--output-last-message')+1])
            path.write_text(json.dumps(self.proposal()))
            return SimpleNamespace(returncode=0)
        with patch.dict('os.environ', {'KITE_ACCESS_TOKEN':'do-not-expose'}):
            agent = CodexDecisionAgent(execute=execute)
            self.assertEqual(agent.choose(self.brief(), {'capital_limit_inr':10000})['proposed_lots'], 1)
    def test_failed_model_is_not_a_trade(self):
        agent = CodexDecisionAgent(execute=lambda *a, **k: SimpleNamespace(returncode=1))
        with self.assertRaises(LiveHalt): agent.choose(self.brief(), {})
    def test_schedule_and_pilot_end(self):
        self.assertTrue(decision_due(NOW, NOW.date(), NOW.date(), busy=False))
        self.assertFalse(decision_due(NOW, NOW.date(), NOW.date(), busy=True))
        self.assertFalse(decision_due(NOW+timedelta(days=1), NOW.date(), NOW.date(), busy=False))
        self.assertFalse(decision_due(NOW.replace(hour=15, minute=15), NOW.date(), NOW.date(), busy=False))
    def test_quote_identity_age_and_spread(self):
        raw = {'x':dict(instrument_token='NSE_FO|1', last_trade_time=int(NOW.timestamp()*1000),
            depth=dict(buy=[{'price':100}], sell=[{'price':101}]))}
        self.assertEqual(fresh_book(raw, 'NSE_FO|1', NOW), (100, 101))
        self.assertIsNone(fresh_book(raw, 'NSE_FO|WRONG', NOW))
        self.assertIsNone(fresh_book(raw, 'NSE_FO|1', NOW+timedelta(seconds=20)))
    def test_upstox_contract_identity_crosschecked(self):
        rows = [dict(instrument_key='NSE_FO|1', expiry='2026-10-06', strike_price=25000,
            instrument_type='CE', lot_size=65)]
        validate_contract(dict(self.proposal(), expiry_date='2026-10-06', lot_size=65), rows)
        with self.assertRaises(LiveHalt):
            validate_contract(dict(self.proposal(), expiry_date='2026-10-06', lot_size=30), rows)
    def test_full_agent_record_queues_live_size_atomically(self):
        from trading_bot.storage import DuckDBStore
        from test_agent_brain import _seed_row
        with tempfile.TemporaryDirectory() as directory:
            db, inbox = Path(directory)/'market.duckdb', Path(directory)/'live/inbox'
            with DuckDBStore(db) as store:
                store.upsert_market_data(_seed_row(time=NOW, lot_size=65))
            receipt = record_proposal(self.proposal(), self.brief(), NOW, db, inbox, 'live')
            self.assertTrue(receipt['live_order_queued'])
            payload = json.loads(next(inbox.glob('*.json')).read_text())
            self.assertEqual(payload['proposed_lots'], 1)
            self.assertEqual(payload['context_ts'], NOW.isoformat())
            self.assertNotIn('paper_order_queued', receipt)

    def test_scheduled_proposal_to_protected_broker_trade(self):
        from trading_bot.storage import DuckDBStore
        from trading_bot.live import LiveRunner
        from test_agent_brain import _seed_row
        from test_live import Broker
        from trading_bot.live_store import LiveStore
        from trading_bot.live_engine import LiveConfig, LiveEngine
        import datetime as dt
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'live'
            db = Path(directory)/'market.duckdb'
            with DuckDBStore(db) as store:
                # Concurrent market writer has advanced to another expiry; the
                # decision must retain its original context, not this latest row.
                store.upsert_market_data(_seed_row(time=NOW, lot_size=65))
            record_proposal(self.proposal(), self.brief(), NOW, db, root/'inbox', 'live')
            broker = Broker()
            engine = LiveEngine(LiveStore(root/'state.sqlite3'), broker, LiveConfig('AB1234',1000,10000,2000,1,200))
            class Quotes:
                def option_contracts(self, **kwargs):
                    return [dict(instrument_key='NSE_FO|1', expiry='2026-10-06', strike_price=25000,
                        instrument_type='CE', lot_size=65)]
                def market_quotes(self, keys):
                    return {'q':dict(instrument_token='NSE_FO|1', last_trade_time=int(NOW.timestamp()*1000),
                        depth=dict(buy=[{'price':100}], sell=[{'price':101}]))}
            runner = LiveRunner(engine, Quotes(), root, log=lambda message: None, clock=lambda: NOW)
            runner.ingest(NOW)
            self.assertEqual(len(broker.book), 1)
            broker.fill(0, 65)
            runner.tick(NOW)
            runner.tick(NOW)
            self.assertEqual(broker.book[1]['order_type'], 'SL')
            self.assertEqual(engine.store.active()[0]['status'], 'PROTECTED')

    def test_example_cannot_activate_without_loss_limits(self):
        with self.assertRaises((LiveHalt, ValueError, TypeError)):
            read_settings(Path('config/live.example.json'))
