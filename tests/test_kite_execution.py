import json
import unittest
from urllib.parse import parse_qs

from trading_bot.kite.execution import KiteExecutionClient, AmbiguousOrderError
from trading_bot.kite.client import KiteError, KiteForbiddenEndpoint, KiteHTTPError


class ExecutionClientTests(unittest.TestCase):
    def test_requires_explicit_activation(self):
        with self.assertRaises(KiteError):
            KiteExecutionClient('k', 't')

    def test_form_encoding_and_fixed_scope(self):
        calls = []
        def transport(method, url, headers, body, timeout):
            calls.append((method, url, headers, body))
            return json.dumps({'status': 'success', 'data': {'order_id': '123'}}).encode()
        client = KiteExecutionClient('k', 't', enabled=True, transport=transport)
        self.assertEqual(client.place_order(dict(tradingsymbol='NIFTY', transaction_type='BUY',
            quantity=65, price=100, order_type='LIMIT', validity='IOC', tag='tb2abc')), '123')
        self.assertEqual(parse_qs(calls[0][3].decode())['product'], ['NRML'])
        self.assertEqual(calls[0][2]['Content-Type'], 'application/x-www-form-urlencoded')
        with self.assertRaises(KiteForbiddenEndpoint):
            client._call('POST', '/gtt/triggers', {})
        with self.assertRaises(KiteForbiddenEndpoint):
            client.modify_order('../user', quantity=65)

    def test_timeout_is_ambiguous_and_never_retried(self):
        calls = []
        def transport(*args):
            calls.append(args)
            raise TimeoutError('secret-token')
        client = KiteExecutionClient('key', 'secret-token', enabled=True, transport=transport)
        with self.assertRaises(AmbiguousOrderError) as caught:
            client.place_order(dict(tradingsymbol='NIFTY', transaction_type='BUY',
                quantity=65, price=100, order_type='LIMIT', validity='IOC', tag='tb2abc'))
        self.assertNotIn('secret-token', str(caught.exception))
        self.assertEqual(len(calls), 1)

    def test_explicit_http_rejection_is_not_ambiguous(self):
        def transport(*args): raise KiteHTTPError(400, 'do-not-expose')
        client = KiteExecutionClient('k', 't', enabled=True, transport=transport)
        with self.assertRaises(KiteError) as caught:
            client.place_order(dict(tradingsymbol='NIFTY', transaction_type='SELL', quantity=65,
                price=89, trigger_price=90, order_type='SL', validity='DAY', tag='tb2abc'))
        self.assertNotIsInstance(caught.exception, AmbiguousOrderError)
        self.assertNotIn('do-not-expose', str(caught.exception))

    def test_rejects_unsafe_order_types_and_unknown_fields(self):
        client = KiteExecutionClient('k', 't', enabled=True, transport=lambda *a: self.fail('transport called'))
        for params in [dict(order_type='SL-M'), dict(exchange='NSE'), dict(autoslice=True)]:
            with self.assertRaises(KiteError):
                client.place_order(params)
