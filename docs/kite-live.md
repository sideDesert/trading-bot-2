# Automated Kite pilot

Implementation is available for offline review. It has not placed any real orders,
been deployed, or demonstrated profitability. The existing paper engine remains
unchanged and is still the default. Kite is the only execution broker.

## What runs automatically

`trading_bot.autopilot` fetches the existing `agent_brain` analytics and raw Upstox
context every configured decision interval when flat. A signed-in local Codex CLI
chooses CALL/PUT/NO_TRADE, contract, prices and proposed lots. This is the independent
agent strategy, not the sibling deterministic ORB advisory candidate. Python then
records and validates the proposal and, in explicitly armed live mode, sends it to
Kite without per-trade human confirmation. No fresh model call is made while a live
trade or uncertain order is outstanding. The execution loop runs every second while
collection/model evaluation runs in a worker; model latency cannot suspend stops.

The adapter uses `codex exec --output-schema --output-last-message` with saved CLI
authentication, no separate LLM API key. It ignores user CLI config, disables shell,
unified exec, apps, MCP configuration and web search, and uses a temporary working
directory. Broker environment variables and repository `.env` are not sent to the
child or model. Its prompt asks the agent to select only supplied contracts. These
flags were checked against installed CLI help and official documentation; the real
model invocation has only been tested with a mocked subprocess, not an authenticated
end-to-end production call. Authentication, provider rate limits and model availability
are activation checks. The CLI default model is used unless `--model` is supplied.

Paper rehearsal (does make Upstox/model requests, but cannot send broker orders):

```bash
.venv/bin/python -m trading_bot.autopilot
```

Paper sizing retains the existing paper engine rules. Proposed live lots do not
change paper sizing or the separate advisory strategy.

For decisions visible in one interactive Codex conversation, add
`--decision-source terminal` and use the repository's `$nifty-agent-advice` skill.
This replaces the nested noninteractive model invocation only; execution,
freshness, pause invalidation and risk checks stay in the Python runner. See
`terminal-pilot.md` for the three-terminal startup and goal instructions.

## Inputs required before activation

Copy `config/live.example.json` to gitignored `config/live.json`. Fill in:

- `account_id`: the exact Kite account ID.
- `risk_per_trade_inr`: a separately chosen maximum planned trade loss; no paper default is copied. The approved local pilot uses ₹10,000.
- `daily_loss_limit_inr`: a separately chosen daily net loss budget. The approved local pilot uses ₹10,000.
- `pilot_start` and `pilot_end`: explicit ISO dates, end within 14 days of start.
- `max_lots`: independent lot ceiling (example is one). The agent may propose up to this ceiling.
- Review `stop_limit_buffer`, `fee_reserve_inr` (minimum ₹200), cadence and model timeout.

`capital_limit_inr: 10000` means **total starting allocation**, not per-trade risk.
Missing/null settings refuse activation. The initial version also refuses planned
risk above ₹10,000/trade or daily loss above ₹10,000. These are upper implementation
ceilings, not approved operating limits. Risk includes the sell-limit buffer and the
larger of the fee reserve and Kite's round-trip charge estimate; high/unknown VIX
halves the risk budget. If even one current lot cannot fit, the trade is skipped.

Python verifies the contract in both Upstox and Kite, dynamic lot size, tick-valid
levels, supported session, context age ≤90 seconds, selected quote age ≤15 seconds,
spread ≤2%, available cash, Kite required margin, capital, lot count and loss budget.
Only one pending/open trade is permitted. No manual/other NFO activity may share the
account during this pilot: foreign NFO positions, open orders or fills halt new
writes. A valid matching-account profile is required before every reconciliation
and entry; expired/missing credentials never enable new entries.

Allocation = persisted starting ₹10,000 + completed bot trades' realized **net** P&L.
Profits may fund subsequent trades; losses reduce allocation. Unrealized gains,
unrelated deposits, account P&L and other traders' profits never increase it. The
available new-trade budget is bounded by verified broker cash and outstanding
commitments. Completed fills/charges/net P&L are immutable and restored on restart;
missing/inconsistent costs block reuse. The scheduler sends current allocation and
available capital to the agent. Profit reuse never raises trade-risk, daily-loss or
lot ceilings. Changing the starting allocation on an existing journal is refused.

Closed P&L uses Kite `/trades` executed quantities/prices and `/charges/orders` for
those actual executed legs, including replacement sell legs. The latter is a broker
charge calculation, not contract-note reconciliation; settlement adjustments are not
automatically imported. A missing trade/charge response leaves the trade incomplete
and blocks new entries rather than crediting estimated profit.

Offline configuration check (no account requests):

```bash
.venv/bin/python -m trading_bot.live validate-config --config config/live.json
```

Activation commands below are documentation only. They have **not** been run:

```bash
# After configuration, daily dashboard login, fixed IP and explicit pilot activation:
.venv/bin/python -m trading_bot.autopilot --mode live --enable-live --config config/live.json --decision-source terminal
```

The existing login helper writes `KITE_ACCESS_TOKEN` into `.env` with restricted
permissions. Supply `UPSTOX_ACCESS_TOKEN`, `KITE_API_KEY`, `KITE_API_SECRET` for login,
and the resulting `KITE_ACCESS_TOKEN` securely. Do not place secrets in the JSON
config. Dashboard login updates the shared token, which the runner reloads each tick.
The CLI helper updates only `.env`; an expired shared token still blocks that
fallback, so use dashboard login for this local pilot. Password/TOTP entry stays
on Zerodha. Private credentials are local and never checked into Git.

