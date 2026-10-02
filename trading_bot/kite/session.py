"""Private shared daily token file for the web login and execution service."""
import json
import os
import secrets
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from ..features import IST
from ..live_store import LiveHalt


class KiteSessionStore:
    def __init__(self, path):
        self.path = Path(path)

    def save(self, access_token, account_id, now):
        if not isinstance(access_token, str) or not access_token or any(c.isspace() for c in access_token):
            raise LiveHalt('Invalid broker token')
        now = now.astimezone(IST)
        expiry = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if expiry <= now: expiry += timedelta(days=1)
        payload = dict(access_token=access_token, account_id=account_id, generation=secrets.token_hex(16),
                       obtained_at=now.isoformat(), expires_at=expiry.isoformat())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.kite-session-', dir=self.path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, 'w') as handle:
                json.dump(payload, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
        return payload

    def load(self, now, account_id):
        try:
            if self.path.stat().st_mode & 0o077:
                raise LiveHalt('Broker token file permissions are unsafe')
            data = json.loads(self.path.read_text())
            if data['account_id'] != account_id or not data['access_token']:
                raise LiveHalt('Broker session account mismatch')
            expiry = datetime.fromisoformat(data['expires_at'])
            if not expiry.tzinfo or now >= expiry:
                raise LiveHalt('Daily Kite login expired')
            return data
        except (ValueError, KeyError, TypeError, OSError):
            raise LiveHalt('Broker session unavailable') from None


def execution_token(root, account_id, now, fallback=''):
    store = KiteSessionStore(Path(root)/'kite-session.json')
    if store.path.exists():
        return store.load(now, account_id)['access_token']
    return fallback
