import json
import unittest
import urllib.parse
from urllib.error import URLError

from datetime import date

from trading_bot.upstox.client import (
    NIFTY_INSTRUMENT_KEY,
    USER_AGENT,
    HttpResponse,
    UpstoxAPIError,
    UpstoxClient,
    UpstoxConfigurationError,
    UpstoxDataError,
    UpstoxTransportError,
    UpstoxValidationError,
)

TOKEN = "test-secret-token"

CONTRACT_ROWS = [
    {"expiry": "2026-09-22", "weekly": True, "instrument_key": "K1",
     "instrument_type": "CE", "strike_price": 24000},
    {"expiry": "2026-09-29", "weekly": False, "instrument_key": "K2",
     "instrument_type": "CE", "strike_price": 24000},
    {"expiry": "2026-10-06", "weekly": True, "instrument_key": "K3",
     "instrument_type": "CE", "strike_price": 24000},
    {"expiry": "2026-10-13", "weekly": True, "instrument_key": "K4",
     "instrument_type": "CE", "strike_price": 24000},
    {"expiry": "2026-10-19", "weekly": True, "instrument_key": "K5",
     "instrument_type": "CE", "strike_price": 24000},
    {"expiry": "2026-10-27", "weekly": False, "instrument_key": "K6",
     "instrument_type": "CE", "strike_price": 24000},
]


def make_response(status=200, payload=None, body=None, headers=None):
    if body is None:
        body = json.dumps(payload if payload is not None else {}).encode("utf-8")
    return HttpResponse(
        status_code=status, headers=headers or {}, body=body
    )


def success(data):
    return make_response(payload={"status": "success", "data": data})


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected request")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def parsed_query(request):
    return urllib.parse.parse_qs(
        urllib.parse.urlsplit(request.full_url).query
    )


def mock_date_today(today):
    from unittest import mock

    fake = mock.Mock(wraps=date)
    fake.today.return_value = today
    return mock.patch("trading_bot.upstox.client.date", fake)


class ConstructorTests(unittest.TestCase):
    def test_blank_token_rejected(self):
        for token in ("", "   "):
            with self.assertRaises(UpstoxConfigurationError):
                UpstoxClient(token)

    def test_invalid_timeout_and_retries(self):
        with self.assertRaises(UpstoxConfigurationError):
            UpstoxClient(TOKEN, timeout=0)
        with self.assertRaises(UpstoxConfigurationError):
            UpstoxClient(TOKEN, timeout=-1)
        with self.assertRaises(UpstoxConfigurationError):
            UpstoxClient(TOKEN, max_retries=-1)

    def test_from_env_missing_and_blank(self):
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(UpstoxConfigurationError):
                UpstoxClient.from_env()
        with mock.patch.dict(os.environ, {"UPSTOX_ACCESS_TOKEN": "  "}, clear=True):
            with self.assertRaises(UpstoxConfigurationError) as ctx:
                UpstoxClient.from_env()
            self.assertIn("UPSTOX_ACCESS_TOKEN", str(ctx.exception))

    def test_from_env_uses_token(self):
        import os
        from unittest import mock

        transport = FakeTransport([success({"x": 1})])
        with mock.patch.dict(
            os.environ, {"UPSTOX_ACCESS_TOKEN": TOKEN}, clear=True
        ):
            client = UpstoxClient.from_env(transport=transport)
        client.health()
        self.assertEqual(
            transport.requests[0].headers["Authorization"],
            f"Bearer {TOKEN}",
        )


class RequestShapeTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport([])
        self.client = UpstoxClient(TOKEN, transport=self.transport, sleep=lambda s: None)

    def test_headers_and_method(self):
        self.transport.responses.append(success({"a": 1}))
        self.client.health()
        request = self.transport.requests[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.headers["Accept"], "application/json")
        self.assertEqual(request.headers["Authorization"], f"Bearer {TOKEN}")
        self.assertEqual(request.headers["User-agent"], USER_AGENT)
        self.assertTrue(
            request.full_url.startswith("https://api.upstox.com/")
        )

    def test_market_quotes_dedup_and_query(self):
        self.transport.responses.append(success({"q": []}))
        self.client.market_quotes(
            ["NSE_INDEX|Nifty 50", "NSE_EQ|INE002A01018", "NSE_INDEX|Nifty 50"]
        )
        qs = parsed_query(self.transport.requests[0])
        self.assertEqual(
            qs["instrument_key"],
            ["NSE_INDEX|Nifty 50,NSE_EQ|INE002A01018"],
        )

    def test_market_quotes_limits(self):
        with self.assertRaises(UpstoxValidationError):
            self.client.market_quotes([])
        with self.assertRaises(UpstoxValidationError):
            self.client.market_quotes([f"k{i}" for i in range(501)])
        with self.assertRaises(UpstoxValidationError):
            self.client.market_quotes(["  "])
        self.transport.responses.append(success({}))
        self.client.market_quotes(["k"] * 500)

    def test_health_uses_nifty(self):
        self.transport.responses.append(success({"live": True}))
        result = self.client.health()
        self.assertEqual(result, {"live": True})
        qs = parsed_query(self.transport.requests[0])
        self.assertEqual(qs["instrument_key"], [NIFTY_INSTRUMENT_KEY])

    def test_option_chain_defaults_and_unwrap(self):
        self.transport.responses.append(success(CONTRACT_ROWS))
        self.transport.responses.append(success({"chain": [1, 2]}))
        data = self.client.option_chain()
        self.assertEqual(data, {"chain": [1, 2]})
        self.assertEqual(len(self.transport.requests), 2)
        self.assertIn(
            "/v2/option/contract?", self.transport.requests[0].full_url
        )
        request = self.transport.requests[1]
        self.assertIn("/v2/option/chain?", request.full_url)
        qs = parsed_query(request)
        self.assertEqual(qs["instrument_key"], [NIFTY_INSTRUMENT_KEY])
        self.assertNotEqual(qs["expiry_date"], ["current_week"])

    def test_option_chain_explicit_expiry_single_request(self):
        self.transport.responses.append(success({"chain": []}))
        self.client.option_chain(expiry_date="2026-09-22")
        self.assertEqual(len(self.transport.requests), 1)
        qs = parsed_query(self.transport.requests[0])
        self.assertEqual(qs["expiry_date"], ["2026-09-22"])

    def test_resolve_expiry_week_aliases(self):
        as_of = date(2026, 9, 20)
        cases = {
            "current_week": "2026-09-22",
            "next_week": "2026-09-29",
            "far_week": "2026-10-06",
        }
        for alias, expected in cases.items():
            self.transport.responses.append(success(CONTRACT_ROWS))
            self.assertEqual(
                self.client.resolve_expiry(expiry_date=alias, as_of=as_of),
                expected,
            )

    def test_resolve_expiry_month_aliases(self):
        as_of = date(2026, 9, 20)
        cases = {"current_month": "2026-09-29", "next_month": "2026-10-27"}
        for alias, expected in cases.items():
            self.transport.responses.append(success(CONTRACT_ROWS))
            self.assertEqual(
                self.client.resolve_expiry(expiry_date=alias, as_of=as_of),
                expected,
            )

    def test_resolve_expiry_explicit_no_request(self):
        self.assertEqual(
            self.client.resolve_expiry(expiry_date="2026-09-22"), "2026-09-22"
        )
        self.assertEqual(len(self.transport.requests), 0)

    def test_resolve_expiry_skips_expired_and_malformed(self):
        rows = CONTRACT_ROWS + [
            {"expiry": "2020-01-01", "weekly": True},
            {"expiry": "not-a-date", "weekly": True},
            {"weekly": True},
            "garbage",
        ]
        self.transport.responses.append(success(rows))
        self.assertEqual(
            self.client.resolve_expiry(
                expiry_date="current_week", as_of=date(2026, 9, 20)
            ),
            "2026-09-22",
        )

    def test_resolve_expiry_insufficient(self):
        self.transport.responses.append(success(CONTRACT_ROWS))
        with self.assertRaises(UpstoxDataError):
            self.client.resolve_expiry(
                expiry_date="far_month", as_of=date(2026, 9, 20)
            )
        self.transport.responses.append(success([]))
        with self.assertRaises(UpstoxDataError):
            self.client.resolve_expiry(
                expiry_date="current_week", as_of=date(2026, 9, 20)
            )

    def test_option_contracts_omits_expiry_when_none(self):
        self.transport.responses.append(success(CONTRACT_ROWS))
        result = self.client.option_contracts(expiry_date=None)
        self.assertEqual(result, CONTRACT_ROWS)
        qs = parsed_query(self.transport.requests[0])
        self.assertNotIn("expiry_date", qs)
        self.assertEqual(qs["instrument_key"], [NIFTY_INSTRUMENT_KEY])

    def test_option_contracts_relative_filters_rows(self):
        self.transport.responses.append(success(CONTRACT_ROWS))
        with mock_date_today(date(2026, 9, 20)):
            result = self.client.option_contracts(expiry_date="current_week")
        self.assertEqual(len(self.transport.requests), 1)
        self.assertEqual(result, [CONTRACT_ROWS[0]])

    def test_option_contracts_with_expiry(self):
        self.transport.responses.append(success([]))
        self.client.option_contracts(expiry_date="2025-01-30")
        qs = parsed_query(self.transport.requests[0])
        self.assertEqual(qs["expiry_date"], ["2025-01-30"])

    def test_expiry_validation(self):
        for bad in ("", "next_year", "2025-13-01", "not-a-date"):
            with self.assertRaises(UpstoxValidationError):
                self.client.option_chain(expiry_date=bad)
        self.transport.responses.append(success({}))
        self.client.option_chain(expiry_date="2025-02-27")

    def test_intraday_path_encoding(self):
        self.transport.responses.append(success({"candles": []}))
        self.client.intraday_candles("NSE_INDEX|Nifty 50")
        url = self.transport.requests[0].full_url
        self.assertIn(
            "/v3/historical-candle/intraday/NSE_INDEX%7CNifty%2050/minutes/1",
            url,
        )

    def test_intraday_units(self):
        for unit in ("weeks", "months", "bogus"):
            with self.assertRaises(UpstoxValidationError):
                self.client.intraday_candles("KEY", unit=unit)
        with self.assertRaises(UpstoxValidationError):
            self.client.intraday_candles("KEY", unit="minutes", interval=301)
        with self.assertRaises(UpstoxValidationError):
            self.client.intraday_candles("KEY", unit="hours", interval=6)
        with self.assertRaises(UpstoxValidationError):
            self.client.intraday_candles("KEY", unit="days", interval=2)
        self.transport.responses.append(success({}))
        self.client.intraday_candles("KEY", unit="days", interval=1)

    def test_historical_path_and_ordering(self):
        self.transport.responses.append(success([]))
        self.client.historical_candles(
            "NSE_EQ|ABC", "2025-01-01", "2025-01-31", unit="days", interval=1
        )
        url = self.transport.requests[0].full_url
        self.assertIn(
            "/v3/historical-candle/NSE_EQ%7CABC/days/1/2025-01-31/2025-01-01",
            url,
        )

    def test_historical_validation(self):
        with self.assertRaises(UpstoxValidationError):
            self.client.historical_candles("K", "2025-02-01", "2025-01-01")
        with self.assertRaises(UpstoxValidationError):
            self.client.historical_candles("K", "bad", "2025-01-01")
        with self.assertRaises(UpstoxValidationError):
            self.client.historical_candles("K", "2025-01-01", "bad")
        with self.assertRaises(UpstoxValidationError):
            self.client.historical_candles(
                "K", "2025-01-01", "2025-01-02", unit="minutes", interval=0
            )
        self.transport.responses.append(success({}))
        self.client.historical_candles(
            "K", "2025-01-01", "2025-01-02", unit="months", interval=1
        )

    def test_search_params(self):
        self.transport.responses.append(success({"results": []}))
        self.client.search_instruments(
            "reliance",
            exchanges="NSE",
            segments="EQ",
            instrument_types="EQ",
            expiry="current_week",
            atm_offset=2,
            page_number=2,
            records=10,
        )
        qs = parsed_query(self.transport.requests[0])
        self.assertEqual(qs["query"], ["reliance"])
        self.assertEqual(qs["exchanges"], ["NSE"])
        self.assertEqual(qs["segments"], ["EQ"])
        self.assertEqual(qs["instrument_types"], ["EQ"])
        self.assertEqual(qs["expiry"], ["current_week"])
        self.assertEqual(qs["atm_offset"], ["2"])
        self.assertEqual(qs["page_number"], ["2"])
        self.assertEqual(qs["records"], ["10"])

    def test_search_defaults_and_optional_omitted(self):
        self.transport.responses.append(success({}))
        self.client.search_instruments("abc")
        qs = parsed_query(self.transport.requests[0])
        self.assertEqual(qs["page_number"], ["1"])
        self.assertEqual(qs["records"], ["20"])
        for key in ("exchanges", "segments", "instrument_types", "expiry", "atm_offset"):
            self.assertNotIn(key, qs)

    def test_search_validation(self):
        with self.assertRaises(UpstoxValidationError):
            self.client.search_instruments("")
        with self.assertRaises(UpstoxValidationError):
            self.client.search_instruments("   ")
        with self.assertRaises(UpstoxValidationError):
            self.client.search_instruments("x" * 51)
        with self.assertRaises(UpstoxValidationError):
            self.client.search_instruments("q", page_number=0)
        with self.assertRaises(UpstoxValidationError):
            self.client.search_instruments("q", records=0)
        with self.assertRaises(UpstoxValidationError):
            self.client.search_instruments("q", records=31)


