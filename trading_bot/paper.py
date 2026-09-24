"""Simulated (paper) order engine for agent decisions.

Picks up LONG_CALL / LONG_PUT decisions dropped into data/paper-inbox/ by
`agent_brain record`, simulates a limit entry, then monitors the option on
Upstox and exits at stop / target / 15:20 square-off. Fills use the live
bid/ask so the spread is paid like a real order. Nothing is ever sent to a
broker order endpoint.

Commands:
  run      Run the engine loop for today's session.
  status   Show today's paper trades and day P&L.
  report     Show all-time paper P&L, win rate, and a per-day breakdown.
  dashboard  Build an HTML dashboard of all paper trades and open it.
"""

import argparse
import json
import math
import os
import sys
import time as time_mod
from dataclasses import dataclass, fields
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional

import duckdb

from .config import load_env_file
from .features import IST
from .kite.client import KiteClient, KiteError, find_option
from .market_rules import TradingCalendar
from .risk import calculate_round_trip_cost
from .upstox.client import UpstoxClient

BOUNDARY = "PAPER TRADE - NO REAL ORDER PLACED"


@dataclass(frozen=True)
class PaperConfig:
    risk_per_trade_inr: float = 10000.0
    high_vix_threshold: float = 16.0
    daily_loss_limit_inr: float = 20000.0
    entry_window: timedelta = timedelta(minutes=10)
    latest_entry: time = time(15, 15)
    square_off: time = time(15, 20)
    poll_seconds: float = 5.0


@dataclass
class PaperTrade:
    decision_id: str
    created_at: str
    decided_at: str
    status: str
    action: str
    instrument_key: str
    strike: float
    limit_entry: float
    stop_price: float
    target_price: float
    lot_size: Optional[int] = None
    lots: Optional[int] = None
    risk_budget_inr: Optional[float] = None
    india_vix: Optional[float] = None
    tradingsymbol: Optional[str] = None
    margin_required: Optional[float] = None
    margin_available: Optional[float] = None
    entry_at: Optional[str] = None
    entry_fill: Optional[float] = None
    exit_at: Optional[str] = None
    exit_fill: Optional[float] = None
    exit_reason: Optional[str] = None
    mae: Optional[float] = None
    mfe: Optional[float] = None
    last_bid: Optional[float] = None
    last_ask: Optional[float] = None
    last_quote_at: Optional[str] = None
    gross_pnl: Optional[float] = None
    charges: Optional[float] = None
    charges_source: Optional[str] = None
    net_pnl: Optional[float] = None
    notes: Optional[str] = None

    @property
    def quantity(self) -> int:
        return (self.lots or 0) * (self.lot_size or 0)


_COLUMNS = [f.name for f in fields(PaperTrade)]
_TYPES = {int: "INTEGER", float: "DOUBLE", str: "VARCHAR"}


def _ddl() -> str:
    cols = []
    for f in fields(PaperTrade):
        base = f.type if isinstance(f.type, type) else getattr(f.type, "__args__", (str,))[0]
        sql = _TYPES.get(base, "VARCHAR")
        cols.append(f"{f.name} {sql}" + (" PRIMARY KEY" if f.name == "decision_id" else ""))
    return "CREATE TABLE IF NOT EXISTS paper_trade (" + ", ".join(cols) + ")"


class PaperStore:
    """Opens the paper DB per operation so `status` can read while `run` is live."""

    def __init__(self, path: Path, lock_retries: int = 20):
        self._path = Path(path)
        self._retries = lock_retries
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._exec(lambda c: c.execute(_ddl()))

    def _exec(self, fn):
        for attempt in range(self._retries):
            try:
                conn = duckdb.connect(str(self._path))
            except duckdb.IOException:
                if attempt == self._retries - 1:
                    raise
                time_mod.sleep(0.1)
                continue
            try:
                return fn(conn)
            finally:
                conn.close()

    def upsert(self, trade: PaperTrade) -> None:
        placeholders = ", ".join("?" for _ in _COLUMNS)
        values = [getattr(trade, n) for n in _COLUMNS]
        self._exec(
            lambda c: c.execute(
                f"INSERT OR REPLACE INTO paper_trade ({', '.join(_COLUMNS)}) VALUES ({placeholders})", values
            )
        )

    def _select(self, where: str, params) -> "list[PaperTrade]":
        def run(c):
            cur = c.execute(f"SELECT {', '.join(_COLUMNS)} FROM paper_trade WHERE {where} ORDER BY created_at", params)
            return [PaperTrade(**dict(zip(_COLUMNS, r))) for r in cur.fetchall()]

        return self._exec(run)

    def get(self, decision_id: str) -> Optional[PaperTrade]:
        rows = self._select("decision_id = ?", [decision_id])
        return rows[0] if rows else None

    def active(self) -> "list[PaperTrade]":
        return self._select("status IN ('PENDING_ENTRY', 'OPEN')", [])

    def all(self) -> "list[PaperTrade]":
        return self._select("TRUE", [])

    def for_day(self, day: date) -> "list[PaperTrade]":
        return self._select("substr(created_at, 1, 10) = ?", [day.isoformat()])


