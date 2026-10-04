import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from trading_bot.features import IST
from trading_bot.live_store import LiveHalt
from trading_bot.terminal_decisions import TerminalDecisionAgent, next_request, submit_proposal


class TerminalDecisionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.now = datetime.now(IST)
        self.brief = dict(status='CONTEXT', fetch_status='OK',
                          meta=dict(ts_ist=self.now.isoformat(), data_is_stale=False))
        self.proposal = dict(action='NO_TRADE', strike=None, instrument_key=None,
                             entry_price=None, stop_price=None, target_price=None,
                             proposed_lots=0, rationale='No qualifying setup')

    def start_request(self, timeout=2):
        self.agent = TerminalDecisionAgent(self.root, timeout=timeout)
        self.results = []

        def choose():
            try:
                self.results.append(self.agent.choose(self.brief, {'capital_limit_inr':10000}))
            except Exception as error:
                self.results.append(error)

        self.worker = threading.Thread(target=choose)
        self.worker.start()
        self.addCleanup(self.worker.join, 3)
        return next_request(self.root, wait=1)

    def test_terminal_decision_round_trip_and_private_files(self):
        request = self.start_request()
        self.assertEqual(request['status'], 'READY')
        self.assertEqual(request['brief'], self.brief)
        self.assertEqual((self.root/'request.json').stat().st_mode & 0o777, 0o600)
        submit_proposal(self.root, request['request_id'], self.proposal)
        self.worker.join(3)
        self.assertEqual(self.results, [self.proposal])
        self.assertFalse((self.root/'request.json').exists())
        self.agent.finish('RECORDED', action='NO_TRADE', queued=False)
        self.assertEqual(next_request(self.root)['last_outcome']['status'], 'RECORDED')

    def test_missing_terminal_times_out_without_proposal(self):
        self.start_request(timeout=.15)
        self.worker.join(2)
        self.assertIsInstance(self.results[0], LiveHalt)
        self.assertFalse((self.root/'request.json').exists())
        self.assertEqual(next_request(self.root)['last_outcome']['status'], 'TIMED_OUT')

    def test_old_or_path_traversing_request_cannot_submit(self):
        request = self.start_request(timeout=.3)
        for request_id in ('../request', '0'*32):
            with self.assertRaises(LiveHalt):
                submit_proposal(self.root, request_id, self.proposal)
        submit_proposal(self.root, request['request_id'], self.proposal)
        self.worker.join(2)

    def test_stale_market_context_is_rejected_before_submission(self):
        self.brief['meta']['ts_ist'] = (self.now-timedelta(minutes=2)).isoformat()
        request = self.start_request(timeout=.2)
        with self.assertRaises(LiveHalt):
            submit_proposal(self.root, request['request_id'], self.proposal)
        self.worker.join(2)
        self.assertIsInstance(self.results[0], LiveHalt)

    def test_expired_request_cannot_be_replayed(self):
        request = self.start_request(timeout=.15)
        self.worker.join(2)
        with self.assertRaises(LiveHalt):
            submit_proposal(self.root, request['request_id'], self.proposal)

    def test_submitted_request_is_not_returned_or_overwritten(self):
        request_id = 'a'*32
        request = dict(request_id=request_id, brief=self.brief,
                       deadline=(self.now+timedelta(seconds=30)).isoformat())
        (self.root/'request.json').write_text(json.dumps(request))
        submit_proposal(self.root, request_id, self.proposal)
        with self.assertRaises(LiveHalt):
            submit_proposal(self.root, request_id, dict(self.proposal, rationale='Different proposal'))
        response = json.loads((self.root/(request_id+'.json')).read_text())
        self.assertEqual(response['proposal'], self.proposal)
        self.assertEqual(next_request(self.root)['status'], 'WAITING')

    def test_response_identity_is_checked_even_for_direct_file_writes(self):
        request = self.start_request()
        response = dict(request_id='wrong-request', proposal=self.proposal)
        (self.root/(request['request_id']+'.json')).write_text(json.dumps(response))
        self.worker.join(3)
        self.assertIsInstance(self.results[0], LiveHalt)


if __name__ == '__main__':
    unittest.main()
