import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Mapping, Sequence
from urllib.request import Request

BASE_URL = "https://api.upstox.com"
NIFTY_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
USER_AGENT = "trading-bot/1.0"

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
RELATIVE_EXPIRIES = frozenset(
    {
        "current_week",
        "next_week",
        "far_week",
        "current_month",
        "next_month",
        "far_month",
    }
)
UNIT_INTERVAL_LIMITS = {
    "minutes": (1, 300),
    "hours": (1, 5),
    "days": (1, 1),
    "weeks": (1, 1),
    "months": (1, 1),
}
INTRADAY_UNITS = frozenset({"minutes", "hours", "days"})
WEEK_ALIAS_INDEX = {"current_week": 0, "next_week": 1, "far_week": 2}
MONTH_ALIAS_INDEX = {"current_month": 0, "next_month": 1, "far_month": 2}


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes


class UpstoxError(Exception):
    pass


class UpstoxConfigurationError(UpstoxError):
    pass


class UpstoxValidationError(UpstoxError):
    pass


class UpstoxTransportError(UpstoxError):
    pass


class UpstoxDataError(UpstoxError):
    pass


class UpstoxAPIError(UpstoxError):
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


Transport = Callable[[Request, float], HttpResponse]


def _default_transport(request: Request, timeout: float) -> HttpResponse:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpResponse(
                status_code=response.status,
                headers=dict(response.headers.items()),
                body=response.read(),
            )
    except urllib.error.HTTPError as error:
        return HttpResponse(
            status_code=error.code,
            headers=dict(error.headers.items()) if error.headers else {},
            body=error.read() or b"",
        )


def _require_nonblank(value: "str | None", name: str) -> str:
    if value is None or not str(value).strip():
        raise UpstoxValidationError(f"{name} must be a non-empty string")
    return str(value)


def _validate_expiry(expiry_date: str) -> str:
    value = _require_nonblank(expiry_date, "expiry_date")
    if value in RELATIVE_EXPIRIES:
        return value
    try:
        date.fromisoformat(value)
    except ValueError:
        raise UpstoxValidationError(
            f"expiry_date must be one of {sorted(RELATIVE_EXPIRIES)} or a YYYY-MM-DD date"
        ) from None
    return value


def _validate_date(value: str, name: str) -> date:
    _require_nonblank(value, name)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise UpstoxValidationError(f"{name} must be a valid YYYY-MM-DD date") from None


def _validate_unit_interval(unit: str, interval: int, allowed_units) -> None:
    _require_nonblank(unit, "unit")
    if unit not in allowed_units:
        raise UpstoxValidationError(
            f"unit must be one of {sorted(allowed_units)}"
        )
    low, high = UNIT_INTERVAL_LIMITS[unit]
    if not isinstance(interval, int) or isinstance(interval, bool) or not low <= interval <= high:
        raise UpstoxValidationError(
            f"interval for unit '{unit}' must be an integer between {low} and {high}"
        )


