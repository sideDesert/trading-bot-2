import hashlib
import os
import stat
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

from trading_bot.kite.login import (
    SESSION_URL,
    KiteLoginError,
    capture_redirect,
    checksum,
    exchange_token,
    login_url,
    parse_request_token,
    write_env_value,
)


class KiteLoginTest(unittest.TestCase):
    def test_login_url(self):
        self.assertEqual(
            login_url("abc"), "https://kite.zerodha.com/connect/login?v=3&api_key=abc"
        )

    def test_checksum_is_sha256_of_key_token_secret(self):
        expected = hashlib.sha256(b"keytoksecret").hexdigest()
        self.assertEqual(checksum("key", "tok", "secret"), expected)

    def test_parse_request_token_from_full_url(self):
        url = "http://127.0.0.1/?action=login&type=login&status=success&request_token=RT123"
        self.assertEqual(parse_request_token(url), "RT123")

    def test_parse_request_token_from_path(self):
        self.assertEqual(parse_request_token("/?request_token=RT9&status=success"), "RT9")

    def test_parse_request_token_rejects_failed_status(self):
        with self.assertRaises(KiteLoginError):
            parse_request_token("http://127.0.0.1/?status=error&request_token=RT")

    def test_parse_request_token_requires_token(self):
        with self.assertRaises(KiteLoginError):
            parse_request_token("http://127.0.0.1/?status=success")

    def test_exchange_token_posts_checksum(self):
        calls = []

        def post(url, data, timeout):
            calls.append((url, data))
            return {"status": "success", "data": {"access_token": "AT", "user_id": "AB1234"}}

        data = exchange_token("key", "secret", "tok", post=post)
        self.assertEqual(data["access_token"], "AT")
        self.assertEqual(calls[0][0], SESSION_URL)
        self.assertEqual(calls[0][1]["checksum"], checksum("key", "tok", "secret"))
        self.assertNotIn("api_secret", calls[0][1])

    def test_exchange_token_rejects_missing_access_token(self):
        with self.assertRaises(KiteLoginError):
            exchange_token("k", "s", "t", post=lambda *a: {"status": "error", "message": "bad"})

    def test_write_env_value_replaces_and_preserves_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("UPSTOX_ACCESS_TOKEN=u\n# note\nKITE_ACCESS_TOKEN=old\n")
            write_env_value(path, "KITE_ACCESS_TOKEN", "new")
            self.assertEqual(
                path.read_text(), "UPSTOX_ACCESS_TOKEN=u\n# note\nKITE_ACCESS_TOKEN=new\n"
            )
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_write_env_value_appends_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("KITE_API_KEY=k\n")
            write_env_value(path, "KITE_ACCESS_TOKEN", "AT")
            self.assertEqual(path.read_text(), "KITE_API_KEY=k\nKITE_ACCESS_TOKEN=AT\n")

    def test_capture_redirect_ignores_favicon_then_captures(self):
        port = 18765
        result = {}
        thread = threading.Thread(
            target=lambda: result.update(path=capture_redirect("127.0.0.1", port, 5.0))
        )
        thread.start()
        time.sleep(0.2)
        base = f"http://127.0.0.1:{port}"
        try:
            urllib.request.urlopen(base + "/favicon.ico")
        except urllib.error.HTTPError:
            pass
        urllib.request.urlopen(base + "/?status=success&request_token=RTX").read()
        thread.join(5)
        self.assertEqual(parse_request_token(result["path"]), "RTX")


if __name__ == "__main__":
    unittest.main()
