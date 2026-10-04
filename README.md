# Trading Bot 2 — local live pilot

The current pilot uses **Upstox for market data, Kite/Zerodha for actual orders,
and your existing agent-driven skill in an interactive Codex conversation for
decisions**. Python continuously manages execution, protection and exits.
The separate deterministic advisory/paper workflows remain available; their
shadow-only labels do not describe this explicitly armed live pilot.

Approved settings for **Monday, 5 October 2026**:

| Setting | Value |
|---|---|
| Starting bot allocation | ₹10,000 |
| Maximum planned loss per trade | ₹10,000 |
| Maximum daily net loss | ₹10,000 |
| Maximum lots | 1 |
| Decision cadence while flat and eligible | 10 minutes |
| New-entry window | 09:45–15:15 IST |
| Planned exit time | 15:20 IST; keep reconciling until resolved |

These are configured limits, not a guaranteed absolute loss ceiling. The existing
VIX rule halves allowed per-trade risk when VIX is high or unknown. Costs, capital,
lot size, spreads, account ownership and freshness are still checked; NO_TRADE is
valid. Remaining daily loss is checked against the proposed trade's planned loss,
not the whole unused per-trade allowance.

## Exact morning instructions

Follow [the local startup guide](docs/terminal-pilot.md): dashboard command, daily
Kite login clicks, Upstox health check, paused execution runner, the exact Codex
loop prompt, Resume, and confirmed shutdown. No live runner has been started by
the implementation work.

The adapted skill is [nifty-agent-advice](.agents/skills/nifty-agent-advice/SKILL.md),
also available at the existing Claude skill path. It displays each proposal and
rationale, then hands it to the runner. It does not directly call Kite order APIs.
The dashboard displays Zerodha's live cash separately from the bot allocation.

## Required network setup

Kite requires a registered **fixed public outbound IP** for API order requests.
This is the address Zerodha sees for your laptop's internet traffic, not
`127.0.0.1` or a router/private address. Obtain a fixed IP from your ISP or a
dedicated fixed-egress provider, then register it in the Kite Connect developer
account under **Profile → IP Whitelist**. A successful login/data read does not
verify permission to place orders. Do not switch networks or disable the chosen
fixed-egress connection mid-session. We have not verified your whitelist.
[Zerodha's instructions](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/static-ip).

## Checks and older workflows

GitHub Actions runs offline Python/JavaScript tests and compilation on pushes and
pull requests. Mocked passing tests are not proof of market performance or live
execution. See `docs/kite-live.md` for order lifecycle and recovery, and
`docs/kite-dashboard.md` for authentication and controls. The original
`nifty-advice` and paper-result tools remain separate legacy workflows.
