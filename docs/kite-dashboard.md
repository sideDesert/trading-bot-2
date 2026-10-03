# Private Kite dashboard

A small mobile browser page, with no frontend dependencies. It shows daily Kite
connection, usable bot capital, open NFO positions, working NFO orders, and completed
bot net P&L. The page polls persisted state every five seconds. Broker reads refresh
in the background at most every 15 seconds; data older than 30 seconds is labelled
stale and available capital becomes unknown. Cash freshness starts before broker
reads and is bound to the exact daily login, so a slow refresh or new login cannot
reuse a previous session's funds.

The dashboard has no broker order-writing routes. Connecting Kite does not start
or arm the live runner. No service or cloud provider is deployed by this feature.

## Local preview

```bash
.venv/bin/python -m trading_bot.live_web --demo --port 8080
```

Open `http://127.0.0.1:8080`. Preview data is illustrative, controls are disabled,
and no account or model calls occur. The preview does not create a live journal.

## Private service configuration

Use the same persistent `--root` as the live runner (default `data/live`) and a
private server configuration copied from `config/live.example.json`. Set the actual
Kite account ID and retain the ₹10,000 starting allocation. Live activation still
requires the separate loss limits and pilot dates described in `kite-live.md`.
The dashboard can run before those activation inputs are complete.

Provide these variables through private server environment/secret management:

```text
DASHBOARD_PUBLIC_URL=https://your-private-domain.example
DASHBOARD_PASSWORD=<unique private password of at least 16 characters>
KITE_API_KEY=<your existing Kite application key>
KITE_API_SECRET=<your existing Kite application secret>
```

A gitignored `.env` is supported via `--env-file`; restrict its permissions and
never paste credentials into chat, source code or browser-side configuration.

```bash
.venv/bin/python -m trading_bot.live_web --config config/live.json --port 8080
```

The service binds only to loopback. Place it behind a trusted HTTPS reverse proxy
on the same host. Preserve the original `Host` and browser `Origin`; the configured
origin is checked exactly. `Referrer-Policy: strict-origin` excludes callback
paths/query tokens while preserving the Origin header on browser form posts;
`no-referrer` would turn those origins into `null` and block sign-in.
Configure request-size/time limits and redact callback
query strings from proxy/access/error logs. The Python handler disables request
logging because callback queries carry short-lived credentials. Firewall direct
backend access. Persist the live root on private encrypted storage and run the web
service and runner as the same restricted operating-system user. One web service
instance is supported; dashboard sessions and callback states are in memory.

Register this **exact HTTPS redirect URL** on the existing Kite developer app:

```text
https://your-private-domain.example/kite/callback
```

Sign in to the private dashboard, then press **Connect Kite**. Login happens on
Zerodha. Kite returns to the registered callback; the server exchanges the
short-lived request token and verifies the configured account before saving the
daily access token. Callback state is random, bound to the original dashboard
session, expires after ten minutes, and can be used once. Browser policy permits
form redirects only to this dashboard and the official Kite login origin. Server
restart or dashboard-session expiry requires starting the login flow again.

The atomic `data/live/kite-session.json` file has mode `0600`. Access tokens and API
secrets never enter the dashboard JSON, HTML or logs. An already running live
runner reads the shared token on each tick, so daily web login needs no runner
restart. When this file exists but is expired or malformed, the runner fails closed
instead of falling back to an older environment token. A missing shared file still
allows the existing environment-token workflow. Daily expiry is handled
conservatively at the next 06:00 IST; earlier broker invalidation also requires a
fresh login. Official handshake and expiry: [Kite authentication](https://kite.trade/docs/connect/v3/user/).

Fixed registered outbound IP requirements still apply to the **execution service**;
a successful dashboard login or broker read does not prove order IP registration.

## Capital and controls

Bot allocation = starting allocation + immutable completed bot net P&L. Profits
can fund later trades and losses reduce the allocation. Open gains and deposits
do not increase it. Available capital is the lower of verified broker cash and
allocation after pending buys, open exposure and fee reserves. Missing broker cash
or incomplete realized costs is shown as unknown, never a made-up zero. Separate
entry, loss, lot and session checks remain enforced by the runner. A displayed
budget does not bypass those checks.

**Stop new trades** writes `data/live/PAUSE`. It prevents fresh model cycles and
entry submission. Existing broker-held stops and runner-managed exits continue.
It does not liquidate positions. The button changes to **Resume new trades**;
resuming removes only `PAUSE`. It does not start the runner, clear `STOP`, clear
an execution halt, bypass entry checks or place an order. Resume is refused while
a stop request or any persisted execution halt exists. Both controls require
the authenticated dashboard session, exact Origin and CSRF token. Each control
transition invalidates older unfinished agent calls and queued entries. A quick
pause/resume cannot reuse a pre-pause decision. Late page polls cannot overwrite
an acknowledged control change.
The existing `STOP` control is different: it requests safe exits and stops entries.

Runner heartbeat older than 30 seconds is shown as not running. Broker rows may
remain visible after connection failure; their refresh timestamp and stale/login
status identify them as historical. Always resolve execution attention in Kite
and the durable journal before resuming. Stop limits can remain unfilled after a
gap; completing login or pausing entries does not guarantee protection.

## Future server schedule

No server schedule is installed yet. After a host/provider is authorized, run one
supervised controller, start around 09:00 IST on weekdays, and retain the existing
holiday/special-session checks. A service manager should restart a crashed runner
and alert the operator; a persistent terminal can expose its logs and controls.
Use a timer/cron only for startup, never an unconditional 15:20 process kill.
The controller targets exits at 15:20 on ordinary sessions and should continue
reconciling until bot positions and working bot orders are confirmed resolved.
It must report an outstanding exit rather than assume a scheduled stop flattened
the account. Daily login and configured pilot/risk limits remain activation gates.

The conversational agent is still ephemeral in the current implementation. Saved
conversation/resume and interactive SSH takeover require a separate controller
change with exclusive ownership of that conversation; they are not enabled by
the dashboard Resume button. This feature resumes entry permission only.