class UpstoxClient:
    @classmethod
    def from_env(
        cls,
        *,
        transport: "Transport | None" = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> "UpstoxClient":
        token = os.environ.get("UPSTOX_ACCESS_TOKEN", "")
        if not token.strip():
            raise UpstoxConfigurationError(
                "UPSTOX_ACCESS_TOKEN environment variable is not set or is empty"
            )
        return cls(token, transport=transport, sleep=sleep)

    def __init__(
        self,
        access_token: str,
        *,
        timeout: float = 10.0,
        max_retries: int = 2,
        transport: "Transport | None" = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not isinstance(access_token, str) or not access_token.strip():
            raise UpstoxConfigurationError("access_token must be a non-empty string")
        if timeout <= 0:
            raise UpstoxConfigurationError("timeout must be greater than 0")
        if max_retries < 0:
            raise UpstoxConfigurationError("max_retries must be >= 0")
        self._access_token = access_token
        self._timeout = timeout
        self._max_retries = max_retries
        self._transport = transport or _default_transport
        self._sleep = sleep

    def health(self) -> Any:
        return self.market_quotes([NIFTY_INSTRUMENT_KEY])

    def market_quotes(self, instrument_keys: Sequence[str]) -> Any:
        if not instrument_keys:
            raise UpstoxValidationError("instrument_keys must contain at least one key")
        unique: list[str] = []
        seen: set[str] = set()
        for key in instrument_keys:
            cleaned = _require_nonblank(key, "instrument_key")
            if cleaned not in seen:
                seen.add(cleaned)
                unique.append(cleaned)
        if len(unique) > 500:
            raise UpstoxValidationError("instrument_keys supports at most 500 keys")
        query = urllib.parse.urlencode({"instrument_key": ",".join(unique)})
        return self._get(f"/v3/market-quote/quotes?{query}")

    def resolve_expiry(
        self,
        instrument_key: str = NIFTY_INSTRUMENT_KEY,
        expiry_date: str = "current_week",
        *,
        as_of: "date | None" = None,
    ) -> str:
        value = _require_nonblank(expiry_date, "expiry_date")
        if value not in RELATIVE_EXPIRIES:
            return _validate_expiry(value)
        key = _require_nonblank(instrument_key, "instrument_key")
        rows = self._contracts_raw(key)
        return self._resolve_from_rows(value, rows, as_of)

    def option_chain(
        self,
        instrument_key: str = NIFTY_INSTRUMENT_KEY,
        expiry_date: str = "current_week",
    ) -> Any:
        key = _require_nonblank(instrument_key, "instrument_key")
        expiry = self.resolve_expiry(key, expiry_date)
        query = urllib.parse.urlencode(
            {"instrument_key": key, "expiry_date": expiry}
        )
        return self._get(f"/v2/option/chain?{query}")

    def option_contracts(
        self,
        instrument_key: str = NIFTY_INSTRUMENT_KEY,
        expiry_date: "str | None" = "current_week",
    ) -> Any:
        key = _require_nonblank(instrument_key, "instrument_key")
        if expiry_date is None:
            return self._contracts_raw(key)
        if expiry_date in RELATIVE_EXPIRIES:
            rows = self._contracts_raw(key)
            resolved = self._resolve_from_rows(expiry_date, rows, None)
            return [
                row
                for row in rows
                if isinstance(row, dict) and row.get("expiry") == resolved
            ]
        expiry = _validate_expiry(expiry_date)
        params = {"instrument_key": key, "expiry_date": expiry}
        return self._get(f"/v2/option/contract?{urllib.parse.urlencode(params)}")

    def _contracts_raw(self, instrument_key: str) -> Any:
        params = {"instrument_key": instrument_key}
        return self._get(f"/v2/option/contract?{urllib.parse.urlencode(params)}")

    @staticmethod
    def _resolve_from_rows(
        expiry_date: str, rows: Any, as_of: "date | None"
    ) -> str:
        if not isinstance(rows, list):
            raise UpstoxDataError("option contracts response is not a list")
        today = as_of or date.today()
        monthly = expiry_date in MONTH_ALIAS_INDEX
        index = (
            MONTH_ALIAS_INDEX[expiry_date]
            if monthly
            else WEEK_ALIAS_INDEX[expiry_date]
        )
        expiries: set[date] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw = row.get("expiry")
            try:
                expiry = date.fromisoformat(str(raw))
            except (TypeError, ValueError):
                continue
            if expiry < today:
                continue
            if monthly and row.get("weekly") is not False:
                continue
            expiries.add(expiry)
        ordered = sorted(expiries)
        if len(ordered) <= index:
            raise UpstoxDataError(
                f"cannot resolve '{expiry_date}': only {len(ordered)} "
                f"matching future expiries found"
            )
        return ordered[index].isoformat()

    def intraday_candles(
        self,
        instrument_key: str,
        unit: str = "minutes",
        interval: int = 1,
    ) -> Any:
        key = _require_nonblank(instrument_key, "instrument_key")
        _validate_unit_interval(unit, interval, INTRADAY_UNITS)
        encoded = urllib.parse.quote(key, safe="")
        return self._get(
            f"/v3/historical-candle/intraday/{encoded}/{unit}/{interval}"
        )

    def historical_candles(
        self,
        instrument_key: str,
        from_date: str,
        to_date: str,
        unit: str = "minutes",
        interval: int = 1,
    ) -> Any:
        key = _require_nonblank(instrument_key, "instrument_key")
        _validate_unit_interval(unit, interval, UNIT_INTERVAL_LIMITS.keys())
        start = _validate_date(from_date, "from_date")
        end = _validate_date(to_date, "to_date")
        if start > end:
            raise UpstoxValidationError("from_date must be on or before to_date")
        encoded = urllib.parse.quote(key, safe="")
        return self._get(
            f"/v3/historical-candle/{encoded}/{unit}/{interval}/{to_date}/{from_date}"
        )

    def search_instruments(
        self,
        query: str,
        *,
        exchanges: "str | None" = None,
        segments: "str | None" = None,
        instrument_types: "str | None" = None,
        expiry: "str | None" = None,
        atm_offset: "int | None" = None,
        page_number: int = 1,
        records: int = 20,
    ) -> Any:
        text = _require_nonblank(query, "query").strip()
        if len(text) > 50:
            raise UpstoxValidationError("query must be at most 50 characters")
        if not isinstance(page_number, int) or page_number < 1:
            raise UpstoxValidationError("page_number must be an integer >= 1")
        if not isinstance(records, int) or not 1 <= records <= 30:
            raise UpstoxValidationError("records must be an integer between 1 and 30")
        params: dict[str, Any] = {"query": text}
        for name, value in (
            ("exchanges", exchanges),
            ("segments", segments),
            ("instrument_types", instrument_types),
            ("expiry", expiry),
            ("atm_offset", atm_offset),
        ):
            if value is not None:
                params[name] = value
        params["page_number"] = page_number
        params["records"] = records
        return self._get(
            f"/v2/instruments/search?{urllib.parse.urlencode(params)}"
        )

    def _get(self, path_and_query: str) -> Any:
        url = f"{BASE_URL}{path_and_query}"
        request = Request(url, method="GET")
        request.add_header("Accept", "application/json")
        request.add_header("Authorization", f"Bearer {self._access_token}")
        request.add_header("User-Agent", USER_AGENT)
        attempt = 0
        while True:
            response = self._send(request)
            if (
                response.status_code in RETRYABLE_STATUS_CODES
                and attempt < self._max_retries
            ):
                self._sleep(self._retry_delay(response, attempt))
                attempt += 1
                continue
            return self._decode(response)

    def _send(self, request: Request) -> HttpResponse:
        try:
            return self._transport(request, self._timeout)
        except UpstoxError:
            raise
        except Exception as error:
            raise UpstoxTransportError(
                self._redact(f"transport error: {error}")
            ) from None

    def _retry_delay(self, response: HttpResponse, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After") or response.headers.get(
            "retry-after"
        )
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after))
            except (TypeError, ValueError):
                pass
        return float(attempt + 1)

    def _decode(self, response: HttpResponse) -> Any:
        try:
            envelope = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            envelope = None
        if not isinstance(envelope, dict):
            if 200 <= response.status_code < 300:
                raise UpstoxAPIError(
                    "malformed response: expected a JSON object envelope",
                    status_code=response.status_code,
                )
            raise UpstoxAPIError(
                f"request failed with status {response.status_code}",
                status_code=response.status_code,
            )
        status = envelope.get("status")
        if 200 <= response.status_code < 300 and status == "success":
            return envelope.get("data")
        message, error_code = self._extract_error(envelope)
        raise UpstoxAPIError(
            self._redact(message or f"request failed with status {response.status_code}"),
            status_code=response.status_code,
            error_code=error_code,
        )

    @staticmethod
    def _extract_error(envelope: Mapping[str, Any]) -> "tuple[str | None, str | None]":
        errors = envelope.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            first = errors[0]
            message = first.get("message")
            error_code = first.get("errorCode") or first.get("error_code")
            return (
                str(message) if message else None,
                str(error_code) if error_code else None,
            )
        message = envelope.get("message")
        return (str(message) if message else None, None)

    def _redact(self, text: str) -> str:
        return text.replace(self._access_token, "[REDACTED]")
