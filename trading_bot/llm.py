import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.request import Request

BASE_URL = "https://api.openai.com"
RESPONSES_PATH = "/v1/responses"
USER_AGENT = "trading-bot/0.2.0"
_SCHEMA_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@dataclass(frozen=True)
class LLMResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes


class LLMError(Exception):
    pass


class LLMConfigurationError(LLMError):
    pass


class LLMTransportError(LLMError):
    pass


class LLMAPIError(LLMError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        error_code: "str | None" = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


Transport = Callable[[Request, float], LLMResponse]


def _default_transport(request: Request, timeout: float) -> LLMResponse:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return LLMResponse(
                status_code=response.status,
                headers=dict(response.headers.items()),
                body=response.read(),
            )
    except urllib.error.HTTPError as error:
        return LLMResponse(
            status_code=error.code,
            headers=dict(error.headers.items()) if error.headers else {},
            body=error.read() or b"",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise LLMTransportError(f"request failed: {error}") from error


@dataclass(frozen=True)
class OpenAIConfig:
    model: str
    timeout_seconds: float = 12.0
    max_output_tokens: int = 300

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise LLMConfigurationError("model must be a non-empty string")
        if self.timeout_seconds is None or self.timeout_seconds <= 0:
            raise LLMConfigurationError("timeout_seconds must be > 0")
        if not isinstance(self.max_output_tokens, int) or isinstance(
            self.max_output_tokens, bool
        ) or self.max_output_tokens <= 0:
            raise LLMConfigurationError("max_output_tokens must be a positive int")


class OpenAIResponsesClient:
    @classmethod
    def from_env(
        cls,
        *,
        transport: "Transport | None" = None,
    ) -> "OpenAIResponsesClient":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        model = os.environ.get("TRADING_BOT_LLM_MODEL", "")
        if not api_key.strip():
            raise LLMConfigurationError(
                "OPENAI_API_KEY environment variable is not set or is empty"
            )
        if not model.strip():
            raise LLMConfigurationError(
                "TRADING_BOT_LLM_MODEL environment variable is not set or is empty"
            )
        return cls(api_key, OpenAIConfig(model=model), transport=transport)

    def __init__(
        self,
        api_key: str,
        config: OpenAIConfig,
        *,
        transport: "Transport | None" = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise LLMConfigurationError("api_key must be a non-empty string")
        if not isinstance(config, OpenAIConfig):
            raise LLMConfigurationError("config must be an OpenAIConfig")
        self._api_key = api_key
        self._config = config
        self._transport = transport or _default_transport

    @property
    def model(self) -> str:
        return self._config.model

    def _redact(self, text: str) -> str:
        return text.replace(self._api_key, "***")

    def generate(
        self,
        system_prompt: str,
        snapshot_json: str,
        output_schema: Mapping[str, Any],
        repair_error: "str | None" = None,
        schema_name: str = "nifty_shadow_advice",
    ) -> str:
        if not _SCHEMA_NAME_RE.match(schema_name):
            raise LLMConfigurationError("invalid schema_name")
        user_text = "Snapshot:\n" + snapshot_json
        if repair_error is not None:
            user_text += (
                "\nPrevious output was invalid: "
                + repair_error
                + ". Return a corrected JSON object only."
            )
        payload = {
            "model": self._config.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {"type": "input_text", "text": system_prompt}
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_text}],
                },
            ],
            "temperature": 0,
            "max_output_tokens": self._config.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": output_schema,
                }
            },
        }
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            BASE_URL + RESPONSES_PATH,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            response = self._transport(request, self._config.timeout_seconds)
        except LLMError:
            raise
        except Exception as error:
            raise LLMTransportError(
                self._redact(f"request failed: {error}")
            ) from error
        if not (200 <= response.status_code < 300):
            message = f"HTTP {response.status_code}"
            code = None
            try:
                parsed = json.loads(response.body.decode("utf-8", "replace"))
                if isinstance(parsed, dict):
                    error_obj = parsed.get("error")
                    if isinstance(error_obj, dict):
                        message = error_obj.get("message") or message
                        code = error_obj.get("code")
            except ValueError:
                pass
            raise LLMAPIError(
                self._redact(message),
                status_code=response.status_code,
                error_code=code,
            )
        try:
            parsed = json.loads(response.body.decode("utf-8"))
        except ValueError as error:
            raise LLMAPIError("response body is not valid JSON") from error
        text = self._extract_text(parsed)
        if text is None:
            raise LLMAPIError("response contains no output_text")
        return text

    @staticmethod
    def _extract_text(parsed) -> "str | None":
        if not isinstance(parsed, dict):
            return None
        top = parsed.get("output_text")
        if isinstance(top, str):
            return top
        output = parsed.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if (
                        isinstance(part, dict)
                        and part.get("type") == "output_text"
                        and isinstance(part.get("text"), str)
                    ):
                        return part["text"]
        return None
