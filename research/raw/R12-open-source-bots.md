# R12: Open-source evidence base — NIFTY option-chain bots & retail algotrading repos

Date: 2026-09-16. All star counts verified via GitHub API on 2026-09-16. No fabricated URLs — every repo below was fetched/searched and exists.

## Sources

| # | Repo/Doc | Stars | Year updated | URL | What it does |
|---|----------|-------|--------------|-----|--------------|
| 1 | VarunS2002/Python-NSE-Option-Chain-Analyzer | 659 | 2026 | https://github.com/VarunS2002/Python-NSE-Option-Chain-Analyzer | Tkinter desktop app polling NSE's public option-chain API; computes PCR, max pain, OI change, IV skew; continuous auto-refresh, only adds row when NSE timestamp changes |
| 2 | upstox/upstox-python (official SDK) | 187 | 2026-09 | https://github.com/upstox/upstox-python | Official SDK: REST wrappers + `MarketDataStreamerV3` websocket client w/ protobuf (`MarketDataFeedV3_pb2`); 47 interactive examples incl. option-chain flows |
| 3 | BennyThadikaran/NseIndiaApi | 161 | 2026-08 | https://github.com/BennyThadikaran/NseIndiaApi | Robust NSE unofficial API wrapper; handles cookie/session dance (httpx http2 on servers), FNO option chain for nifty/banknifty/finnifty/niftyit |
| 4 | hopit-ai/india-trade-cli ("Vibe Trading") | 103 | 2026-09 | https://github.com/hopit-ai/india-trade-cli | Multi-agent LLM platform for NSE/BSE/NFO: 7 analyst agents (options analyst incl.) debate bull/bear; LLM-agnostic (Gemini/Claude/OpenAI/Ollama); live orders via Fyers/Zerodha |
| 5 | sumitsainidev/OIAnalysis | 37 | 2020 | https://github.com/sumitsainidev/OIAnalysis | Classic pattern: poll NSE option chain every 5 min per strike, dump to Excel, pivot tables for OI buildup (long/short buildup signals) |
| 6 | zackakshayy/zAck_trading_bot | 15 | 2026 | https://github.com/zackakshayy/zAck_trading_bot | Event-driven Zerodha NIFTY F&O bot w/ LLM (Gemini) + RAG in the loop for loss analysis & strategy reassessment; isolated worker pattern for thread-safe orders |
| 7 | leomoon85/nifty_tradebot | 4 | 2023 | https://github.com/leomoon85/nifty_tradebot | Learning project: ML/AI NIFTY option trading |
| 8 | Akash9078/option-chain-dashboard | 0 | 2026 | https://github.com/Akash9078/option-chain-dashboard | Streamlit dashboard on unofficial NSE API: OI/ΔOI/PCR/ΔPCR/IV smile, max pain, participant-wise OI (FII/DII); auto-collects PCR only 09:15–15:30 IST |
| 9 | Harish2106/dhan-trader-bot | 0 | 2026 | https://github.com/Harish2106/dhan-trader-bot | Async BankNifty scalping bot on DhanHQ: websockets → asyncio queues → 1-min candle builder; rate-limit discipline (25 orders/s cap) |
| 10 | growthquantix/upstox-auth-pro | 2 | 2026 | https://github.com/growthquantix/upstox-auth-pro | Playwright+TOTP automation of Upstox OAuth daily login; IST-aware token expiry handling (3:30 AM IST) — exists *because* of the daily-token pain |
| 11 | Tanmay-312/trade-engine | 2 | 2026 | https://github.com/Tanmay-312/trade-engine | Go+Python NIFTY options scalper; Zerodha Kite websockets, gRPC/protobuf between brain/executor, QuestDB for ticks, daily manual token refresh noted |
| 12 | DRD8077/jarvis-trading-bot | 1 | 2026 | https://github.com/DRD8077/jarvis-trading-bot | NSE-scraping analytics: PCR w/ trend, max pain, futures basis, FII/DII, straddle premium, multi-expiry compare |
| 13 | deepak-05dktopG/IndiaQuant-MCP-Server | 1 | 2026 | https://github.com/deepak-05dktopG/IndiaQuant-MCP-Server | MCP server for Claude Desktop: option chain from yfinance, Black-Scholes Greeks from scratch, max pain, OI-spike z-scores, SQLite local storage |
| 14 | mimran-khan/deltaforge | 2 | 2026 | https://github.com/mimran-khan/deltaforge | Autonomous Angel One NIFTY intraday options engine; backtest=paper=live same code path; Telegram/Slack alerts, kill switch |
| 15 | DhanHQ docs (benchmark for option-chain API) | n/a | live | https://dhanhq.co/docs/v2/option-chain/ | Option-chain endpoint explicitly rate-limited to 1 request / 3 s "because OI data gets updated slowly compared to LTP" — design hint for polling cadence |
| 16 | Upstox API docs (rate limits, option chain, feed v3, sandbox) | n/a | live | https://upstox.com/developer/api-documentation/rate-limiting | Official: REST order vs standard API limits, wss v3 protobuf feed, sandbox orders (30-day token) |
| 17 | Upstox community threads | n/a | 2024-26 | https://community.upstox.com/t/unauthorized-401-from-websocket-connection/5847 | Token-expiry 401s on websocket; confirm token valid for one day, expires 3:30 AM IST |
| 18 | StackOverflow NSE 401 threads | n/a | 2020-25 | https://stackoverflow.com/questions/63981362/python-requests-get-returns-response-code-401-for-nse-india-website | Canonical "NSE blocks scrapers" thread: session + cookies + UA required; cookie rotation breaks scrapers periodically |

