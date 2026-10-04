# Local pilot with an interactive Codex terminal

Two processes share the existing runner: Python continuously manages execution;
an interactive Codex conversation uses `$nifty-agent-advice` for decisions.
The runner supplies fresh market facts, capital limits and recent decisions. The
terminal displays each proposal and rationale in the same conversation. No nested
`codex exec` model call is made in terminal mode. The old `exec` mode remains the
default for compatibility.

## Before starting

Private `config/live.json` is configured for 5 October 2026: ₹10,000 starting
allocation, ₹10,000 planned risk per trade, ₹10,000 daily loss, one lot and a
600-second decision interval. The terminal-mode live runner always starts with
entries paused. No live runner or real order has been started during setup.
Three processes stay open: dashboard, execution runner, and Codex.
Before live startup, verify the fixed outbound IP registration described in README.md.

## Terminal 1: dashboard and daily Kite login

Open a terminal and run:

```bash
cd /Users/siddarth/.codex/worktrees/e673/trading-bot-2
caffeinate -i -s env SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python -m trading_bot.live_web \
  --local --config config/live.json --port 8080
```

Keep this terminal running, the laptop plugged in, and its lid open. `caffeinate`
prevents idle sleep while the dashboard process runs; closing the lid can still
sleep the laptop. If the dashboard is already listening on 8080, use that running
instance rather than starting a second one. Do not use the old temporary launcher.

1. Open http://127.0.0.1:8080/ in your browser. Use HTTP, not HTTPS.
2. Enter `DASHBOARD_PASSWORD`, the private password you set in `.env`, and click
   **Open dashboard**. This is the dashboard password, not your Zerodha password.
3. Click **Connect Kite**. Complete Zerodha's normal login and second factor on
   its website. It returns to the local page. Keep that browser session open.
4. Wait for **Kite connected** and verified Zerodha cash. Missing or expired
   tokens are shown as unavailable; yesterday's connection does not count.
5. Inspect Kite directly for unexpected NFO orders or positions. Do not share
   this pilot account with another manual/automated NFO strategy during the run.

The existing developer app redirect is `http://127.0.0.1:8080/`; local mode routes
that callback through the same session/state checks. `DASHBOARD_PUBLIC_URL` is not
needed in local mode. The server opens even when yesterday's Kite token is expired.
A fresh login writes the private shared token file used by the runner.

## Before live startup: offline config and read-only data checks

In another terminal, start in the same checkout:

```bash
cd /Users/siddarth/.codex/worktrees/e673/trading-bot-2
.venv/bin/python -m trading_bot.live validate-config --config config/live.json
SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python - <<'PYTHON'
from trading_bot.config import load_env_file
from trading_bot.upstox.client import UpstoxClient
load_env_file('.env', names=('UPSTOX_ACCESS_TOKEN',))
UpstoxClient.from_env().health()
print('Upstox data access OK')
PYTHON
```

Expected: **Live configuration valid** and **Upstox data access OK**. The checks
place no orders. If the Upstox check fails, refresh that data token through your
existing Upstox setup and update `.env`; Kite login does not refresh Upstox.
Do not continue with failed checks or an unverified fixed order IP.

## Terminal 2: execution

From the same checkout, after the activation checks are complete:

```bash
SSL_CERT_FILE=/etc/ssl/cert.pem .venv/bin/python -m trading_bot.autopilot \
  --mode live --enable-live --config config/live.json --decision-source terminal
```

This command can place real orders after entries are resumed and a valid proposal
is accepted. It is documented here; it has not been run during implementation.
It owns the exclusive live runner lock. Do not also launch `live run` or a second
autopilot. Existing positions/exits are checked every second while the decision
worker waits for Codex.

## Terminal 3: visible decisions

From the same repository root:

```bash
cd /Users/siddarth/.codex/worktrees/e673/trading-bot-2
codex
```

Enter this in Codex (goals are enabled on this machine):

```text
/goal Keep invoking $nifty-agent-advice for the live pilot until 15:15 IST on 5 October 2026. Handle each fresh request from the local runner, scheduled every ten minutes while flat and eligible. Show every decision, levels, lots, planned loss and reason in this conversation. Use the configured ₹10,000 starting capital, ₹10,000 per-trade planned-loss limit, ₹10,000 daily-loss limit and one-lot maximum. Submit each proposal once through the skill. Leave orders, stops and exits to the runner. Do not change limits, start or stop processes, or resume entries yourself.
```

Confirm the dashboard shows the runner as running and entries paused. Then use
**Resume new trades** on the dashboard when Codex is waiting for requests. This
is the step that allows new entries; daily Kite login alone does not arm them. The configured pilot
requests a decision every ten minutes while flat, within its entry window; it
does not request new decisions during an open trade or entry pause. Each response
has at most the configured 60-second timeout and still must pass existing context
freshness, pause revision, session, account, lot, capital and risk checks. Requests
and responses are private atomic files under `data/live/terminal`, outside Git.

Terminal proposals and journal entries are not broker fills. Use the dashboard
for broker-confirmed positions/orders and completed net P&L. Rejected or timed-out
requests cannot be replayed into a later cycle. If Codex closes, misses its goal
continuation or exceeds the deadline, new decisions stop for that cycle; execution
continues. Native goals are a conversational continuation mechanism, not a timing
guarantee. The Python runner owns the market schedule and timeouts.

## Pause, resume and finish

Pause new entries on the dashboard before interrupting or changing the decision
conversation. Existing exits remain active. `codex resume` reopens the saved
conversation; resume its goal and then resume entries when ready. The runner
passes fresh data each time; chat recollection is never proof of execution.

At 15:15 the decision goal ends. The runner targets exits at 15:20 and must stay
running until actual broker positions and bot orders are resolved. Do not close
Terminal 2 merely because the goal ended. For a controlled early stop, run `touch data/live/STOP` from the repository root.
This blocks entries and requests exits; it does not prove an exit completed.
Inspect Kite on execution attention. Closing a
terminal or sleep/power loss is not a confirmed liquidation.

## Validation

Offline bridge tests cover successful submission, private file permissions,
missing-terminal timeout, expired requests, stale market data and mismatched
response IDs. Existing execution and pause-revision tests still cover broker and
entry safety. Real Codex skill reasoning and live market execution require the
supervised pilot; this feature has not placed orders during development.
