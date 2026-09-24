import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable, Optional

from ..config import load_env_file

LOGIN_URL = "https://kite.zerodha.com/connect/login"
SESSION_URL = "https://api.kite.trade/session/token"
ENV_NAMES = ("KITE_API_KEY", "KITE_API_SECRET")
TOKEN_NAME = "KITE_ACCESS_TOKEN"


class KiteLoginError(Exception):
    pass


def login_url(api_key: str) -> str:
    return LOGIN_URL + "?" + urllib.parse.urlencode({"v": "3", "api_key": api_key})


def checksum(api_key: str, request_token: str, api_secret: str) -> str:
    return hashlib.sha256((api_key + request_token + api_secret).encode()).hexdigest()


def parse_request_token(redirect: str) -> str:
    query = urllib.parse.urlparse(redirect.strip()).query or redirect.strip()
    params = urllib.parse.parse_qs(query)
    status = params.get("status", [""])[0]
    token = params.get("request_token", [""])[0]
    if status and status != "success":
        raise KiteLoginError(f"Zerodha login returned status={status}")
    if not token:
        raise KiteLoginError("No request_token found in the redirect URL")
    return token


def _post(url: str, data: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"X-Kite-Version": "3", "User-Agent": "trading-bot/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read()).get("message", "")
        except ValueError:
            message = ""
        raise KiteLoginError(f"Session exchange failed (HTTP {exc.code}) {message}".strip())
    except urllib.error.URLError as exc:
        raise KiteLoginError(f"Could not reach Kite: {exc.reason}")


Poster = Callable[[str, dict, float], dict]


def exchange_token(
    api_key: str, api_secret: str, request_token: str, post: Poster = _post
) -> dict:
    payload = post(
        SESSION_URL,
        {
            "api_key": api_key,
            "request_token": request_token,
            "checksum": checksum(api_key, request_token, api_secret),
        },
        15.0,
    )
    data = payload.get("data") or {}
    if payload.get("status") != "success" or not data.get("access_token"):
        raise KiteLoginError(payload.get("message") or "Session exchange returned no access_token")
    return data


def write_env_value(path: Path, name: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out, replaced = [], False
    for line in lines:
        key = line.strip().removeprefix("export ").split("=", 1)[0].strip()
        if key == name and "=" in line:
            if not replaced:
                out.append(f"{name}={value}")
                replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(f"{name}={value}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def capture_redirect(host: str, port: int, timeout: float) -> Optional[str]:
    captured: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if "request_token=" not in self.path:
                self.send_response(404)
                self.end_headers()
                return
            captured["path"] = self.path
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Kite login captured. You can close this tab.")

        def log_message(self, *args):
            pass

    try:
        server = HTTPServer((host, port), Handler)
    except OSError as exc:
        print(f"Could not listen on {host}:{port} ({exc.strerror}).", file=sys.stderr)
        return None
    deadline = time.monotonic() + timeout
    with server:
        while "path" not in captured:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                print("Timed out waiting for the redirect.", file=sys.stderr)
                return None
            server.timeout = remaining
            server.handle_request()
    return captured["path"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading_bot.kite", description="Zerodha Kite login")
    sub = parser.add_subparsers(dest="command", required=True)
    login = sub.add_parser("login", help="Get today's Kite access token and save it to .env")
    login.add_argument("--env-file", default=".env")
    login.add_argument("--host", default="127.0.0.1")
    login.add_argument("--port", type=int, default=80)
    login.add_argument("--timeout", type=float, default=180.0)
    login.add_argument("--paste", action="store_true", help="Skip the local listener; paste the redirect URL")
    login.add_argument("--no-browser", action="store_true")
    return parser


def run_login(args) -> int:
    env_path = Path(args.env_file)
    load_env_file(env_path, names=ENV_NAMES)
    api_key = os.environ.get("KITE_API_KEY", "").strip()
    api_secret = os.environ.get("KITE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise KiteLoginError("KITE_API_KEY and KITE_API_SECRET must be set in .env")

    url = login_url(api_key)
    print(f"Log in to Zerodha here:\n  {url}")
    if not args.no_browser:
        webbrowser.open(url)

    redirect = None
    if not args.paste:
        print(f"Waiting for the redirect on http://{args.host}:{args.port} ...")
        redirect = capture_redirect(args.host, args.port, args.timeout)
    if redirect is None:
        redirect = input("Paste the full URL from your browser's address bar after login: ")

    data = exchange_token(api_key, api_secret, parse_request_token(redirect))
    write_env_value(env_path, TOKEN_NAME, data["access_token"])
    print(f"Saved {TOKEN_NAME} to {env_path} for user {data.get('user_id', '?')}. It expires around 06:00 IST tomorrow.")
    return 0


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    try:
        sys.exit(run_login(args))
    except KiteLoginError as exc:
        print(f"Kite login failed: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
