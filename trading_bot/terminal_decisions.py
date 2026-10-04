"""Private request/response bridge to an interactive Codex skill; no broker calls."""
import argparse
import json
import os
import re
import secrets
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

from .autopilot import SCHEMA, validate_proposal
from .features import IST
from .live_store import LiveHalt


def write_private_json(path, payload, *, replace=True):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix='.terminal-')
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(payload, stream, default=str, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            temporary_path.replace(path)
        else:
            # Publish a complete response once; duplicate submissions cannot
            # overwrite the decision the runner may already be consuming.
            os.link(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def read_request(root):
    path = Path(root)/'request.json'
    try:
        if path.stat().st_size > 300000:
            raise LiveHalt('Terminal request exceeds size bound')
        request = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    deadline = datetime.fromisoformat(request['deadline'])
    if not deadline.tzinfo or datetime.now(IST) >= deadline:
        return None
    return request


def next_request(root, wait=0):
    deadline = time.monotonic()+wait
    while True:
        request = read_request(root)
        if request and not (Path(root)/(request['request_id']+'.json')).exists():
            return dict(status='READY', **request)
        if time.monotonic() >= deadline:
            outcome_path = Path(root)/'outcome.json'
            try:
                outcome = json.loads(outcome_path.read_text())
            except FileNotFoundError:
                outcome = None
            return dict(status='WAITING', last_outcome=outcome)
        time.sleep(.1)


def submit_proposal(root, request_id, proposal):
    if not re.fullmatch('[0-9a-f]{32}', request_id):
        raise LiveHalt('Invalid terminal request ID')
    request = read_request(root)
    if not request or request['request_id'] != request_id:
        raise LiveHalt('Terminal request expired or superseded')
    validate_proposal(proposal, request['brief'], datetime.now(IST))
    response_path = Path(root)/(request_id+'.json')
    try:
        write_private_json(response_path, dict(request_id=request_id, proposal=proposal), replace=False)
    except FileExistsError:
        raise LiveHalt('Terminal decision already submitted') from None
    return dict(status='SUBMITTED', request_id=request_id, action=proposal['action'],
                meaning='Proposal only; runner validation and broker confirmation still required')


class TerminalDecisionAgent:
    def __init__(self, root, timeout=60):
        self.root, self.timeout = Path(root), timeout
        self.request_id = None

    def finish(self, status, **details):
        write_private_json(self.root/'outcome.json', dict(status=status,
            request_id=self.request_id, checked_at=datetime.now(IST).isoformat(), **details))

    def choose(self, brief, limits):
        self.request_id = secrets.token_hex(16)
        request = dict(request_id=self.request_id, brief=brief, limits=limits, schema=SCHEMA,
            deadline=(datetime.now(IST)+timedelta(seconds=self.timeout)).isoformat())
        if len(json.dumps(request, default=str, allow_nan=False).encode()) > 250000:
            raise LiveHalt('Agent brief exceeds size bound')
        request_path = self.root/'request.json'
        response_path = self.root/(self.request_id+'.json')
        write_private_json(request_path, request)
        self.finish('AWAITING_DECISION')
        deadline = time.monotonic()+self.timeout
        try:
            while time.monotonic() < deadline:
                if response_path.exists():
                    if response_path.stat().st_size > 50000:
                        raise LiveHalt('Terminal response exceeds size bound')
                    response = json.loads(response_path.read_text())
                    if response.get('request_id') != self.request_id:
                        raise LiveHalt('Terminal response identity mismatch')
                    return response['proposal']
                time.sleep(.05)
            self.finish('TIMED_OUT')
            raise LiveHalt('Codex terminal did not respond; no trade')
        finally:
            request_path.unlink(missing_ok=True)
            response_path.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('data/live/terminal'))
    commands = parser.add_subparsers(dest='command', required=True)
    waiting = commands.add_parser('next')
    waiting.add_argument('--wait', type=int, default=0, choices=range(61))
    submission = commands.add_parser('submit')
    submission.add_argument('--request-id', required=True)
    submission.add_argument('--proposal-file', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'next':
            result = next_request(args.root, args.wait)
        else:
            if args.proposal_file.stat().st_size > 50000:
                raise LiveHalt('Terminal proposal exceeds size bound')
            proposal = json.loads(args.proposal_file.read_text())
            result = submit_proposal(args.root, args.request_id, proposal)
        print(json.dumps(result, default=str, allow_nan=False))
        return 0
    except Exception as error:
        message = str(error) if isinstance(error, LiveHalt) else type(error).__name__
        print(json.dumps(dict(status='REFUSED', reason=message)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
