import argparse
import json
from typing import Callable, Sequence

from .client import (
    NIFTY_INSTRUMENT_KEY,
    UpstoxAPIError,
    UpstoxClient,
    UpstoxConfigurationError,
    UpstoxDataError,
    UpstoxError,
    UpstoxValidationError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot.upstox",
        description="Read-only Upstox API tools",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")

    quotes = sub.add_parser("market-quotes")
    quotes.add_argument("--instrument-key", action="append", required=True)

    chain = sub.add_parser("option-chain")
    chain.add_argument("--instrument-key", default=NIFTY_INSTRUMENT_KEY)
    chain.add_argument("--expiry-date", default="current_week")

    contracts = sub.add_parser("option-contracts")
    contracts.add_argument("--instrument-key", default=NIFTY_INSTRUMENT_KEY)
    contracts.add_argument("--expiry-date", default="current_week")

    resolve = sub.add_parser("resolve-expiry")
    resolve.add_argument("--instrument-key", default=NIFTY_INSTRUMENT_KEY)
    resolve.add_argument("--expiry-date", default="current_week")

    intraday = sub.add_parser("intraday-candles")
    intraday.add_argument("--instrument-key", required=True)
    intraday.add_argument("--unit", default="minutes")
    intraday.add_argument("--interval", type=int, default=1)

    historical = sub.add_parser("historical-candles")
    historical.add_argument("--instrument-key", required=True)
    historical.add_argument("--from-date", required=True)
    historical.add_argument("--to-date", required=True)
    historical.add_argument("--unit", default="minutes")
    historical.add_argument("--interval", type=int, default=1)

    search = sub.add_parser("search-instruments")
    search.add_argument("--query", required=True)
    search.add_argument("--exchanges")
    search.add_argument("--segments")
    search.add_argument("--instrument-types")
    search.add_argument("--expiry")
    search.add_argument("--atm-offset", type=int)
    search.add_argument("--page-number", type=int, default=1)
    search.add_argument("--records", type=int, default=20)

    return parser


def _dispatch(client: UpstoxClient, args: argparse.Namespace):
    if args.command == "health":
        return client.health()
    if args.command == "market-quotes":
        return client.market_quotes(args.instrument_key)
    if args.command == "option-chain":
        return client.option_chain(args.instrument_key, args.expiry_date)
    if args.command == "option-contracts":
        return client.option_contracts(args.instrument_key, args.expiry_date)
    if args.command == "resolve-expiry":
        return client.resolve_expiry(args.instrument_key, args.expiry_date)
    if args.command == "intraday-candles":
        return client.intraday_candles(
            args.instrument_key, unit=args.unit, interval=args.interval
        )
    if args.command == "historical-candles":
        return client.historical_candles(
            args.instrument_key,
            args.from_date,
            args.to_date,
            unit=args.unit,
            interval=args.interval,
        )
    if args.command == "search-instruments":
        return client.search_instruments(
            args.query,
            exchanges=args.exchanges,
            segments=args.segments,
            instrument_types=args.instrument_types,
            expiry=args.expiry,
            atm_offset=args.atm_offset,
            page_number=args.page_number,
            records=args.records,
        )
    raise UpstoxValidationError(f"unknown command: {args.command}")


def _emit(payload) -> None:
    print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))


def run(
    argv: "Sequence[str] | None" = None,
    *,
    client_factory: Callable[[], UpstoxClient] = UpstoxClient.from_env,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = client_factory()
        data = _dispatch(client, args)
    except (UpstoxConfigurationError, UpstoxValidationError) as error:
        _emit(
            {
                "ok": False,
                "command": args.command,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                    "status_code": None,
                    "error_code": None,
                },
            }
        )
        return 2
    except UpstoxError as error:
        status_code = (
            error.status_code if isinstance(error, UpstoxAPIError) else None
        )
        error_code = (
            error.error_code if isinstance(error, UpstoxAPIError) else None
        )
        _emit(
            {
                "ok": False,
                "command": args.command,
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                    "status_code": status_code,
                    "error_code": error_code,
                },
            }
        )
        return 1
    _emit({"ok": True, "command": args.command, "data": data})
    return 0


def main() -> None:
    raise SystemExit(run())
