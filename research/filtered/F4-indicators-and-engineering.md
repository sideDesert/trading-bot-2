# F4: Indicators & engineering — filtered

Filter agent: F4. Inputs: R06 (technical-indicator efficacy, academic/practitioner evidence) + R12 (open-source NIFTY bots & Upstox engineering practice). Rule applied: keep decision-changing/corroborated claims; demote folklore; adjudicate R06-vs-R12 conflicts by layer (signal vs alert/context).

## Adjudication log

| Contested claim | R06 (academic) | R12 (community) | Verdict | Reason |
|---|---|---|---|---|
| Do indicators belong in the bot at all? | Graveyard for raw intraday TA rules (7,846 rules, none survive data-snooping correction; edges die at 10–20bp costs) | Community bots (option-chain analyzers, LLM analyst repos) prominently compute PCR, max pain, OI walls, IV skew, RSI | **Both right, different layers.** OI/PCR/RSI-class features live in the CONTEXT/alert layer fed to the LLM, never as deterministic entry triggers | R06 falsifies indicators *as signals net of costs*; R12 bots use them as *state descriptions*. No conflict once layers are separated |
| Supertrend (ubiquitous in Indian retail algos) | Grade D+: win rate flat 40–43% across all params; intraday whipsaw fatal; "a re-parameterized ATR trailing stop" | Practically every retail BankNifty bot runs supertrend flips | **Banned as signal.** ATR trailing stop allowed as an exit mechanic (not called a signal) | R06's 200k-trade study is far stronger evidence than repo popularity; exit-trailing is risk management, not edge |
| RSI on intraday | Grade D−: RSI(2) real 63% WR, PF 0.99 net — "win rate is real, profit is not" | RSI features appear in ML repos and analyst prompts | **Banned as entry; context-only extreme-reading tag permitted** | Use expectancy, not win rate; extreme RSI is a legitimate *regime descriptor* for the LLM |
| ORB | Best combined evidence B+ but ONLY with filters (vol-contraction, in-play days); naive = coin flip; headline Zarattini alpha failed independent replication | Few repos run ORB; Zerodha's own study (R12-adjacent, tier B) confirms 9:15–11:15 long-side edge, no costs | **Sole surviving signal family**, with mandatory filters + cost floor + decay monitoring | Academic and practitioner evidence converge that the *filter* is the edge; replication failure means allocate confidence, not certainty |
| ML/LLM prediction | 93.8% CNN-LSTM accuracy = leakage artifact (F); ML-as-filter C+ (cuts trades, raises Sharpe) | LLM repos all converge on "slow-layer analyst": scheduled debate/review, none document profitable per-tick LLM scalping | **No contradiction.** LLM = scheduled analyst/filter over aggregated state at 1-min+ cadence; banned from tick loop | Independent lineages reach the same architecture — strong corroboration |
| CVD/order-flow delta | Grade D without true aggressor flags; tick-rule CVD error ~169% of magnitude | Upstox v3 feed offers `full_d30` 30-level depth but no aggressor classification | **Banned.** Depth imbalance not used either (equity-centric docs, unvalidated for options) | Measurement error defeats signal; NSE feed cannot fix this |
| VWAP | VWAP-cross = net loser (honest negative result, tier B); band-reversion context B− (~68% revert >1σ) | Little direct VWAP use in repos; credible practitioner ML uses VWAP-breakout *filter* | **Context only** (bands, σ-distance, above/below regime). No crossover trigger | Both sources agree VWAP is reference/filter, not trigger |
| Option-chain polling cadence | Needs 5-min bars for mean-reversion stats (S19) | NSE scrapers poll 10s–5min; Dhan hard-limits 1 req/3s "because OI changes slowly"; Upstox splits chain=REST / prices=wss | **Websocket for subscribed keys + sparse REST chain (30–60s)** | R12's engineering argument (OI is slow) satisfies R06's data need (5-min bars) with 10–20× headroom |

## Indicator plan