The standalone executor can also consume explicit `agent_brain record
--execution-mode live --proposed-lots N` decisions in `data/live/inbox`; it is not
necessary for autopilot users. `trading_bot.live run --enable-live --config ...`
manages that inbox without scheduling a model. Both runners share an exclusive
`data/live/runner.lock`, so they cannot control one journal concurrently.

## Order lifecycle and recovery

- Entry: regular NFO/NRML IOC LIMIT buy. Unfilled remainder expires at the broker;
  any observed partial fill is protected. A buy stuck OPEN beyond 30 seconds is
  cancelled. No assumed quote fill is recorded as a real fill.
- Protection: one regular DAY SL **sell limit** for broker-confirmed bought units.
  A submitted order is not labelled protected until the broker reports an exchange
  ID and TRIGGER PENDING. Further entry fills resize the same sell; the remaining
  buy is cancelled once protection is observed. Submission/confirmation still
  leaves a short exposure window; Kite has no atomic entry+stop here.
- Target, 15:20 flat time, pilot expiry, or STOP file: convert that same sell order
  into a marketable LIMIT. A triggered SL stranded below its limit is converted
  similarly. There is no simultaneous target sell that can race the stop into an
  accidental short. Modification rejection leaves the existing order in place.
- If a sell becomes terminal with units remaining, cancel/confirm the buy first,
  then place a replacement for exactly the confirmed remaining units. At most
  three sell placements are attempted; repeated rejections require manual action.
- Writes have FULL-synchronous SQLite intents committed before transmission.
  Deterministic ≤20-character tags recover accepted placements after a crash or
  timeout. Tags are **not** broker idempotency keys. An unresolved/absent placement
  is never resubmitted. It halts entries and requires inspection; a known pending
  buy is safely cancelled to bound additional exposure.
- Broker positions and order fills must agree before writes. A transient mismatch
  is retried on a later reconciliation cycle. Unexpected shorts, unknown orders,
  missing IDs, duplicate tags, account change or prior-day active state require
  manual inspection. The broker's order book lasts only one day; do not delete the
  journal to bypass a halt. A recovered ambiguous write keeps an entry halt and
  exits known exposure where safe, instead of silently restarting new trading.

Request a controlled stop with `touch data/live/STOP`. This blocks new decisions
and attempts to exit through the single existing sell. It is **not proof of a
completed exit**. Keep the service running until Kite confirms zero position and
no active sell. `python -m trading_bot.live status` reads local state without an
account call. Inspect Kite directly on any `ATTENTION` message. Do not remove a STOP
file, edit the journal or clear a sticky halt until the cause and all positions/
orders are reconciled. This version deliberately has no automatic force-reset.

## Hosting requirements and limits

No cloud provider, deployment or scheduled service has been provisioned. A future
host needs Python, pinned `requirements.txt`, Codex CLI with valid saved sign-in,
Upstox read token, daily Kite token, durable encrypted storage and a **fixed outbound
IP registered in the Kite developer console**. Read endpoints working from a host
do not prove that its order traffic is whitelisted. Match the actual IPv4/IPv6
source; a rotating/shared egress address is unsuitable. Only one service instance
may use the live journal. Persist `data/live/` across restarts and deployments.

A market-day service may start around 09:00 IST (09:45 earliest new entry) and stop
**after** the 15:20 exit has been confirmed. The existing calendar fails closed on
unsupported years and closed days; special short sessions flatten 20 minutes before
close. Do not blindly power off at 15:20: an unfilled exit can leave a position.
The private browser login/dashboard is described in `kite-dashboard.md`; it writes
a shared private token file which a running service reloads each tick. Connecting
the dashboard does not arm the runner. `PAUSE` stops only new trades and leaves
existing exits running, unlike `STOP`.
Daily token refresh and attention handling still require an operator. Fresh login
is needed each morning: Kite documents token expiry at 06:00 the next day, and a
master logout can invalidate it earlier. No overnight-refresh workaround is used.

NRML positions are not assumed to be automatically flattened by broker RMS. Stops
are DAY orders and expire; outages, revoked auth, exchange rejection/circuit limits
and price gaps can leave exposure. An SL trigger/limit or planned loss budget does
not guarantee execution or a maximum realized loss. Targets and flat time still
require the runner; broker-held stop triggering works independently once accepted.
This is a concrete implementation for review, not a claim of unattended safety or
strategy profitability.

Official sources checked 03-Oct-2026:

- [Kite order APIs/statuses and transient daily book](https://kite.trade/docs/connect/v3/orders/)
- [Index-option SL-M restriction](https://zerodha.com/marketintel/bulletin/307362/stop-loss-market-sl-m-orders-blocked-for-index-options)
- [Kite authentication expiry and funds fields](https://kite.trade/docs/connect/v3/user/)
- [Zerodha fixed-IP requirement](https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/static-ip)
- [Codex structured noninteractive execution](https://learn.chatgpt.com/docs/non-interactive-mode)
- [Codex tool/config settings](https://learn.chatgpt.com/docs/config-file/config-reference)

## Offline verification

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q trading_bot tests
```

New tests use mocked broker methods/transports, mocked Codex subprocesses and
local temporary databases. They never place broker test orders. The existing OAuth
callback test uses a localhost HTTP server and can require a less restrictive test
sandbox. Authenticated model/Kite interaction, cloud hosting, account-specific
order acceptance, finalized charges and continuous production monitoring remain
unverified.
