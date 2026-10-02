"""Long-only Kite lifecycle. One entry, one working sell, no synthetic OCO."""
import hashlib
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_FLOOR

from .features import IST
from .kite.client import KiteError, find_option
from .kite.execution import AmbiguousOrderError
from .live_store import LiveHalt
from .market_rules import TradingCalendar

TERMINAL = frozenset({'COMPLETE', 'CANCELLED', 'REJECTED'})
WORKING = frozenset({'OPEN', 'TRIGGER PENDING'})


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise LiveHalt('Positive finite market/risk values required')
    return value


def grid(value, tick=.05):
    units = Decimal(str(value)) / Decimal(str(tick))
    return units == units.to_integral_value()


def floor_tick(value, tick=.05):
    return float((Decimal(str(value)) / Decimal(str(tick))).to_integral_value(rounding=ROUND_FLOOR) * Decimal(str(tick)))


@dataclass(frozen=True)
class LiveConfig:
    account_id: str
    risk_per_trade_inr: float
    capital_limit_inr: float
    daily_loss_limit_inr: float
    stop_limit_buffer: float
    fee_reserve_inr: float = 200
    max_lots: int = 1

    def __post_init__(self):
        if not self.account_id or not self.account_id.isalnum():
            raise ValueError('Explicit Kite account ID required')
        values = (self.risk_per_trade_inr, self.capital_limit_inr, self.daily_loss_limit_inr,
                  self.stop_limit_buffer, self.fee_reserve_inr)
        if any(not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError('Explicit positive finite live limits required')
        if self.risk_per_trade_inr > 2500 or self.daily_loss_limit_inr > 5000:
            raise ValueError('Initial live version caps planned risk at 2500/trade and daily loss at 5000')
        if not grid(self.stop_limit_buffer):
            raise ValueError('Stop limit buffer must be on the 0.05 tick grid')
        if type(self.max_lots) is not int or not 1 <= self.max_lots <= 10:
            raise ValueError('Explicit maximum lots must be between 1 and 10')
        if self.fee_reserve_inr < 200:
            raise ValueError('At least 200 INR fee reserve required')


class LiveEngine:
    def __init__(self, store, broker, config):
        self.store, self.broker, self.config = store, broker, config
        self.store.bind_account(config.account_id)
        self.store.bind_capital(config.capital_limit_inr)

    def capital_status(self, cash=None):
        trades = self.store.all()
        completed = [t for t in trades if t['status'] == 'CLOSED']
        for trade in completed:
            if any(type(trade.get(k)) not in (int, float) or not math.isfinite(trade[k])
                   for k in ('net_pnl', 'charges', 'gross_pnl')):
                raise LiveHalt('Completed net P&L or charges missing; capital unavailable')
            if trade['charges'] < 0 or abs(trade['net_pnl']-(trade['gross_pnl']-trade['charges'])) > .001:
                raise LiveHalt('Completed capital ledger inconsistent')
        net = sum(t['net_pnl'] for t in completed)
        allocation = self.config.capital_limit_inr + net
        commitments = 0
        for trade in self.store.active():
            entry = trade.get('entry', {})
            remaining = entry.get('filled', 0) - sum(s.get('filled', 0) for s in trade['sells'])
            pending_buy = 0 if entry.get('snapshot', {}).get('status') in TERMINAL else trade['quantity']-entry.get('filled', 0)
            commitments += max(0, remaining+pending_buy)*trade['payload']['entry_price'] + self.config.fee_reserve_inr
        cash = self.broker.cash_available() if cash is None else cash
        if not math.isfinite(cash): raise LiveHalt('Broker cash unavailable')
        return dict(starting_capital_inr=self.config.capital_limit_inr, realized_net_pnl_inr=net,
                    allocation_inr=allocation, committed_inr=commitments,
                    broker_cash_inr=cash, available_for_new_trade_inr=max(0, min(allocation-commitments, cash)))

    def _account(self):
        if self.broker.profile().get('user_id') != self.config.account_id:
            raise LiveHalt('Kite account does not match live configuration')

    def _snapshot(self, trade, book):
        """Adopt exact tag/ID matches and monotonically confirmed fills."""
        known = {o['order_id']: o for o in book}
        legs = ([trade['entry']] if trade.get('entry') else []) + trade['sells']
        for leg in legs:
            matches = [o for o in book if o.get('tag') == leg['tag']]
            if len(matches) > 1:
                raise LiveHalt('Duplicate broker tag; manual reconciliation required')
            order = known.get(leg.get('id')) if leg.get('id') else (matches[0] if matches else None)
            if not order:
                if leg.get('id'):
                    raise LiveHalt('Known order missing from daily broker book')
                continue
            if (order.get('tradingsymbol') != trade['symbol'] or order.get('exchange') != 'NFO' or
                    order.get('product') != 'NRML' or order.get('transaction_type') != leg['side'] or
                    order.get('tag') != leg['tag']):
                raise LiveHalt('Broker order identity mismatch')
            filled = int(order['filled_quantity'])
            if filled < leg.get('filled', 0) or filled > int(order['quantity']) or filled < 0:
                raise LiveHalt('Broker fill quantity inconsistent')
            if leg['side'] == 'BUY' and int(order['quantity']) != trade['quantity']:
                raise LiveHalt('Entry quantity changed outside bot')
            if leg['side'] == 'SELL':
                earlier = trade['sells'][:trade['sells'].index(leg)]
                maximum = trade['entry'].get('filled', 0) - sum(s.get('filled', 0) for s in earlier)
                if int(order['quantity']) > maximum:
                    raise LiveHalt('Sell quantity exceeds confirmed owned exposure')
            leg.update(id=str(order['order_id']), filled=filled, snapshot=order)
            if leg['side'] == 'BUY':
                trade['entry_id'] = leg['id']
        self.store.save(trade, 'BROKER_SNAPSHOT')

    def _ownership(self, book, positions):
        trades = self.store.all()
        known = {leg.get('id') for t in trades for leg in ([t['entry']] if t.get('entry') else []) + t['sells']}
        tags = {leg['tag'] for t in trades for leg in ([t['entry']] if t.get('entry') else []) + t['sells']}
        for order in book:
            if order.get('exchange') == 'NFO' and (order.get('status') not in TERMINAL or int(order.get('filled_quantity', 0))):
                if order.get('order_id') not in known and order.get('tag') not in tags:
                    raise LiveHalt('Foreign NFO order; exclusive NFO account activity required')
        expected = {}
        for t in trades:
            remaining = t.get('entry', {}).get('filled', 0) - sum(s.get('filled', 0) for s in t['sells'])
            if remaining < 0:
                raise LiveHalt('Unexpected short exposure; manual intervention required')
            if remaining:
                expected[t['symbol']] = expected.get(t['symbol'], 0) + remaining
        actual = {}
        for p in positions:
            if p.get('exchange') == 'NFO' and int(p.get('quantity', 0)):
                if p.get('product') != 'NRML':
                    raise LiveHalt('Foreign NFO position product')
                actual[p['tradingsymbol']] = actual.get(p['tradingsymbol'], 0) + int(p['quantity'])
        if actual != expected:
            raise LiveHalt('Position/order snapshots disagree; reconcile before writes')

    def accept(self, payload, now, clock=None, before_submit=None):
        now = now.astimezone(IST)
        decision_id = payload.get('decision_id')
        if not isinstance(decision_id, str) or not decision_id or len(decision_id) > 100:
            raise LiveHalt('Invalid decision ID')
        if self.store.get(decision_id):
            return False
        if self.store.active() or any(t.get('halted') for t in self.store.all()):
            raise LiveHalt('Live state busy or halted; no new entry')
        bounds = TradingCalendar().session_bounds(now.date())
        if not bounds or not time(9, 45) <= now.time() < min(time(15, 15), bounds[1]):
            raise LiveHalt('Live entry session closed')
        stamp = datetime.fromisoformat(payload['decided_at'])
        if not stamp.tzinfo or not 0 <= (now-stamp).total_seconds() <= 90:
            raise LiveHalt('Decision stale or future-dated')
        if payload.get('context_ts'):
            context = datetime.fromisoformat(payload['context_ts'])
            if not context.tzinfo or not 0 <= (now-context).total_seconds() <= 90:
                raise LiveHalt('Agent market context is stale')
        if payload.get('action') not in ('LONG_CALL', 'LONG_PUT'):
            raise LiveHalt('Live execution accepts long option decisions only')
        entry, stop, target = (positive(payload[k]) for k in ('entry_price', 'stop_price', 'target_price'))
        if not 0 < self.config.stop_limit_buffer < stop < entry < target or not all(grid(v) for v in (entry, stop, target)):
            raise LiveHalt('Invalid tick grid or long option levels')
        expiry = date.fromisoformat(payload['expiry_date'])
        if expiry < now.date():
            raise LiveHalt('Expired contract')
        self._account()
        book = self.broker.orders()
        self._ownership(book, self.broker.positions())
        instrument = find_option(self.broker.nifty_options(), expiry, positive(payload['strike']),
                                 'CE' if payload['action'] == 'LONG_CALL' else 'PE')
        if not instrument or instrument.lot_size != payload.get('lot_size') or instrument.lot_size <= 0:
            raise LiveHalt('Contract/lot metadata mismatch')
        lots = payload.get('proposed_lots', 1)
        if type(lots) is not int or not 1 <= lots <= self.config.max_lots:
            raise LiveHalt('Agent quantity exceeds configured lot ceiling')
        quantity = instrument.lot_size * lots
        budget = self.config.risk_per_trade_inr
        vix = payload.get('india_vix')
        if vix is None or not math.isfinite(float(vix)) or float(vix) <= 0 or float(vix) > 16:
            budget /= 2
        stop_limit = floor_tick(stop-self.config.stop_limit_buffer)
        estimated_fees = positive(self.broker.round_trip_charges(instrument.tradingsymbol, quantity, entry, stop_limit))
        fees = max(self.config.fee_reserve_inr, estimated_fees)
        if (entry-stop_limit)*quantity + fees > budget:
            raise LiveHalt('One lot exceeds live risk budget including stop buffer and fees')
        day_trades = [t for t in self.store.all() if t['created_at'][:10] == now.date().isoformat() and t.get('entry', {}).get('filled')]
        if any(t.get('net_pnl') is None for t in day_trades):
            raise LiveHalt('Live daily P&L incomplete')
        daily = sum(t['net_pnl'] for t in day_trades)
        if daily - budget <= -self.config.daily_loss_limit_inr:
            raise LiveHalt('Live daily loss budget exhausted')
        required = positive(self.broker.order_margin(instrument.tradingsymbol, quantity, entry))
        cash = positive(self.broker.cash_available())
        capital = self.capital_status(cash=cash)
        if max(required, entry*quantity) + fees > capital['available_for_new_trade_inr']:
            raise LiveHalt('Insufficient live cash or bot allocation')
        if before_submit is not None:
            before_submit()
        final_now = clock().astimezone(IST) if clock else now
        final_bounds = TradingCalendar().session_bounds(final_now.date())
        if (not final_bounds or final_now.date() != now.date() or
                not time(9, 45) <= final_now.time() < min(time(15, 15), final_bounds[1]) or
                not 0 <= (final_now-stamp).total_seconds() <= 90):
            raise LiveHalt('Entry session/decision expired during preflight')
        if payload.get('context_ts') and (final_now-datetime.fromisoformat(payload['context_ts'])).total_seconds() > 90:
            raise LiveHalt('Agent context expired during preflight')
        now = final_now
        trade = dict(decision_id=decision_id, created_at=now.isoformat(), payload=payload,
            status='ENTRY_PENDING', symbol=instrument.tradingsymbol, quantity=quantity,
            stop=stop, stop_limit=stop_limit, target=target, tick=.05, entry_id=None,
            sells=[], halted=False, exit_reason=None, pending=None, net_pnl=None)
        self._place(trade, 'BUY', quantity, entry, 'LIMIT', now, validity='IOC')
        return True

    def _tag(self, trade, role):
        return 'tb2' + hashlib.sha256((trade['decision_id']+role).encode()).hexdigest()[:17]

    def _place(self, trade, side, quantity, price, order_type, now, validity='DAY'):
        if side == 'SELL' and len(trade['sells']) >= 3:
            trade['halted'] = True
            trade['exit_reason'] = 'EXIT_ATTEMPTS_EXHAUSTED'
            self.store.save(trade, 'MANUAL_EXIT_REQUIRED')
            raise LiveHalt('Exit attempts exhausted; inspect Kite and close remaining exposure manually')
        role = 'entry' if side == 'BUY' else 'sell'+str(len(trade['sells']))
        params = dict(tradingsymbol=trade['symbol'], transaction_type=side, quantity=quantity,
                      price=price, order_type=order_type, validity=validity, tag=self._tag(trade, role))
        if order_type == 'SL':
            params['trigger_price'] = trade['stop']
        leg = dict(tag=params['tag'], side=side, filled=0, id=None)
        if side == 'BUY':
            trade['entry'] = leg
        else:
            trade['sells'].append(leg)
        trade['pending'] = dict(kind='place', tag=leg['tag'], params=params, since=now.isoformat())
        self.store.save(trade, 'PLACE_INTENT')
        try:
            leg['id'] = self.broker.place_order(params)
            if side == 'BUY': trade['entry_id'] = leg['id']
        except AmbiguousOrderError:
            trade['halted'] = True
        except KiteError:
            leg['snapshot'] = dict(status='REJECTED', filled_quantity=0, quantity=quantity)
            trade['pending'] = None
            trade['halted'] = True
            trade['exit_reason'] = 'PROTECTION_FAILED' if side == 'SELL' else 'ENTRY_REJECTED'
            if side == 'BUY': trade['status'] = 'REJECTED'
        self.store.save(trade, 'PLACE_RESPONSE')

    def _write(self, trade, leg, kind, params, now):
        trade['pending'] = dict(kind=kind, tag=leg['tag'], params=params, since=now.isoformat())
        self.store.save(trade, kind.upper()+'_INTENT')
        try:
            if kind == 'cancel': self.broker.cancel_order(leg['id'])
            else: self.broker.modify_order(leg['id'], **params)
        except KiteError:
            # Modifications/cancellations may be accepted despite a timeout.
            # Keep intent until a subsequent broker snapshot resolves it.
            trade['halted'] = True
        self.store.save(trade, kind.upper()+'_RESPONSE')

    def _cancel_entry_during_uncertain_sell(self, trade, now):
        entry = trade['entry']
        if not entry.get('id') or entry.get('snapshot', {}).get('status') not in WORKING:
            return
        previous = trade.get('auxiliary_cancel')
        if previous and (now-datetime.fromisoformat(previous['since'])).total_seconds() < 5:
            return
        trade['auxiliary_cancel'] = dict(order_id=entry['id'], since=now.isoformat())
        self.store.save(trade, 'CANCEL_BUY_DURING_UNCERTAIN_SELL_INTENT')
        try:
            self.broker.cancel_order(entry['id'])
        except KiteError:
            trade['halted'] = True
        self.store.save(trade, 'CANCEL_BUY_DURING_UNCERTAIN_SELL_RESPONSE')

    def _resolve(self, trade, now):
        pending = trade.get('pending')
        if not pending: return True
        legs = [trade['entry']] + trade['sells']
        leg = next(s for s in legs if s['tag'] == pending['tag'])
        order = leg.get('snapshot')
        if leg['side'] == 'SELL' and trade['entry'].get('filled', 0):
            self._cancel_entry_during_uncertain_sell(trade, now)
        confirmed = bool(order and (order['status'] in TERMINAL or (
            order['status'] in WORKING and (
                (pending['kind'] == 'place' and (leg['side'] == 'BUY' or order.get('exchange_order_id'))) or (pending['kind'] == 'modify' and
                all(order.get(k) == v for k, v in pending['params'].items()))))))
        if pending['kind'] == 'cancel':
            confirmed = bool(order and order['status'] in TERMINAL)
        if confirmed:
            trade['pending'] = None
            self.store.save(trade, 'WRITE_CONFIRMED')
            return True
        if (now-datetime.fromisoformat(pending['since'])).total_seconds() > 30:
            trade['halted'] = True
            self.store.save(trade, 'WRITE_UNRESOLVED')
            # Safe cancellation of the buy reduces further exposure even when
            # the existence of a protective sell remains uncertain.
            entry = trade['entry']
            if entry.get('id') and entry.get('snapshot', {}).get('status') in WORKING:
                self.store.save(trade, 'EMERGENCY_CANCEL_ENTRY_INTENT')
                try: self.broker.cancel_order(entry['id'])
                except KiteError: pass
            raise LiveHalt('Order write unresolved; no resubmission; inspect Kite immediately')
        return False

    def _close(self, trade, now):
        entry = trade['entry']
        if not entry.get('filled'):
            trade['status'] = 'CANCELLED'
            self.store.save(trade, 'NO_FILL')
            return
        # Executed trade rows, not quote/limit or partial-order average prices.
        fills = self.broker.trades()
        legs = [entry] + trade['sells']
        charges_orders = []
        gross = 0
        for leg in legs:
            executed = [f for f in fills if str(f['order_id']) == leg.get('id')]
            quantity = sum(int(f['quantity']) for f in executed)
            if quantity != leg.get('filled', 0):
                raise LiveHalt('Trade ledger has not caught up; P&L remains incomplete')
            if not quantity: continue
            value = sum(positive(f['price'])*int(f['quantity']) for f in executed)
            gross += value * (1 if leg['side'] == 'SELL' else -1)
            charges_orders.append(dict(order_id=leg['id'], exchange='NFO', tradingsymbol=trade['symbol'],
                transaction_type=leg['side'], variety='regular', product='NRML', order_type='LIMIT',
                quantity=quantity, average_price=value/quantity))
        charges = self.broker.execution_charges(charges_orders)
        if not math.isfinite(charges) or charges < 0:
            raise LiveHalt('Executed charges unavailable')
        trade.update(status='CLOSED', closed_at=now.isoformat(), executed_legs=charges_orders,
                     gross_pnl=gross, charges=charges, net_pnl=gross-charges)
        self.store.save(trade, 'CLOSED')

    def step(self, now, bid=None, kill=False, quote_provider=None, clock=None):
        now = now.astimezone(IST)
        self._account()
        book = self.broker.orders()
        active = self.store.active()
        for trade in active:
            if trade['created_at'][:10] != now.date().isoformat():
                raise LiveHalt('Prior-day live state requires manual reconciliation; DAY protection expires')
            self._snapshot(trade, book)
        self._ownership(book, self.broker.positions())
        now = clock().astimezone(IST) if clock else now
        if quote_provider is not None:
            bid = quote_provider()
            now = clock().astimezone(IST) if clock else now
        for trade in active:
            if trade['created_at'][:10] != now.date().isoformat():
                raise LiveHalt('Session date changed during reconciliation')
            if not self._resolve(trade, now): continue
            entry = trade['entry']
            entry_order = entry.get('snapshot')
            if not entry_order: continue
            bought = entry['filled']
            sold = sum(s['filled'] for s in trade['sells'])
            exposure = bought-sold
            entry_terminal = entry_order['status'] in TERMINAL
            sell = trade['sells'][-1] if trade['sells'] else None
            sell_order = sell.get('snapshot') if sell else None
            sell_terminal = bool(sell_order and sell_order['status'] in TERMINAL)
            if exposure == 0:
                if not entry_terminal:
                    if sold or kill or now.time() >= time(15, 15) or (now-datetime.fromisoformat(trade['created_at'])).total_seconds() > 30:
                        self._write(trade, entry, 'cancel', {}, now)
                elif not sell or sell_terminal:
                    self._close(trade, now)
                elif sell_order and sell_order['status'] in WORKING:
                    self._write(trade, sell, 'cancel', {}, now)
                continue
            if sell and sell_terminal:
                trade['halted'] = True
                trade['exit_reason'] = 'PROTECTION_TERMINATED'
            bounds = TradingCalendar().session_bounds(now.date())
            flat_time = min(time(15, 20), (datetime.combine(now.date(), bounds[1])-timedelta(minutes=20)).time()) if bounds else time(0)
            if kill or now.time() >= flat_time:
                trade['exit_reason'] = 'KILL' if kill else 'SQUARE_OFF'
            if bid is not None and positive(bid) >= trade['target']:
                trade['exit_reason'] = trade['exit_reason'] or 'TARGET'
            if trade['halted']:
                trade['exit_reason'] = trade['exit_reason'] or 'HALTED'
            self.store.save(trade, 'EXPOSURE')
            # Protection first, including partially filled pending entries.
            if not sell or sell_terminal:
                if trade['exit_reason']:
                    if not entry_terminal:
                        self._write(trade, entry, 'cancel', {}, now)
                    elif bid is not None:
                        self._place(trade, 'SELL', exposure, max(.05, floor_tick(positive(bid)-self.config.stop_limit_buffer)), 'LIMIT', now)
                    else:
                        raise LiveHalt('Unprotected exposure; fresh bid required for emergency exit')
                else:
                    self._place(trade, 'SELL', exposure, trade['stop_limit'], 'SL', now)
                continue
            if not sell_order or sell_order['status'] not in WORKING:
                continue  # Submitted/pending is never labelled protected.
            prior_sold = sold-sell['filled']
            required_total = bought-prior_sold
            if int(sell_order['quantity']) != required_total:
                params = dict(quantity=required_total, price=float(sell_order['price']),
                              order_type=sell_order['order_type'], validity='DAY')
                if params['order_type'] == 'SL': params['trigger_price'] = trade['stop']
                self._write(trade, sell, 'modify', params, now)
                continue
            if not sell_order.get('exchange_order_id'):
                trade['status'] = 'PROTECTION_PENDING'
                trade['halted'] = True
                self.store.save(trade, 'PROTECTION_UNCONFIRMED')
                self._cancel_entry_during_uncertain_sell(trade, now)
                raise LiveHalt('Protective sell not exchange-confirmed; inspect Kite')
            if not entry_terminal:
                self._write(trade, entry, 'cancel', {}, now)
                continue
            if trade['exit_reason'] or (sell_order['order_type'] == 'SL' and sell_order['status'] == 'OPEN'):
                # SL OPEN means triggered, potentially stranded below its limit.
                trade['exit_reason'] = trade['exit_reason'] or 'STOP_TRIGGERED'
                if bid is not None:
                    price = max(.05, floor_tick(positive(bid)-self.config.stop_limit_buffer))
                    if sell_order['order_type'] != 'LIMIT' or float(sell_order['price']) > price:
                        self._write(trade, sell, 'modify', dict(quantity=required_total, price=price,
                            order_type='LIMIT', trigger_price=0, validity='DAY'), now)
                else:
                    self.store.save(trade, 'EXIT_WAITING_FRESH_QUOTE')
                    raise LiveHalt('Exit requires a fresh quote; broker limit may remain unfilled')
            else:
                trade['status'] = 'PROTECTED' if sell_order.get('exchange_order_id') and sell_order['status']=='TRIGGER PENDING' else 'PROTECTION_PENDING'
                self.store.save(trade, 'PROTECTION_CHECK')
