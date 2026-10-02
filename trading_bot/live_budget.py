"""Shared realized allocation and commitment calculation; never credits open gains."""
import math
from .live_store import LiveHalt


def capital_from_trades(trades, starting, fee_reserve, broker_cash):
    if broker_cash is not None and (type(broker_cash) not in (int,float) or not math.isfinite(broker_cash)):
        raise LiveHalt('Broker cash unavailable')
    completed = [t for t in trades if t['status']=='CLOSED']
    for trade in completed:
        if any(type(trade.get(k)) not in (int,float) or not math.isfinite(trade[k]) for k in ('net_pnl','gross_pnl','charges')):
            raise LiveHalt('Completed costs unavailable')
        if trade['charges'] < 0 or abs(trade['net_pnl']-(trade['gross_pnl']-trade['charges'])) > .001:
            raise LiveHalt('Capital ledger inconsistent')
    realized = sum(t['net_pnl'] for t in completed)
    commitments = 0
    for trade in trades:
        if trade['status'] in ('CLOSED','CANCELLED','REJECTED'): continue
        entry = trade.get('entry', {})
        exposure = entry.get('filled',0)-sum(s.get('filled',0) for s in trade['sells'])
        pending = 0 if entry.get('snapshot',{}).get('status') in ('COMPLETE','CANCELLED','REJECTED') else trade['quantity']-entry.get('filled',0)
        commitments += max(0,exposure+pending)*trade['payload']['entry_price']+fee_reserve
    allocation = starting+realized
    available = None if broker_cash is None else max(0,min(allocation-commitments,broker_cash))
    return dict(starting_capital_inr=starting, allocation_inr=allocation, realized_net_pnl_inr=realized,
        committed_inr=commitments, broker_cash_inr=broker_cash, available_for_new_trade_inr=available)

