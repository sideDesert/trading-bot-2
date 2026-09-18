import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

from trading_bot.upstox import cli
from trading_bot.upstox.client import (
    NIFTY_INSTRUMENT_KEY,
    UpstoxAPIError,
    UpstoxConfigurationError,
    UpstoxValidationError,
)


class FakeClient:
    def __init__(self, data=None, error=None):
        self.data = data if data is not None else {"some": "data"}
        self.error = error
        self.calls = []

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        if self.error is not None:
            raise self.error
        return self.data

    def health(self):
        return self._record("health")

    def market_quotes(self, keys):
        return self._record("market_quotes", keys)

    def option_chain(self, key, expiry):
        return self._record("option_chain", key, expiry)

    def option_contracts(self, key, expiry):
        return self._record("option_contracts", key, expiry)

    def resolve_expiry(self, key, expiry):
        return self._record("resolve_expiry", key, expiry)

    def intraday_candles(self, key, unit, interval):
        return self._record("intraday_candles", key, unit=unit, interval=interval)

    def historical_candles(self, key, from_date, to_date, unit, interval):
        return self._record(
            "historical_candles",
            key,
            from_date,
            to_date,
            unit=unit,
            interval=interval,
        )

    def search_instruments(self, query, **kwargs):
        return self._record("search_instruments", query, **kwargs)


def run_cli(argv, client):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.run(argv, client_factory=lambda: client)
    out = buf.getvalue().strip()
    return code, json.loads(out) if out else None, out


class CliSuccessTests(unittest.TestCase):
    def test_health(self):
        client = FakeClient(data={"ok": 1})
        code, payload, _ = run_cli(["health"], client)
        self.assertEqual(code, 0)
        self.assertEqual(
            payload, {"ok": True, "command": "health", "data": {"ok": 1}}
        )
        self.assertEqual(client.calls[0][0], "health")

    def test_market_quotes(self):
        client = FakeClient()
        code, payload, _ = run_cli(
            ["market-quotes", "--instrument-key", "A", "--instrument-key", "B"],
            client,
        )
        self.assertEqual(code, 0)
        self.assertEqual(client.calls[0][1], (["A", "B"],))
        self.assertEqual(payload["command"], "market-quotes")

    def test_option_chain_defaults(self):
        client = FakeClient()
        code, payload, _ = run_cli(["option-chain"], client)
        self.assertEqual(code, 0)
        name, args, _ = client.calls[0]
        self.assertEqual(name, "option_chain")
        self.assertEqual(args, (NIFTY_INSTRUMENT_KEY, "current_week"))

    def test_option_contracts(self):
        client = FakeClient()
        code, _, _ = run_cli(
            ["option-contracts", "--expiry-date", "2025-01-30"], client
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            client.calls[0][1], (NIFTY_INSTRUMENT_KEY, "2025-01-30")
        )

    def test_resolve_expiry(self):
        client = FakeClient(data="2026-09-22")
        code, payload, _ = run_cli(
            ["resolve-expiry", "--expiry-date", "next_week"], client
        )
        self.assertEqual(code, 0)
        name, args, _ = client.calls[0]
        self.assertEqual(name, "resolve_expiry")
        self.assertEqual(args, (NIFTY_INSTRUMENT_KEY, "next_week"))
        self.assertEqual(payload["data"], "2026-09-22")

    def test_intraday_candles(self):
        client = FakeClient()
        code, payload, _ = run_cli(
            [
                "intraday-candles",
                "--instrument-key",
                "K",
                "--unit",
                "hours",
                "--interval",
                "3",
            ],
            client,
        )
        self.assertEqual(code, 0)
        name, args, kwargs = client.calls[0]
        self.assertEqual(name, "intraday_candles")
        self.assertEqual(args, ("K",))
        self.assertEqual(kwargs, {"unit": "hours", "interval": 3})

    def test_historical_candles(self):
        client = FakeClient()
        code, _, _ = run_cli(
            [
                "historical-candles",
                "--instrument-key",
                "K",
                "--from-date",
                "2025-01-01",
                "--to-date",
                "2025-01-31",
            ],
            client,
        )
        self.assertEqual(code, 0)
        name, args, kwargs = client.calls[0]
        self.assertEqual(name, "historical_candles")
        self.assertEqual(args, ("K", "2025-01-01", "2025-01-31"))
        self.assertEqual(kwargs, {"unit": "minutes", "interval": 1})

    def test_search_instruments(self):
        client = FakeClient()
        code, _, _ = run_cli(
            [
                "search-instruments",
                "--query",
                "nifty",
                "--exchanges",
                "NSE",
                "--page-number",
                "2",
                "--records",
                "5",
            ],
            client,
        )
        self.assertEqual(code, 0)
        name, args, kwargs = client.calls[0]
        self.assertEqual(name, "search_instruments")
        self.assertEqual(args, ("nifty",))
        self.assertEqual(kwargs["exchanges"], "NSE")
        self.assertEqual(kwargs["page_number"], 2)
        self.assertEqual(kwargs["records"], 5)

    def test_compact_json_output(self):
        client = FakeClient(data={"a": 1})
        _, _, raw = run_cli(["health"], client)
        self.assertNotIn(" ", raw)
        self.assertEqual(
            raw, '{"ok":true,"command":"health","data":{"a":1}}'
        )


class CliErrorTests(unittest.TestCase):
    def test_configuration_error(self):
        def factory():
            raise UpstoxConfigurationError("no token configured")

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.run(["health"], client_factory=factory)
        payload = json.loads(buf.getvalue())
        self.assertEqual(code, 2)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "health")
        self.assertEqual(
            payload["error"]["type"], "UpstoxConfigurationError"
        )
        self.assertIsNone(payload["error"]["status_code"])
        self.assertIsNone(payload["error"]["error_code"])

    def test_validation_error_exit_2(self):
        client = FakeClient(error=UpstoxValidationError("bad key"))
        code, payload, _ = run_cli(["option-chain"], client)
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"]["type"], "UpstoxValidationError")

    def test_api_error_exit_1(self):
        error = UpstoxAPIError(
            "denied", status_code=403, error_code="E403"
        )
        client = FakeClient(error=error)
        code, payload, _ = run_cli(["health"], client)
        self.assertEqual(code, 1)
        self.assertEqual(payload["error"]["type"], "UpstoxAPIError")
        self.assertEqual(payload["error"]["status_code"], 403)
        self.assertEqual(payload["error"]["error_code"], "E403")

    def test_no_token_leakage(self):
        from trading_bot.upstox.client import HttpResponse, UpstoxClient

        secret = "super-secret-token-value"
        body = json.dumps(
            {
                "status": "error",
                "errors": [{"message": f"denied for {secret}"}],
            }
        ).encode()
        calls = []

        def transport(request, timeout):
            calls.append(request)
            return HttpResponse(status_code=403, headers={}, body=body)

        client = UpstoxClient(secret, transport=transport, sleep=lambda s: None)
        code, payload, raw = run_cli(["health"], client)
        self.assertEqual(code, 1)
        self.assertNotIn(secret, raw)
        self.assertIn("[REDACTED]", payload["error"]["message"])

    def test_argparse_error_exit_2(self):
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(buf):
                cli.run(["market-quotes"], client_factory=FakeClient)
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
