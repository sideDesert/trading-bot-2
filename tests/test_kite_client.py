import json
import unittest
from datetime import date

from trading_bot.kite.client import (
    KiteClient,
    KiteError,
    KiteForbiddenEndpoint,
    find_option,
    parse_nifty_options,
)

CSV = (
    "instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange\n"
    "1,1,NIFTY26SEP23050CE,NIFTY,0,2026-09-29,23050,0.05,65,CE,NFO-OPT,NFO\n"
    "2,2,NIFTY26SEP23050PE,NIFTY,0,2026-09-29,23050,0.05,65,PE,NFO-OPT,NFO\n"
    "3,3,NIFTY26SEPFUT,NIFTY,0,2026-09-29,0,0.05,65,FUT,NFO-FUT,NFO\n"
    "4,4,BANKNIFTY26SEP50000CE,BANKNIFTY,0,2026-09-29,50000,0.05,30,CE,NFO-OPT,NFO\n"
)


class Recorder:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, json.loads(body) if body else None))
        return self.responses.pop(0)


class KiteClientTests(unittest.TestCase):
    def test_order_endpoints_are_refused(self):
        client = KiteClient("k", "t", transport=Recorder([]))
        for method, path in (("POST", "/orders/regular"), ("PUT", "/orders/regular/1"), ("POST", "/gtt/triggers")):
            with self.assertRaises(KiteForbiddenEndpoint):
                client._call(method, path)

    def test_requires_credentials(self):
        with self.assertRaises(KiteError):
            KiteClient("k", "")

    def test_margin_request_shape_and_auth(self):
        rec = Recorder([json.dumps({"status": "success", "data": [{"total": 9915.75}]}).encode()])
        margin = KiteClient("key", "tok", transport=rec).order_margin("NIFTY26SEP23050CE", 65, 152.55)
        self.assertEqual(margin, 9915.75)
        method, url, headers, body = rec.calls[0]
        self.assertEqual((method, url), ("POST", "https://api.kite.trade/margins/orders"))
        self.assertEqual(headers["Authorization"], "token key:tok")
        self.assertEqual(body[0]["transaction_type"], "BUY")
        self.assertEqual(body[0]["quantity"], 65)

    def test_round_trip_charges_sums_both_legs(self):
        data = [{"charges": {"total": 30.5}}, {"charges": {"total": 41.25}}]
        rec = Recorder([json.dumps({"status": "success", "data": data}).encode()])
        total = KiteClient("k", "t", transport=rec).round_trip_charges("SYM", 65, 150.0, 160.0)
        self.assertAlmostEqual(total, 71.75)
        legs = rec.calls[0][3]
        self.assertEqual([(l["transaction_type"], l["average_price"]) for l in legs], [("BUY", 150.0), ("SELL", 160.0)])

    def test_error_envelope_raises(self):
        rec = Recorder([json.dumps({"status": "error", "message": "TokenException"}).encode()])
        with self.assertRaises(KiteError):
            KiteClient("k", "t", transport=rec).available_equity_margin()

    def test_parse_and_find_nifty_options(self):
        options = parse_nifty_options(CSV)
        self.assertEqual([o.tradingsymbol for o in options], ["NIFTY26SEP23050CE", "NIFTY26SEP23050PE"])
        found = find_option(options, date(2026, 9, 29), 23050.0, "PE")
        self.assertEqual((found.tradingsymbol, found.lot_size), ("NIFTY26SEP23050PE", 65))
        self.assertIsNone(find_option(options, date(2026, 10, 6), 23050.0, "PE"))


if __name__ == "__main__":
    unittest.main()