## Polling vs streaming

| Repo/solution | Data source | Cadence | Why |
|---|---|---|---|
| VarunS2002 NSE-OCA (#1) | NSE REST scrape | POLL every ~10s–1min (configurable), dedupes on NSE timestamp | NSE public API updates OI/LTP slowly; no official stream exists for chains |
| sumitsainidev/OIAnalysis (#5) | NSE REST scrape | POLL every 5 min & 15 min | OI interpretation needs interval snapshots; Excel/pivot workflow |
| Akash9078 dashboard (#8) | NSE REST scrape | POLL, fixed interval, **market hours only** (09:15–15:30, Mon–Fri) | Chain is dead outside hours; saves quota & storage |
| Harish2106 dhan-trader-bot (#9) | DhanHQ websocket ticks → 1-min OHLCV candles built in-process | STREAM ticks, DOWNsample to 1-min bars for strategy | Scalping needs tick latency; strategies need bars; queue decouples them |
| Tanmay-312/trade-engine (#11) | Kite websocket + yfinance REST backfill | STREAM ticks to QuestDB; REST for history | Tick store for ML replay; REST can't give intraday history cheaply |
| upstox-python examples (#2) | REST `/option/chain` + wss v3 | REST for full-chain snapshot incl. greeks; STREAM for subscribed keys (LTPC/full/option_greeks modes) | Upstox designed exactly this split: chain = on-demand REST, live prices = push |
| Dhan option chain (#15) | REST POST /optionchain | Hard limit 1 req/3s | Broker states OI updates slowly — polling faster is pointless AND blocked |
| deltaforge (#14) | Angel One SmartAPI stream | STREAM + scheduled strategy ticks | Same engine backtest/paper/live → data abstraction layer common pattern |
| NSE-OCA edge case | new row appended ONLY if server timestamp changed | n/a | NSE repeats stale payloads; dedupe avoids fake series |

## Common pitfalls documented

- **Daily token expiry (Upstox)**: access token dies at 3:30 AM IST regardless of generation time; "I have seen setups silently stop trading overnight because nobody refreshed the token before the open" (jayadevrana.com). 401s on websocket are almost always stale tokens (community.upstox.com/t/5847). Whole repos exist just to automate login (upstox-auth-pro #10, Playwright+TOTP).
- **Instrument-key drift**: `NSE_FO|<number>` keys are session-token-like identifiers that change per expiry (see Upstox chain response example: NSE_FO|51059). Never cache instrument keys across expiries — re-resolve via `/option/contract` + master instruments file every morning. (Upstox docs; upstox-instrument-query PyPI pkg exists to query the ~60 MB complete.json.gz via SQLite.)
- **NSE scraping is fragile**: 401s without session cookies; `nsit`/`nseappid` cookies required; cloud IPs need httpx/http2; cookies rotate (SO threads #18, NseIndiaApi #3). Don't build the primary feed on NSE scraping.
- **Stale/duplicate data from NSE**: scrapers must dedupe on NSE `timestamp` field or analysis series fills with repeated rows (#1 README).
- **Market-hours-only data**: option chain + OI flatline outside 09:15–15:30; repos gate collection jobs to market hours & weekdays (#8); India VIX/OI meaningless overnight.
- **Websocket reconnect handling**: trade-engine (#11) advertises "auto-recovery for network disconnects"; zAck bot (#6) isolates order execution in a worker so feed threads can't block orders. Upstox v3 caps at **2 connections per user** — reconnect storms will lock you out.
- **Rate-limit shocks**: Dhan 1 chain req / 3 s; Upstox splits order vs standard buckets (see cheat-sheet); repos get "temporary suspension" warnings when naive loops exceed per-second caps (Upstox docs: "Exceeding these limits might result in temporary suspension of access").
- **PCR payloads unreliable**: #8 README recomputes PCR from OI rather than trusting rounded payload values; treats PCR as unavailable (not 0) when CE/PE OI ≤ 0 — division-by-zero and garbage-PCR bugs are common.
- **SEBI retail-algo rules (Apr 2026)**: static IP, Algo-ID registration for ops>threshold, and order API rate classes (regular algo 10 req/s vs registered 50 req/s) trip new builders (Upstox announcements; jayadevrana.com).
- **CSV instruments file deprecated** — must parse JSON gz (Upstox announcements).

## Upstox API cheat-sheet (implementation-ready)

**Auth**
- OAuth2 auth-code flow: `POST https://api.upstox.com/v2/login/authorization/token` (form-encoded: code, client_id, client_secret, redirect_uri, grant_type).
- Token valid **until 3:30 AM IST next day**, always. Plan a pre-market (≈07:30–08:45 IST) re-auth job. Access Token Request API can push token to a notifier webhook on approval.
- **Sandbox**: separate sandbox app + token valid 30 days; **orders only** (place/modify/cancel v2&v3, multi order). NO sandbox for option chain or market data — market data is free anyway.

**Option chain REST**
- `GET https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX%7CNifty%2050&expiry_date=YYYY-MM-DD` (not available for MCX).
- `expiry_date` also accepts relative keywords: `current_week`, `next_week`, `far_week`, `current_month`, `next_month`, `far_month` — auto-rolls after expiry; USE THIS to avoid expiry-drift bugs.
- Response rows: `expiry`, `strike_price`, `pcr`, `underlying_key`, `underlying_spot_price`, plus `call_options`/`put_options` each with `instrument_key` (NSE_FO|xxxxx), `market_data{ltp, volume, oi, prev_oi, close_price, bid_price/qty, ask_price/qty}`, `option_greeks{vega, theta, gamma, delta, iv, pop}` (`pop` = probability of profit, added 2025).
- Companion: `GET /v2/option/contract?instrument_key=...` lists all strikes+expiries for an underlying.

**Rate limits (per API, per user)**
- Order place/modify/cancel/multi/GTT combined: regular algo **10/s, 500/min, 2000/30min**; SEBI-registered algo **50/s**.
- "Other standard APIs" (holdings, positions, funds, **historical candles, market quotes**): **50/s, 500/min, 2000/30min**.
- Community/third-party SDK constant files show option/market-quote buckets ~25/s — stay well under; suspension is the penalty.

**Instruments master (expiry/strike resolution)**
- `https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz` (~60 MB uncompressed-ish stream; CSV format being deprecated → parse JSON). Download at boot, filter `segment == "NSE_FO"` + `instrument_type == "OPTIDX"` + `underlying_symbol == "NIFTY"`, index by (expiry, strike, option_type). Pattern proven by upstox-instrument-query (SQLite + LRU cache).
- Expired instruments + historical data v3 endpoints exist for backtesting.
- India VIX available as `NSE_INDEX|India VIX` on the feed — free volatility regime input.

**Websocket v3 (MarketDataFeedV3)**
- Two-step: `GET /v2/feed/market-data-feed/authorize` → authorized wss URL → connect (client must follow redirects). **Binary protobuf** messages; decode with `MarketDataFeed.proto` from `https://assets.upstox.com/feed/market-data-feed/v3/MarketDataFeed.proto` (sdk bundle: `MarketDataFeedV3_pb2`).
- Subscribe modes: `ltpc`, `full`, `option_greeks`, `full_d30` (30-level depth). Change mode per-key at runtime via `change_mode`.
- Limits: **2 connections per user**; per-mode caps — LTPC 5000 keys, option_greeks 3000 (combined 2000), full 2000 (combined 1500). Per-connection subscription message caps apply.
- `MarketFullFeed` fields: ltpc, marketLevel (5-depth bid/ask), optionGreeks, marketOHLC, atp, vtt, **oi, iv**, tbq/tsq — meaning OI and IV stream natively, no polling needed for subscribed keys.
- Feed carries Closing Auction Session fields (iep, rp, ieq, imbalance qty) in full/ltpc during pre-open & CAS.
- Feed is silent/heartbeats-only outside market hours — gate downstream consumers, and detect feed-dead via no-message timeout (implement our own watchdog; SDK raises only on close events).

## Implications for our bot

**Copy these patterns:**
1. **Hybrid REST snapshot + websocket stream** (matches Upstox's own architecture): pull `/option/chain` every 30–60 s for full-chain OI/greeks deltas (PCR, max pain, OI walls), subscribe via wss in `full`/`option_greeks` mode for the ~15±3 strikes near ATM for tick-level LTP/OI/IV. Dhan's 1-req/3-s rule and NSE-scrapers' 5-min cadence both prove OI doesn't change faster — don't poll a full chain at tick speed.
2. **Relative expiry keywords** (`current_week` etc.) — eliminates the #1 class of expiry-rollover bugs (hardcoded dates).
3. **Daily instrument-master reload at boot** into SQLite/in-memory index (upstox-instrument-query pattern); resolve ATM strike → instrument_key fresh each session; treat keys as ephemeral.
4. **Automated auth with watchdog** (upstox-auth-pro pattern): IST-aware expiry check, exponential backoff on transient failures, fail loudly (screenshot/alert) — silent overnight auth death is the most documented failure.
5. **Market-hours gating** (09:05 warm-up → 15:35 teardown): saves storage, avoids "analysis" on dead data (dashboard #8 pattern).
6. **Tick → bar downsample in async queue** (dhan-trader-bot #9): subscribe ticks, build 1-min candles in-process, strategies consume bars — clean separation of feed latency from strategy logic.
7. **Same engine for backtest/paper/live** (deltaforge #14): data-source abstraction; synthetic-past replay for off-hours dev (IndexVol-style offline replay).
8. **Dedupe + sanity on chain payloads**: drop rows with unchanged timestamps; guard PCR when CE/PE OI ≤ 0; prefer recomputed PCR over payload field.

**Avoid:**
1. Scraping NSE as primary data source — cookie arms race, 401s, IP bans; we already pay for Upstox. (Keep NSE scrape as optional cross-check only.)
2. Polling full option chain in a tight loop — wastes the 50/s bucket and risks suspension; websocket + sparse REST wins.
3. LLM-in-the-hot-loop per tick. The LLM repos (hopit-ai #4, zAck #6, MCP servers #13) all converge on LLM as *slow-layer analyst* — scheduled multi-agent debate, killed-trade review, daily bias memo — while deterministic code owns execution. zAck's `strategy_reassessment_period_minute` + 5 trades/day cap and paper-default flags are the safety posture to mirror. None of these repos document profitable live LLM scalping; the viable snapshot format is aggregated state (bars, OI walls, PCR trend, positions) at 1-min+ cadence, not raw ticks.
4. Storing ticks naively — QuestDB (#11) / TimescaleDB (aaryansinha16 AI-trader) / SQLite (#13) are the three observed tiers; for our scope, SQLite/Parquet for chain snapshots + bars is enough.
5. Assuming sandbox covers market data — it doesn't; paper-trade the pipeline against the live feed with orders pointed at sandbox.

**Strategy-catalogue bookmarks:** Quantpedia intraday option entries (e.g., #1116 Intraday Option Reversals — half-hourly reversal predictability; premium-gated but abstracts free); Quantplay NIFTY 9:30 short-ATM-straddle parametrization (entry/exit times, 50% premium SL per leg); broussardkobey67-spec/nifty-straddle-backtest (intraday-only enforcement: senior-priority insight = never hold short gamma overnight intraday-standard, combine-premium SL, re-entry cutoff). Backtest libs seen in the wild: `backtesting.py` (Harish2106 suite), custom tick-replay engines (aaryansinha16), Opstrat (payoff diagrams), Quantsbin (Greeks).

## Open questions

1. Actual Upstox *option-chain REST* per-second bucket: docs lump it under "standard APIs" (50/s) but third-party SDK constants show 25/s / 250/min / 1000 per 30 min for market-data endpoints — verify empirically with burst test on day 1.
2. Sandbox order fills: do sandbox fills simulate realistic slippage/partial fills for scalping realism, or instant-fills only? Needs hands-on test.
3. Upstox v3 `full_d30` mode availability for NSE_FO options vs equities — docs are equity-centric; confirm 30-depth on option keys.
4. Does `/option/chain` return data pre-open (e.g., 08:55) with greeks from prev close, or empty? Deterministic behavior matters for the morning warm-up sequence.
5. LLM snapshot compression: what minimal token format (top-N strikes × [LTP, ΔOI, IV] + PCR trend + spot deltas) preserves decision quality? No repo measured this — our own ablation needed.
6. April 2026 SEBI rules: whether an advisory (no auto-execute) bot still needs static-IP/Algo-ID registration — legal/compliance check (R-agent for regulatory track).
