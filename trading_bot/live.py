"""Explicit live runner. `status`/`validate-config` are offline; `run` can trade."""
import argparse
import json
import os
import sys
import time as time_module
from dataclasses import fields
from datetime import date, datetime
from pathlib import Path

from .config import load_env_file
from .features import IST
from .kite.execution import KiteExecutionClient
from .live_engine import LiveConfig, LiveEngine, positive
from .live_store import LiveStore, LiveHalt, runner_lock
from .upstox.client import UpstoxClient

LIVE_ROOT = Path('data/live')


def read_settings(path):
    raw = json.loads(Path(path).read_text())
    allowed = {f.name for f in fields(LiveConfig)} | {'pilot_start', 'pilot_end',
        'decision_interval_seconds', 'model_timeout_seconds'}
    if set(raw) - allowed:
        raise LiveHalt('Unknown live configuration fields')
    config = LiveConfig(**{f.name: raw[f.name] for f in fields(LiveConfig)})
    start, end = date.fromisoformat(raw['pilot_start']), date.fromisoformat(raw['pilot_end'])
    if not 0 <= (end-start).days <= 14:
        raise LiveHalt('Pilot must have an explicit end within 14 calendar days')
    interval, timeout = raw['decision_interval_seconds'], raw['model_timeout_seconds']
    if type(interval) is not int or interval < 60 or type(timeout) is not int or not 1 <= timeout <= 60:
        raise LiveHalt('Decision interval >=60 seconds and model timeout <=60 required')
    return config, start, end, interval, timeout


def fresh_book(payload, key, now):
    for quote in (payload or {}).values():
        if not isinstance(quote, dict) or quote.get('instrument_token') != key:
            continue
        try:
            stamp = quote.get('last_trade_time')
            stamp = datetime.fromtimestamp(float(stamp)/1000, IST) if stamp is not None else datetime.fromisoformat(quote['timestamp'])
            if not stamp.tzinfo or not 0 <= (now-stamp).total_seconds() <= 15:
                return None
            buy, sell = quote['depth']['buy'], quote['depth']['sell']
            bid, ask = positive(buy[0]['price']), positive(sell[0]['price'])
            if ask < bid:
                return None
            return bid, ask
        except (KeyError, ValueError, TypeError, IndexError, LiveHalt, OverflowError):
            return None
    return None


def validate_contract(payload, contracts):
    matches = [c for c in contracts if c.get('instrument_key') == payload['instrument_key']]
    if len(matches) != 1:
        raise LiveHalt('Selected Upstox contract is missing or ambiguous')
    contract = matches[0]
    expected = 'CE' if payload['action'] == 'LONG_CALL' else 'PE'
    if (str(contract.get('expiry'))[:10] != payload['expiry_date'] or
        contract.get('instrument_type') != expected or float(contract.get('strike_price', 0)) != payload['strike'] or
        contract.get('lot_size') != payload['lot_size']):
        raise LiveHalt('Upstox/Kite contract identity mismatch')


class LiveRunner:
    def __init__(self, engine, upstox, root=LIVE_ROOT, log=print, clock=lambda: datetime.now(IST)):
        self.engine, self.upstox, self.root, self.log = engine, upstox, Path(root), log
        self.clock = clock

    def ingest(self, now):
        inbox = self.root/'inbox'
        inbox.mkdir(parents=True, exist_ok=True)
        for path in sorted(inbox.glob('*.json')):
            # Stop after the first accepted entry. Every other decision must be
            # reconsidered against freshness/busy gates; never batch live buys.
            try:
                payload = json.loads(path.read_text())
                if not self.engine.store.get(payload['decision_id']):
                    validate_contract(payload, self.upstox.option_contracts(expiry_date=payload['expiry_date']))
                    def quote_check():
                        raw = self.upstox.market_quotes([payload['instrument_key']])
                        book = fresh_book(raw, payload['instrument_key'], self.clock())
                        if not book or (book[1]-book[0])/((book[1]+book[0])/2) > .02:
                            raise LiveHalt('Selected option quote stale/missing or spread >2%')
                    self.engine.accept(payload, self.clock(), clock=self.clock, before_submit=quote_check)
                result = 'ACCEPTED_OR_DUPLICATE'
            except (LiveHalt, KeyError, ValueError, TypeError) as error:
                result = 'SKIPPED:'+type(error).__name__
                self.log('Live decision skipped by validation; see processed receipt')
            except Exception:
                self.log('Live input read unavailable; retaining decision for reconciliation')
                return
            done = inbox/'processed'
            done.mkdir(exist_ok=True)
            path.replace(done/path.name)
            (done/(path.stem+'.result.json')).write_text(json.dumps({'result': result}))
            if self.engine.store.active(): return

    def tick(self, now, kill=False):
        active = self.engine.store.active()
        def fresh_bid():
            if not active: return None
            key = active[0]['payload']['instrument_key']
            try:
                raw = self.upstox.market_quotes([key])
                book = fresh_book(raw, key, self.clock())
                return book[0] if book else None
            except Exception:
                return None
        self.engine.step(now, quote_provider=fresh_bid, clock=self.clock, kill=kill)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=LIVE_ROOT)
    parser.add_argument('--env-file', type=Path, default=Path('.env'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    validate = sub.add_parser('validate-config')
    validate.add_argument('--config', type=Path, required=True)
    run = sub.add_parser('run')
    run.add_argument('--config', type=Path, required=True)
    run.add_argument('--enable-live', action='store_true')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == 'validate-config':
            read_settings(args.config)
            print('Live configuration valid; no broker connection made')
            return 0
        if args.command == 'status':
            if not (args.root/'state.sqlite3').exists():
                print('No live state; no broker connection made')
                return 0
            print(json.dumps(LiveStore(args.root/'state.sqlite3').all(), indent=2))
            return 0
        if not args.enable_live:
            raise LiveHalt('run requires --enable-live; this command can place real orders')
        if 'paper' in args.root.name or args.root.resolve() == Path('data').resolve():
            raise LiveHalt('Separate live state directory required')
        config, start, end, _, _ = read_settings(args.config)
        load_env_file(args.env_file, names=('UPSTOX_ACCESS_TOKEN', 'KITE_API_KEY', 'KITE_ACCESS_TOKEN'))
        with runner_lock(args.root/'runner.lock'):
            broker = KiteExecutionClient(os.environ.get('KITE_API_KEY', ''), os.environ.get('KITE_ACCESS_TOKEN', ''), enabled=True)
            runner = LiveRunner(LiveEngine(LiveStore(args.root/'state.sqlite3'), broker, config), UpstoxClient.from_env(), args.root)
            print('LIVE EXECUTION ENABLED; broker-held stops are DAY stop-limit orders', flush=True)
            while True:
                now = datetime.now(IST)
                kill = (args.root/'STOP').exists() or not start <= now.date() <= end
                try:
                    runner.tick(now, kill=kill)
                    if not kill: runner.ingest(now)
                except Exception as error:
                    print('LIVE ATTENTION REQUIRED: '+type(error).__name__+'; inspect Kite orders and positions', file=sys.stderr, flush=True)
                time_module.sleep(1)
    except KeyboardInterrupt:
        print('Runner stopped; inspect Kite. DAY stops expire; positions may remain.', file=sys.stderr)
        return 130
    except Exception as error:
        reason = str(error) if isinstance(error, (LiveHalt, ValueError)) else type(error).__name__
        print('Live command refused: '+reason, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
