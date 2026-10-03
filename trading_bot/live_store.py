"""Separate durable live state. All order writes have a committed prior intent."""
import fcntl
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class LiveHalt(Exception):
    pass


@contextmanager
def runner_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise LiveHalt('Another live runner holds this state lock') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


class LiveStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS live_trade (decision_id TEXT PRIMARY KEY, state TEXT NOT NULL)')
            conn.execute('CREATE TABLE IF NOT EXISTS live_event (id INTEGER PRIMARY KEY, decision_id TEXT, event TEXT NOT NULL)')
            conn.execute('CREATE TABLE IF NOT EXISTS live_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.execute('PRAGMA synchronous=FULL')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def metadata(self, key):
        with self._connect() as conn:
            row = conn.execute('SELECT value FROM live_meta WHERE key=?', (key,)).fetchone()
        if not row: return None
        return row[0] if key == 'account' else json.loads(row[0])

    def set_metadata(self, key, value):
        if key not in ('dashboard_broker', 'runner_heartbeat', 'entry_pause'):
            raise LiveHalt('Runtime metadata key not permitted')
        with self._connect() as conn:
            conn.execute('INSERT OR REPLACE INTO live_meta VALUES (?, ?)',
                         (key, json.dumps(value, allow_nan=False)))

    def entry_pause_revision(self):
        return (self.metadata('entry_pause') or {}).get('revision','initial')

    def bind_account(self, account):
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM live_meta WHERE key='account'").fetchone()
            if row and row[0] != account:
                raise LiveHalt('Live journal belongs to another account')
            conn.execute("INSERT OR IGNORE INTO live_meta VALUES ('account', ?)", (account,))

    def bind_capital(self, capital):
        value = str(float(capital))
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM live_meta WHERE key='starting_capital'").fetchone()
            if row and row[0] != value:
                raise LiveHalt('Starting allocation differs from persisted pilot ledger')
            conn.execute("INSERT OR IGNORE INTO live_meta VALUES ('starting_capital', ?)", (value,))

    def save(self, trade, event='STATE'):
        state = json.dumps(trade, allow_nan=False, sort_keys=True)
        with self._connect() as conn:
            previous = conn.execute('SELECT state FROM live_trade WHERE decision_id=?', (trade['decision_id'],)).fetchone()
            if previous and previous[0] == state:
                return
            if previous and json.loads(previous[0])['status'] == 'CLOSED':
                raise LiveHalt('Completed live fills and net P&L are immutable')
            conn.execute('INSERT OR REPLACE INTO live_trade VALUES (?, ?)', (trade['decision_id'], state))
            conn.execute('INSERT INTO live_event (decision_id, event) VALUES (?, ?)',
                         (trade['decision_id'], json.dumps(dict(event=event, state=trade), allow_nan=False)))

    def get(self, decision_id):
        with self._connect() as conn:
            row = conn.execute('SELECT state FROM live_trade WHERE decision_id=?', (decision_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self):
        with self._connect() as conn:
            rows = conn.execute('SELECT state FROM live_trade ORDER BY rowid').fetchall()
        return [json.loads(row[0]) for row in rows]

    def active(self):
        return [t for t in self.all() if t['status'] not in ('CLOSED', 'CANCELLED', 'REJECTED')]
