import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from trading_bot.config import load_env_file


class LoadEnvFileTests(unittest.TestCase):
    def _write(self, content):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / ".env"
        path.write_text(content)
        return path

    def test_loads_unquoted(self):
        path = self._write("UPSTOX_ACCESS_TOKEN=abc123\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(load_env_file(path))
            self.assertEqual(os.environ["UPSTOX_ACCESS_TOKEN"], "abc123")

    def test_quoted_and_export(self):
        for content in (
            "export UPSTOX_ACCESS_TOKEN='q1'\n",
            'UPSTOX_ACCESS_TOKEN="q2"\n',
        ):
            path = self._write(content)
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertTrue(load_env_file(path))
                self.assertTrue(
                    os.environ["UPSTOX_ACCESS_TOKEN"] in ("q1", "q2")
                )

    def test_ignores_comments_blanks_and_other_vars(self):
        path = self._write(
            "# comment\n\nOTHER=value\ngarbage line\nUPSTOX_ACCESS_TOKEN=tok\n"
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(load_env_file(path))
            self.assertEqual(os.environ["UPSTOX_ACCESS_TOKEN"], "tok")
            self.assertNotIn("OTHER", os.environ)

    def test_existing_env_wins(self):
        path = self._write("UPSTOX_ACCESS_TOKEN=file_value\n")
        with mock.patch.dict(
            os.environ, {"UPSTOX_ACCESS_TOKEN": "env_value"}, clear=True
        ):
            self.assertFalse(load_env_file(path))
            self.assertEqual(os.environ["UPSTOX_ACCESS_TOKEN"], "env_value")

    def test_missing_file_and_empty_value(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(load_env_file("/nonexistent/.env"))
            path = self._write("UPSTOX_ACCESS_TOKEN=\n")
            self.assertFalse(load_env_file(path))
            self.assertNotIn("UPSTOX_ACCESS_TOKEN", os.environ)


if __name__ == "__main__":
    unittest.main()
