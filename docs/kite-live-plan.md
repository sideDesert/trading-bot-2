# Kite live implementation plan

Authorized scope: implementation and offline tests only. No broker execution.

1. Add a separate, explicitly enabled Kite execution client. Preserve the calculation client's allowlist. Test URL/form encoding, mutation errors, credential redaction, and endpoint refusal.
2. Add a SQLite FULL-synchronous intent journal and exclusive runner lock. Persist intent before each write; recover placements by deterministic tags, never retry uncertain placements. Pin account identity.
3. Consume explicit live agent decisions without changing the strategy. Validate current contract, session, fresh decision/quote, tick grid, one-lot sizing, live cash/margin, capital, fees and daily loss.
4. Use IOC limit buys, protect every confirmed partial fill with a DAY SL sell, resize only the single sell order; convert that same order to a marketable LIMIT for target/flat/kill exits. Never submit a replacement before the old sell is terminal. Unknown/rejected protection halts entries and triggers cancellation/controlled exit where broker state permits.
5. Test timeout recovery, rejection, partial fills, resize, target/stop races, restart, duplicate decisions, stale quotes, funds, foreign account activity and overnight state. Run full offline suite and compile checks.
6. Document explicit activation and manual recovery. Record limitations: no atomic buy+SL, stop-limit gap risk, DAY expiry, no OCO, no guaranteed exit, and no demonstrated profitability.

## Completion evidence

All six steps completed. Extended scope includes scheduled Codex CLI decisions,
agent-proposed lots, total starting capital, realized net-profit reuse and frozen
decision context. Independent review found three P1 lifecycle issues; each was
reproduced by a failing test, repaired and re-reviewed with no remaining important
findings. Final offline suite: 426 tests passed. Compilation, whitespace checks,
CLI help, safe status and refused-unarmed activation checks passed. No real model
call, broker request/order, credentials installation or cloud deployment occurred.