def day_net_pnl(trades) -> float:
    return sum(t.net_pnl for t in trades if t.status == "CLOSED" and t.net_pnl is not None)


def risk_budget(vix: Optional[float], config: PaperConfig) -> float:
    if vix is None or vix > config.high_vix_threshold:
        return config.risk_per_trade_inr / 2.0
    return config.risk_per_trade_inr


def size_lots(entry: float, stop: float, lot_size: int, budget: float) -> int:
    per_lot = (entry - stop) * lot_size
    if per_lot <= 0:
        return 0
    return int(math.floor(budget / per_lot + 1e-9))


def top_of_book(quote) -> "tuple[float, float] | None":
    if not isinstance(quote, dict):
        return None
    depth = quote.get("depth") or {}
    buy, sell = depth.get("buy") or [], depth.get("sell") or []
    try:
        bid, ask = float(buy[0]["price"]), float(sell[0]["price"])
    except (IndexError, KeyError, TypeError, ValueError):
        return None
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    return bid, ask


def _quotes_by_token(payload) -> dict:
    out = {}
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, dict) and value.get("instrument_token"):
                out[value["instrument_token"]] = value
    return out


def _iso(dt: datetime) -> str:
    return dt.astimezone(IST).isoformat(timespec="seconds")


class PaperEngine:
    def __init__(self, store: PaperStore, upstox, inbox: Path, kite=None, config: PaperConfig = PaperConfig(), log=print):
        self.store = store
        self.upstox = upstox
        self.kite = kite
        self.inbox = Path(inbox)
        self.config = config
        self.log = log
        self._kite_instruments = None

    def _kite_symbol(self, expiry: Optional[date], strike: float, option_type: str):
        if self.kite is None or expiry is None:
            return None
        if self._kite_instruments is None:
            try:
                self._kite_instruments = self.kite.nifty_options()
            except KiteError as exc:
                self.log(f"Kite instruments unavailable ({exc}); using local charge model.")
                self.kite, self._kite_instruments = None, []
                return None
        return find_option(self._kite_instruments, expiry, strike, option_type)

    # ---- inbox -------------------------------------------------------------

    def ingest(self, now: datetime) -> None:
        if not self.inbox.is_dir():
            return
        done = self.inbox / "processed"
        for path in sorted(self.inbox.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if self.store.get(payload.get("decision_id", "")) is None:
                self._accept(payload, now)
            done.mkdir(exist_ok=True)
            path.replace(done / path.name)

    def _accept(self, p: dict, now: datetime) -> None:
        cfg = self.config
        option_type = "CE" if p["action"] == "LONG_CALL" else "PE"
        trade = PaperTrade(
            decision_id=p["decision_id"],
            created_at=_iso(now),
            decided_at=p["decided_at"],
            status="PENDING_ENTRY",
            action=p["action"],
            instrument_key=p["instrument_key"],
            strike=float(p["strike"]),
            limit_entry=float(p["entry_price"]),
            stop_price=float(p["stop_price"]),
            target_price=float(p["target_price"]),
            india_vix=p.get("india_vix"),
        )
        expiry = date.fromisoformat(p["expiry_date"][:10]) if p.get("expiry_date") else None
        inst = self._kite_symbol(expiry, trade.strike, option_type)
        trade.tradingsymbol = inst.tradingsymbol if inst else None
        trade.lot_size = p.get("lot_size") or (inst.lot_size if inst else None)
        notes = []
        if inst and p.get("lot_size") and inst.lot_size != p["lot_size"]:
            notes.append(f"LOT_SIZE_MISMATCH upstox={p['lot_size']} kite={inst.lot_size}")

        decided = datetime.fromisoformat(p["decided_at"])
        today = self.store.for_day(now.date())
        skip = None
        if now - decided > cfg.entry_window:
            skip = "DECISION_TOO_OLD"
        elif now.timetz().replace(tzinfo=None) >= cfg.latest_entry:
            skip = "LATE_ENTRY_CUTOFF"
        elif self.store.active():
            skip = "ANOTHER_POSITION_ACTIVE"
        elif day_net_pnl(today) <= -cfg.daily_loss_limit_inr:
            skip = "DAILY_LOSS_LIMIT"
        elif not trade.lot_size:
            skip = "LOT_SIZE_UNKNOWN"
        else:
            trade.risk_budget_inr = risk_budget(trade.india_vix, cfg)
            if trade.india_vix is None:
                notes.append("VIX_UNKNOWN_BUDGET_HALVED")
            trade.lots = size_lots(trade.limit_entry, trade.stop_price, trade.lot_size, trade.risk_budget_inr)
            if trade.lots < 1:
                skip = "RISK_BUDGET_TOO_SMALL"

        if skip:
            trade.status, trade.exit_reason = "SKIPPED", skip
        elif self.kite is not None and trade.tradingsymbol:
            try:
                trade.margin_required = self.kite.order_margin(trade.tradingsymbol, trade.quantity, trade.limit_entry)
                trade.margin_available = self.kite.available_equity_margin()
                if trade.margin_required > trade.margin_available:
                    notes.append("REAL_ACCOUNT_WOULD_LACK_MARGIN")
            except KiteError as exc:
                notes.append(f"KITE_MARGIN_UNAVAILABLE: {exc}")
        trade.notes = "; ".join(notes) or None
        self.store.upsert(trade)
        if skip:
            self.log(f"SKIPPED {trade.action} {trade.strike:g} ({skip})")
        else:
            risk = (trade.limit_entry - trade.stop_price) * trade.quantity
            self.log(
                f"ORDER {trade.action} {trade.strike:g} x{trade.lots} lot(s) ({trade.quantity} qty) "
                f"limit ₹{trade.limit_entry:g} stop ₹{trade.stop_price:g} target ₹{trade.target_price:g} "
                f"risk ₹{risk:,.0f}" + (f" [{trade.notes}]" if trade.notes else "")
            )

    # ---- monitoring --------------------------------------------------------

    def monitor(self, now: datetime) -> None:
        active = self.store.active()
        if not active:
            return
        try:
            quotes = _quotes_by_token(self.upstox.market_quotes([t.instrument_key for t in active]))
        except Exception as exc:
            self.log(f"Quote fetch failed ({type(exc).__name__}: {exc}); will retry.")
            return
        for trade in active:
            self._step(trade, top_of_book(quotes.get(trade.instrument_key)), now)

    def _step(self, t: PaperTrade, book, now: datetime) -> None:
        cfg = self.config
        clock = now.timetz().replace(tzinfo=None)
        if t.status == "PENDING_ENTRY":
            if now - datetime.fromisoformat(t.decided_at) > cfg.entry_window or clock >= cfg.latest_entry:
                t.status, t.exit_reason, t.exit_at = "CANCELLED", "ENTRY_NOT_FILLED", _iso(now)
                self.store.upsert(t)
                self.log(f"CANCELLED {t.action} {t.strike:g}: ask never reached ₹{t.limit_entry:g}")
                return
            if book is None:
                return
            bid, ask = book
            t.last_bid, t.last_ask, t.last_quote_at = bid, ask, _iso(now)
            if ask <= t.limit_entry:
                t.status, t.entry_fill, t.entry_at, t.mae, t.mfe = "OPEN", ask, _iso(now), 0.0, 0.0
                self.log(f"FILLED BUY {t.strike:g} {t.action} @ ₹{ask:g} x{t.quantity}")
            self.store.upsert(t)
            return

        if book is None:
            if clock >= cfg.square_off:
                self.log(f"Square-off time but no valid quote for {t.strike:g}; retrying.")
            return
        bid, ask = book
        t.last_bid, t.last_ask, t.last_quote_at = bid, ask, _iso(now)
        move = bid - t.entry_fill
        t.mae, t.mfe = min(t.mae or 0.0, move), max(t.mfe or 0.0, move)
        if bid <= t.stop_price:
            self._close(t, bid, "STOP_HIT", now)
        elif bid >= t.target_price:
            self._close(t, t.target_price, "TARGET_HIT", now)
        elif clock >= cfg.square_off:
            self._close(t, bid, "SQUARE_OFF", now)
        else:
            self.store.upsert(t)

    def _close(self, t: PaperTrade, price: float, reason: str, now: datetime) -> None:
        t.status, t.exit_fill, t.exit_reason, t.exit_at = "CLOSED", price, reason, _iso(now)
        t.gross_pnl = (price - t.entry_fill) * t.quantity
        t.charges, t.charges_source = None, None
        if self.kite is not None and t.tradingsymbol:
            try:
                t.charges = self.kite.round_trip_charges(t.tradingsymbol, t.quantity, t.entry_fill, price)
                t.charges_source = "KITE_CONTRACT_NOTE"
            except KiteError as exc:
                self.log(f"Kite charges unavailable ({exc}); using local model.")
        if t.charges is None:
            cost = calculate_round_trip_cost(t.entry_fill, price, t.lots, t.lot_size, 0.0)
            t.charges, t.charges_source = cost.total - cost.slippage, "LOCAL_MODEL"
        t.net_pnl = t.gross_pnl - t.charges
        self.store.upsert(t)
        day = day_net_pnl(self.store.for_day(now.date()))
        self.log(
            f"EXIT {reason} {t.strike:g} {t.action} @ ₹{price:g}: gross ₹{t.gross_pnl:,.0f}, "
            f"charges ₹{t.charges:,.0f}, net ₹{t.net_pnl:,.0f} | day net ₹{day:,.0f}"
        )
        if day <= -self.config.daily_loss_limit_inr:
            self.log(f"Daily paper-loss limit of ₹{self.config.daily_loss_limit_inr:,.0f} reached. No new paper trades today.")

    def tick(self, now: datetime) -> None:
        self.ingest(now)
        self.monitor(now)


def run_loop(engine: PaperEngine, calendar: TradingCalendar = TradingCalendar(), now_fn=lambda: datetime.now(IST), sleep=time_mod.sleep) -> int:
    today = now_fn().date()
    bounds = calendar.session_bounds(today)
    if bounds is None:
        engine.log(f"No supported NSE session on {today}. Exiting.")
        return 0
    open_t, close_t = bounds
    engine.log(f"Paper engine running for {today}. Watching {engine.inbox} every {engine.config.poll_seconds:g}s. {BOUNDARY}")
    while True:
        now = now_fn()
        clock = now.timetz().replace(tzinfo=None)
        if clock >= close_t:
            active = engine.store.active()
            late = now >= datetime.combine(today, close_t, tzinfo=IST) + timedelta(minutes=10)
            if not active or late:
                for t in active:
                    engine.log(f"WARNING: {t.action} {t.strike:g} still {t.status} after close (no valid quote). Check it manually.")
                day = engine.store.for_day(today)
                engine.log(f"Session closed. {len(day)} paper trade(s) today, day net ₹{day_net_pnl(day):,.0f}.")
                return 0
        if clock >= open_t:
            engine.tick(now)
        sleep(engine.config.poll_seconds)


def format_status(trades) -> str:
    if not trades:
        return "No paper trades today."
    lines = []
    for t in trades:
        line = f"{t.created_at[11:16]} {t.action} {t.strike:g} {t.status}"
        if t.status == "SKIPPED":
            line += f" ({t.exit_reason})"
        if t.entry_fill is not None:
            line += f" | x{t.lots} in ₹{t.entry_fill:g}"
        if t.status == "OPEN" and t.last_bid is not None:
            line += f" bid ₹{t.last_bid:g} unrealised ₹{(t.last_bid - t.entry_fill) * t.quantity:,.0f}"
        if t.status == "CLOSED":
            line += f" out ₹{t.exit_fill:g} {t.exit_reason} net ₹{t.net_pnl:,.0f} ({t.charges_source})"
        lines.append(line)
    lines.append(f"Day net (closed): ₹{day_net_pnl(trades):,.0f}")
    return "\n".join(lines)


def _paint(text: str, code: str, color: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if color else text


def _money(value: float, color: bool) -> str:
    text = f"₹{value:,.0f}"
    if value > 0:
        return _paint(text, "32", color)
    if value < 0:
        return _paint(text, "31", color)
    return text


def format_report(trades, color: bool = False) -> str:
    closed = [t for t in trades if t.status == "CLOSED" and t.net_pnl is not None]
    if not closed:
        return "No closed paper trades yet."
    wins = [t.net_pnl for t in closed if t.net_pnl > 0]
    losses = [t.net_pnl for t in closed if t.net_pnl <= 0]
    rate = len(wins) / len(closed)
    rate_text = _paint(f"{rate:.0%}", "32" if rate >= 0.5 else "31", color)
    net = sum(t.net_pnl for t in closed)
    lines = [
        _paint("Paper trading report", "1", color),
        f"Closed paper trades: {len(closed)} ({_paint(f'{len(wins)} won', '32', color)}, "
        f"{_paint(f'{len(losses)} lost', '31', color)}, win rate {rate_text})",
        f"Gross P&L:   {_money(sum(t.gross_pnl for t in closed), color)}",
        f"Charges:     {_paint(f'₹{sum(t.charges for t in closed):,.0f}', '33', color)}",
        _paint("Net P&L:     ", "1", color) + _paint(_money(net, color), "1", color),
    ]
    if wins:
        lines.append(f"Average win:  {_money(sum(wins) / len(wins), color)}")
    if losses:
        lines.append(f"Average loss: {_money(sum(losses) / len(losses), color)}")
    lines.append(f"Best trade:   {_money(max(t.net_pnl for t in closed), color)}")
    lines.append(f"Worst trade:  {_money(min(t.net_pnl for t in closed), color)}")
    other = {}
    for t in trades:
        if t.status in ("SKIPPED", "CANCELLED"):
            other[t.status] = other.get(t.status, 0) + 1
    if other:
        lines.append(_paint("Not traded: " + ", ".join(f"{n} {k.lower()}" for k, n in sorted(other.items())), "2", color))
    lines.append("")
    lines.append(_paint("By day:", "1", color))
    days = {}
    for t in closed:
        days.setdefault(t.created_at[:10], []).append(t.net_pnl)
    for day in sorted(days):
        pnl = days[day]
        lines.append(f"  {day}  {len(pnl)} trade(s)  net {_money(sum(pnl), color)}")
    open_now = [t for t in trades if t.status in ("PENDING_ENTRY", "OPEN")]
    if open_now:
        lines.append(_paint(f"({len(open_now)} trade(s) still pending/open, not included)", "2", color))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading_bot.paper", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--paper-db", type=Path, default=Path("data/paper.duckdb"))
    parser.add_argument("--inbox", type=Path, default=Path("data/paper-inbox"))
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--no-kite", action="store_true", help="Skip Kite margin/charges; use local cost model")
    sub.add_parser("status")
    sub.add_parser("report")
    dash = sub.add_parser("dashboard")
    dash.add_argument("--out", type=Path, default=Path("data/paper-dashboard.html"))
    dash.add_argument("--no-open", action="store_true")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    store = PaperStore(args.paper_db)
    if args.command == "status":
        print(format_status(store.for_day(datetime.now(IST).date())))
        print(BOUNDARY)
        return
    if args.command == "dashboard":
        import webbrowser
        from .paper_dashboard import render_dashboard

        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_dashboard(store.all(), datetime.now(IST)), encoding="utf-8")
        print(f"Dashboard written to {args.out}")
        if not args.no_open:
            webbrowser.open(args.out.resolve().as_uri())
        return
    if args.command == "report":
        use_color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
        print(format_report(store.all(), color=use_color))
        print(BOUNDARY)
        return
    load_env_file(args.env_file, names=("UPSTOX_ACCESS_TOKEN", "KITE_API_KEY", "KITE_ACCESS_TOKEN"))
    kite = None
    if not args.no_kite:
        try:
            kite = KiteClient.from_env()
            kite.available_equity_margin()
        except KiteError as exc:
            print(f"Kite unavailable ({exc}). Continuing with local charge model.", file=sys.stderr)
            kite = None
    engine = PaperEngine(store, UpstoxClient.from_env(), args.inbox, kite=kite, log=lambda m: print(f"[{datetime.now(IST):%H:%M:%S}] {m}", flush=True))
    try:
        sys.exit(run_loop(engine))
    except KeyboardInterrupt:
        print("\nStopped. Open paper positions stay open and resume on the next run.")
        sys.exit(130)


if __name__ == "__main__":
    main()