| Indicator | Params (suggested) | Tier | Role | Notes |
|---|---|---|---|---|
| ORB with regime filters | 5/15/30-min opening range; eligible window 09:15–11:15; skip if OR range < 20th percentile of 20d ATR (contraction proxy NR4-analog); skip non-"in-play" days (low rel-volume, no news/expiry/event); NO tight stops (≥ OR-width or trail OR-extreme) | B+ | **signal** | Strongest combined evidence (R06 S6/S7/S10/S12/S14). Net edge is thin: enforce cost floor (gross edge ≥ 2–3× all-in round-trip incl. STT) and rolling-decay monitor (expect ~26% OOS decay) |
| First-30/60-min momentum | First-30-min spot return sign & magnitude → session-direction prior; feed to LLM snapshot as state field | A− | **context** | JFE-grade result but US-only; R06 open question — flag as "needs internal NIFTY replication" before any weight |
| Session-clock regime tags | Trend-bias windows 09:15–11:15 + final hour; mean-reversion bias 11:30–14:30 | A−/B | **context** | Synthesizes R06 S1/S12/S19/S24; deterministic clock tags, zero data cost |
| VWAP bands / regime | Session VWAP (09:15 anchor); distance in σ (rolling 20d intraday σ); tags: >+1σ, ±2σ, above/below | B− | **context** | Mean-reversion bias at band extremes on range days only; VWAP-cross trigger explicitly banned (net loser, R06 S18) |
| Relative-volume spike | Current 5-min volume / same-time 20d median; flag ≥1.5× | B− | **context** (breakout confirmation filter) | Cheapest robust filter; corroborated by both ORB studies and ML-filter practice |
| India VIX regime | Spot VIX level + Δ vs prev close; session tag (low/normal/high) | B− (inferred) | **context** | Free on Upstox feed (`NSE_INDEX|India VIX`); vol-regime gating is the Crabel/OR-filter mechanism; no direct NIFTY efficacy test — keep weight low |
| PCR / ΔOI / OI walls / max pain | Recompute PCR from CE/PE OI (ignore payload field); unavailable (not 0) when CE/PE OI ≤ 0; OI walls = top-3 ΔOI strikes per side | C (community practice, untested academically) | **context** | All top repos compute these for the analyst layer; zero efficacy evidence as trigger — LLM context only |
| ML/LLM signal filter | XGBoost-style filter over ORB/VWAP-breakout features; or LLM veto on aggregated state | C+ | **filter layer** only | Value demonstrated is trade REDUCTION (−63% trades, Sharpe 0.82→1.94), not prediction |
| Supertrend | n/a | D+ | **banned** (signal) | ATR(14) trailing stop permitted as exit risk mechanic, never as entry |
| EMA crossovers ≤15-min | n/a | F | **banned** | Negative expectancy intraday across assets; positive only on D1 (useless for scalping) |
| RSI threshold entries | n/a | D− | **banned** (entry) | Extreme-reading tag as context/exit heuristic only |
| Naive first-candle breakout | n/a | F | **banned** | ~52% sustain rate = coin flip (2,148 NIFTY sessions) |
| CVD / inferred delta / depth imbalance | n/a | D | **banned** | No aggressor flags on NSE feed; CVD sign error documented |
| ML direction-prediction (claimed >90% acc) | n/a | F | **banned** | Lookahead-bias graveyard |
| AVWAP (event-anchored) | n/a | ungraded | **banned** (evidence gap) | No rigorous test found anywhere; at most a chart annotation |

## Data ingestion spec

| Data type | Transport | Cadence | Rate-limit budget | Failure handling |
|---|---|---|---|---|
| Spot LTP: NIFTY index + India VIX | Upstox wss v3, `ltpc` mode | Streaming (push) | 1 of 2 wss connections; ~2 keys of 5,000 LTPC cap | No-message watchdog (30s during market hours) → reconnect w/ exp backoff; temp REST `/market-quote` fallback at 5s |
| ATM±15 option strikes: LTP + greeks + OI + IV | Upstox wss v3, `full` (or `option_greeks`) mode | Streaming (push); downsample in-process to 1-min bars via async queue | ~30 keys of `full` cap 2,000 (combined 1,500) | Same watchdog; re-subscribe on reconnect; queue decouples feed from strategy so burst drops don't block bars (dhan-bot pattern) |
| Full option chain (OI, PCR, max pain, greeks snapshot) | REST `GET /v2/option/chain` with `expiry_date=current_week` (relative keyword) | Every 30–60s, market hours only | Standard bucket (50/s nominal, third-party constants suggest 25/s / 250/min / 1000-per-30min — verify burst day 1); 1–2 req/min ≈ ≤540/day ≪ caps | Dedupe on payload timestamp (skip unchanged rows); recompute PCR, guard CE/PE OI ≤ 0; 3 consecutive stale/failed pulls → alert + mark chain features stale in snapshot |
| 1-min OHLCV bars (strategy/LLM unit) | Built in-process from wss ticks | Continuous aggregation | Zero API cost | On wss gap: backfill hole via historical-candle REST at resume |
| Historical candles (boot backfill, gap repair) | REST historical-candle API | Once at boot + on-demand | Standard bucket; handful of calls/day | Retry 3× exp backoff; if unavailable at boot, degrade to wss-only accumulation and flag reduced context |
| Instruments master (~60MB JSON gz) | HTTPS assets CDN (`complete.json.gz`) | Once daily at boot (pre-08:00) | Not API-rate-limited; CSV format deprecated | Parse failure → keep yesterday's file BUT still re-verify today's expiry via `/option/contract`; alert on mismatch |
| Instrument-key resolution (ATM strikes → `NSE_FO|xxxxx`) | Local SQLite/in-memory index over master (filter segment=NSE_FO, OPTIDX, underlying NIFTY) | Recomputed every session start; keys treated as ephemeral | Zero API cost | Never cache across expiries; on subscribe error, re-resolve via `/option/contract` before retrying |
| Order API | — (none: advisory bot, human executes) | — | Order bucket (10/s regular algo) intentionally untouched | n/a; keeps SEBI algo-registration exposure minimal (route Q to compliance track — R12 open Q6) |
| NSE scrape (OPTIONAL cross-check only) | REST scrape w/ session cookies, http2, UA rotation | 5 min, market hours only | Fragile by nature; IP-ban risk | Any 401/cookie failure → disable silently for the day; NEVER on critical path |