class ErrorAndRetryTests(unittest.TestCase):
    def test_retry_429_then_success_with_retry_after(self):
        delays = []
        transport = FakeTransport(
            [
                make_response(status=429, payload={}, headers={"Retry-After": "3"}),
                success({"v": 1}),
            ]
        )
        client = UpstoxClient(TOKEN, transport=transport, sleep=delays.append)
        self.assertEqual(client.health(), {"v": 1})
        self.assertEqual(delays, [3.0])
        self.assertEqual(len(transport.requests), 2)

    def test_retry_503_exhaustion(self):
        delays = []
        transport = FakeTransport(
            [
                make_response(status=503, payload={}),
                make_response(status=503, payload={}),
                make_response(status=503, payload={}),
            ]
        )
        client = UpstoxClient(
            TOKEN, transport=transport, sleep=delays.append, max_retries=2
        )
        with self.assertRaises(UpstoxAPIError) as ctx:
            client.health()
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(delays, [1.0, 2.0])
        self.assertEqual(len(transport.requests), 3)

    def test_401_not_retried(self):
        transport = FakeTransport(
            [make_response(status=401, payload={"status": "error"})]
        )
        client = UpstoxClient(TOKEN, transport=transport, sleep=lambda s: None)
        with self.assertRaises(UpstoxAPIError):
            client.health()
        self.assertEqual(len(transport.requests), 1)

    def test_malformed_json_and_envelope(self):
        transport = FakeTransport([make_response(body=b"not json")])
        client = UpstoxClient(TOKEN, transport=transport, sleep=lambda s: None)
        with self.assertRaises(UpstoxAPIError):
            client.health()

        transport2 = FakeTransport([make_response(body=b"[1,2]")])
        client2 = UpstoxClient(TOKEN, transport=transport2, sleep=lambda s: None)
        with self.assertRaises(UpstoxAPIError):
            client2.health()

        transport3 = FakeTransport(
            [make_response(payload={"status": "failure", "data": {}})]
        )
        client3 = UpstoxClient(TOKEN, transport=transport3, sleep=lambda s: None)
        with self.assertRaises(UpstoxAPIError):
            client3.health()

    def test_api_error_extraction(self):
        payload = {
            "status": "error",
            "errors": [
                {"errorCode": "UDAPI100050", "message": "bad instrument"},
            ],
        }
        transport = FakeTransport([make_response(status=400, payload=payload)])
        client = UpstoxClient(TOKEN, transport=transport, sleep=lambda s: None)
        with self.assertRaises(UpstoxAPIError) as ctx:
            client.health()
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.error_code, "UDAPI100050")
        self.assertIn("bad instrument", str(ctx.exception))

    def test_token_redaction(self):
        transport = FakeTransport(
            [URLError(f"connection failed for token {TOKEN}")]
        )
        client = UpstoxClient(TOKEN, transport=transport, sleep=lambda s: None)
        with self.assertRaises(UpstoxTransportError) as ctx:
            client.health()
        self.assertNotIn(TOKEN, str(ctx.exception))
        self.assertIn("[REDACTED]", str(ctx.exception))

        payload = {
            "status": "error",
            "errors": [{"error_code": "E1", "message": f"denied for {TOKEN}"}],
        }
        transport2 = FakeTransport([make_response(status=403, payload=payload)])
        client2 = UpstoxClient(TOKEN, transport=transport2, sleep=lambda s: None)
        with self.assertRaises(UpstoxAPIError) as ctx2:
            client2.health()
        self.assertNotIn(TOKEN, str(ctx2.exception))
        self.assertIn("[REDACTED]", str(ctx2.exception))
        self.assertEqual(ctx2.exception.error_code, "E1")


if __name__ == "__main__":
    unittest.main()
