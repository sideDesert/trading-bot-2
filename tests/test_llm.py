import json
import os
import unittest
from unittest import mock

from trading_bot.llm import (
    LLMAPIError,
    LLMConfigurationError,
    LLMResponse,
    LLMTransportError,
    OpenAIConfig,
    OpenAIResponsesClient,
)

SCHEMA = {"type": "object", "properties": {"action": {"type": "string"}}}


def ok_response(text='{"action":"NO_TRADE"}', status=200):
    body = json.dumps(
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": text},
                    ],
                }
            ]
        }
    ).encode()
    return LLMResponse(status_code=status, headers={}, body=body)


class RecordingTransport:
    def __init__(self, response=None, error=None):
        self.response = response or ok_response()
        self.error = error
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        if self.error is not None:
            raise self.error
        return self.response


def make_client(transport, **config_kw):
    return OpenAIResponsesClient(
        "sk-secret-key",
        OpenAIConfig(model="gpt-test", **config_kw),
        transport=transport,
    )


class OpenAIResponsesClientTests(unittest.TestCase):
    def test_request_shape(self):
        transport = RecordingTransport()
        client = make_client(transport)
        result = client.generate("SYS", '{"a":1}', SCHEMA)
        self.assertEqual(result, '{"action":"NO_TRADE"}')
        request, timeout = transport.requests[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(timeout, 12.0)
        self.assertEqual(request.headers["Authorization"], "Bearer sk-secret-key")
        self.assertEqual(request.headers["Content-type"], "application/json")
        self.assertEqual(request.headers["Accept"], "application/json")
        self.assertEqual(request.headers["User-agent"], "trading-bot/0.2.0")
        body = json.loads(request.data.decode())
        self.assertEqual(body["model"], "gpt-test")
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["max_output_tokens"], 300)
        self.assertEqual(
            body["text"]["format"],
            {
                "type": "json_schema",
                "name": "nifty_shadow_advice",
                "strict": True,
                "schema": SCHEMA,
            },
        )
        self.assertEqual(body["input"][0]["role"], "system")
        self.assertEqual(
            body["input"][0]["content"],
            [{"type": "input_text", "text": "SYS"}],
        )
        self.assertEqual(
            body["input"][1]["content"][0]["text"], "Snapshot:\n{\"a\":1}"
        )

    def test_repair_error_appended(self):
        transport = RecordingTransport()
        client = make_client(transport)
        client.generate("SYS", "{}", SCHEMA, repair_error="SCHEMA")
        body = json.loads(transport.requests[0][0].data.decode())
        text = body["input"][1]["content"][0]["text"]
        self.assertIn("Previous output was invalid: SCHEMA", text)
        self.assertTrue(text.endswith("Return a corrected JSON object only."))

    def test_top_level_output_text_accepted(self):
        response = LLMResponse(
            status_code=200,
            headers={},
            body=json.dumps({"output_text": "{\"x\":1}"}).encode(),
        )
        client = make_client(RecordingTransport(response=response))
        self.assertEqual(client.generate("S", "{}", SCHEMA), "{\"x\":1}")

    def test_config_timeout_and_tokens(self):
        transport = RecordingTransport()
        client = make_client(
            transport, timeout_seconds=3.5, max_output_tokens=50
        )
        client.generate("S", "{}", SCHEMA)
        request, timeout = transport.requests[0]
        self.assertEqual(timeout, 3.5)
        self.assertEqual(json.loads(request.data.decode())["max_output_tokens"], 50)

    def test_config_validation(self):
        with self.assertRaises(LLMConfigurationError):
            OpenAIConfig(model=" ")
        with self.assertRaises(LLMConfigurationError):
            OpenAIConfig(model="m", timeout_seconds=0)
        with self.assertRaises(LLMConfigurationError):
            OpenAIConfig(model="m", max_output_tokens=0)
        with self.assertRaises(LLMConfigurationError):
            OpenAIResponsesClient("  ", OpenAIConfig(model="m"))

    def test_non_2xx_extracts_error_message(self):
        response = LLMResponse(
            status_code=429,
            headers={},
            body=json.dumps(
                {"error": {"message": "rate limited", "code": "rate_limit"}}
            ).encode(),
        )
        client = make_client(RecordingTransport(response=response))
        with self.assertRaises(LLMAPIError) as ctx:
            client.generate("S", "{}", SCHEMA)
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(str(ctx.exception), "rate limited")
        self.assertEqual(ctx.exception.error_code, "rate_limit")

    def test_malformed_and_missing_output(self):
        bad_json = LLMResponse(status_code=200, headers={}, body=b"not json")
        client = make_client(RecordingTransport(response=bad_json))
        with self.assertRaises(LLMAPIError):
            client.generate("S", "{}", SCHEMA)
        no_text = LLMResponse(
            status_code=200, headers={}, body=b'{"output":[]}'
        )
        client2 = make_client(RecordingTransport(response=no_text))
        with self.assertRaises(LLMAPIError):
            client2.generate("S", "{}", SCHEMA)

    def test_transport_error_and_key_redaction(self):
        client = make_client(
            RecordingTransport(error=RuntimeError("bad sk-secret-key boom"))
        )
        with self.assertRaises(LLMTransportError) as ctx:
            client.generate("S", "{}", SCHEMA)
        self.assertNotIn("sk-secret-key", str(ctx.exception))
        self.assertIn("***", str(ctx.exception))

    def test_from_env_requires_key_and_model(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(LLMConfigurationError):
                OpenAIResponsesClient.from_env()
        with mock.patch.dict(
            os.environ, {"OPENAI_API_KEY": "k"}, clear=True
        ):
            with self.assertRaises(LLMConfigurationError):
                OpenAIResponsesClient.from_env()
        with mock.patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "k", "TRADING_BOT_LLM_MODEL": "m9"},
            clear=True,
        ):
            client = OpenAIResponsesClient.from_env(
                transport=RecordingTransport()
            )
            self.assertEqual(client.model, "m9")


if __name__ == "__main__":
    unittest.main()