## Ops spec

**Auth refresh workflow (3:30 AM IST token death — #1 documented failure mode):**
- Token always expires 03:30 IST regardless of issue time. Daily re-auth job scheduled 07:30–08:45 IST, well before warm-up.
- Preferred: automated OAuth via Playwright+TOTP (upstox-auth-pro pattern); fallback: manual login with notifier-webhook delivery (Upstox Access Token Request API can POST the token to a webhook on approval).
- Post-auth verification: one cheap authenticated REST call (e.g., funds/profile); on 401 → retry once, then FAIL LOUDLY (alert channel) before 09:05 — silent overnight auth death is the canonical outage.
- Websocket 401s ≈ stale token; treat as auth failure, not network failure.
- Sandbox note: sandbox token lasts 30 days but covers ORDERS ONLY — no option chain/market data; paper-trade against live feed with orders pointed at sandbox if ever needed.

**Instrument-key resolution:**
- Keys (`NSE_FO|<num>`) are per-expiry ephemeral — the largest bug class is expiry-rollover. Reload master at boot, index (expiry, strike, type), resolve ATM±15 fresh each morning, always call `/option/chain` with relative expiry keywords (`current_week` etc.) so the chain auto-rolls.

**Market-hours gate:**
- Collect/strategize only Mon–Fri (holiday calendar check) 09:05 warm-up → 15:35 teardown. Chain/OI data flatlines off-hours; wss feed is heartbeats-only off-hours. LLM snapshots, chain polling, and bar consumers all gated; off-hours runs use recorded replay only.

**Watchdog:**
- wss: no-application-message for 30s inside the gate → reconnect with exp backoff (SDK only raises on close; implement own liveness). Respect 2-connection/user cap — kill the old socket before opening the new one, or reconnect storms lock you out.
- Chain: staleness alarm after 3 unchanged-timestamp cycles; PCR sanity guards; storage-write monitor.
- Daily pre-open health summary (auth OK, master loaded, keys resolved, feed connected) to alert channel; kill-switch flag file checked by every job (deltaforge pattern).
- Same code path for backtest/paper/live via data-source abstraction (deltaforge pattern); binary protobuf decode via official `MarketDataFeed.proto`.

## Demoted/dropped + reasons

1. **Zarattini 33%-alpha ORB headline** — demoted: independent replication Sharpe −0.06 full-sample, −0.84 post-publication; use ORB only with filters + decay monitoring (R06 S6–S9, S23).
2. **Supertrend as signal** — dropped to banned: flat win rate across all params, intraday whipsaw + Indian costs fatal despite massive retail-bot adoption (R06 S15–17 vs R12 practice — adjudicated: retail usage is alert-layer folklore).
3. **Intraday EMA/MA crossovers** — banned: F-grade, negative after costs on every sub-daily TF tested (S3, S5, S20, S21).
4. **RSI/RSI(2) standalone entries** — banned as entry; only an extreme-reading context tag survives (S22, S3).
5. **Naive first-candle / unfiltered ORB** — banned: 52% sustain = coin flip (S11).
6. **CVD / tick-rule delta / 30-depth imbalance** — banned: no aggressor flags on NSE/Upstox feed; documented sign-error risk (S25; R12 full_d30 unvalidated for options).
7. **CNN-LSTM / any >90%-accuracy direction ML** — banned: leakage/overfit signature (S26).
8. **LLM in per-tick hot loop** — demoted to scheduled slow-layer analyst at 1-min+ aggregated cadence; no repo documents profitable per-tick LLM scalping; deterministic code owns signals (R12 avoid #3, corroborates R06 S27 lesson).
9. **NSE scraping as primary feed** — dropped: cookie arms race, 401s, IP bans; optional cross-check only (R12 pitfalls; we pay for Upstox).
10. **Tight full-chain polling loops / tick-speed OI** — dropped: Dhan's 1-per-3s rule and stale-timestamp dedupe prove OI doesn't move that fast; wss carries OI/IV for subscribed keys anyway (R12).
11. **AVWAP signals** — dropped to visualization: total evidence gap (R06 open question).
12. **Payload PCR / rounded chain fields** — demoted: always recompute from OI; treat as unavailable (not 0) on zero-OI rows (R12 pitfall #8/README).
13. **Hardcoded expiry dates / cached instrument keys** — banned as engineering practice: relative expiry keywords + daily master reload only (R12).
14. **Mid-day trend-following and open/final-hour mean-reversion** — flagged anti-regime: clock tags gate which bias is admissible (R06 S1/S12/S19/S24 synthesis).
15. **Tick-store infrastructure (QuestDB/TimescaleDB)** — descoped: SQLite/Parquet for chain snapshots + 1-min bars suffices at advisory-bot scale (R12 avoid #4).
