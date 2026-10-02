import csv
import io
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

BASE_URL = "https://api.kite.trade"

# Calculation/read-only endpoints only. Order placement (/orders, /gtt, ...) is never allowed.
ALLOWED_ENDPOINTS = frozenset(
    {
        ("GET", "/user/profile"),
        ("GET", "/user/margins/equity"),
        ("GET", "/instruments/NFO"),
        ("POST", "/margins/orders"),
        ("POST", "/charges/orders"),
    }
)


class KiteError(Exception):
    pass


class KiteHTTPError(KiteError):
    def __init__(self, status_code, message=''):
        self.status_code = status_code
        super().__init__(f'Kite HTTP {status_code}: {message}'.strip())


class KiteForbiddenEndpoint(KiteError):
    pass


@dataclass(frozen=True)
class KiteInstrument:
    tradingsymbol: str
    expiry: date
    strike: float
    option_type: str
    lot_size: int


Transport = Callable[[str, str, dict, Optional[bytes], float], bytes]


def _default_transport(method, url, headers, body, timeout) -> bytes:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read()).get("message", "")
        except ValueError:
            message = ""
        raise KiteHTTPError(exc.code, message)
    except urllib.error.URLError as exc:
        raise KiteError(f"Could not reach Kite: {exc.reason}")


class KiteClient:
    def __init__(self, api_key: str, access_token: str, transport: Transport = _default_transport):
        if not api_key or not access_token:
            raise KiteError("KITE_API_KEY and KITE_ACCESS_TOKEN are required (run: python -m trading_bot.kite login)")
        self._headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {api_key}:{access_token}",
            "User-Agent": "trading-bot/1.0",
        }
        self._transport = transport

    @classmethod
    def from_env(cls) -> "KiteClient":
        return cls(os.environ.get("KITE_API_KEY", "").strip(), os.environ.get("KITE_ACCESS_TOKEN", "").strip())

    def _call(self, method: str, path: str, payload=None, timeout: float = 15.0) -> bytes:
        if (method, path) not in ALLOWED_ENDPOINTS:
            raise KiteForbiddenEndpoint(f"{method} {path} is not an allowed Kite endpoint")
        headers = dict(self._headers)
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        return self._transport(method, BASE_URL + path, headers, body, timeout)

    def _json(self, method: str, path: str, payload=None):
        envelope = json.loads(self._call(method, path, payload))
        if envelope.get("status") != "success":
            raise KiteError(envelope.get("message") or f"{path} failed")
        return envelope.get("data")

    def available_equity_margin(self) -> float:
        return float((self._json("GET", "/user/margins/equity") or {})["net"])

    def order_margin(self, tradingsymbol: str, quantity: int, price: float) -> float:
        data = self._json(
            "POST",
            "/margins/orders",
            [
                {
                    "exchange": "NFO",
                    "tradingsymbol": tradingsymbol,
                    "transaction_type": "BUY",
                    "variety": "regular",
                    "product": "NRML",
                    "order_type": "LIMIT",
                    "quantity": quantity,
                    "price": price,
                    "trigger_price": 0,
                }
            ],
        )
        return float(data[0]["total"])

    def round_trip_charges(self, tradingsymbol: str, quantity: int, buy_price: float, sell_price: float) -> float:
        legs = [
            {
                "order_id": f"paper-{side.lower()}",
                "exchange": "NFO",
                "tradingsymbol": tradingsymbol,
                "transaction_type": side,
                "variety": "regular",
                "product": "NRML",
                "order_type": "MARKET",
                "quantity": quantity,
                "average_price": price,
            }
            for side, price in (("BUY", buy_price), ("SELL", sell_price))
        ]
        data = self._json("POST", "/charges/orders", legs)
        return sum(float(leg["charges"]["total"]) for leg in data)

    def nifty_options(self) -> "list[KiteInstrument]":
        text = self._call("GET", "/instruments/NFO", timeout=60.0).decode()
        return parse_nifty_options(text)


def parse_nifty_options(csv_text: str) -> "list[KiteInstrument]":
    out = []
    for row in csv.DictReader(io.StringIO(csv_text)):
        if row.get("name") != "NIFTY" or row.get("instrument_type") not in ("CE", "PE"):
            continue
        out.append(
            KiteInstrument(
                tradingsymbol=row["tradingsymbol"],
                expiry=date.fromisoformat(row["expiry"]),
                strike=float(row["strike"]),
                option_type=row["instrument_type"],
                lot_size=int(row["lot_size"]),
            )
        )
    return out


def find_option(instruments, expiry: date, strike: float, option_type: str) -> Optional[KiteInstrument]:
    for inst in instruments:
        if inst.expiry == expiry and abs(inst.strike - strike) < 1e-6 and inst.option_type == option_type:
            return inst
    return None
