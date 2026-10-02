# CONTEXT.md — trading-bot

The original advisory and paper paths remain shadow-only. An explicitly armed agent-driven Kite autopilot was added on 03-Oct-2026; see `docs/kite-live.md`. No live pilot has been activated.

Original NIFTY options intraday advisory bot: deterministic Python computes market features, levels, costs, sizing, and safety gates; an LLM may only validate a supplied candidate or choose `NO_TRADE`; every model decision is shadow-only; a human remains the only possible executor. Research in `research/` is the evidence baseline, but explicit decisions here and in `DATABASE.md` supersede conflicting synthesis implementation details.

## Operating mode and approved pilot decisions

- The pilot is forward-only shadow mode. It never places orders and every terminal advice is labelled `SHADOW ONLY - DO NOT EXECUTE`.
- The sole signal family is a filtered 15-minute opening-range breakout: range labels 09:15–09:29 IST, breakout evaluation from 09:30, but the conservative entry-time gate blocks all new candidates before 09:45.
- Fixed risk settings: maximum hypothetical loss ₹2,500/trade and daily actual-user-loss cutoff ₹5,000. India VIX >16 halves the hypothetical risk budget. Position size is always engine-owned.
- VWAP source is decided: nearest NIFTY futures OHLCV. The implementation is explicitly a one-minute typical-price/volume proxy, not tick VWAP; raw futures fields are stored for audit but omitted from the model snapshot.
- REST-only features are active. WebSocket/tick-only OFI, L1/L5 imbalance, CVD, signed volume, and true tick-mid MAE/MFE remain disabled.

## Upstox data source and authentication

- Upstox is the only advisory-critical market source. The API surface is fixed-host, authenticated, read-only GET; there is no order or generic-URL tool.
- Pilot cadence: `GET /v3/market-quote/quotes` about every 5 s, concrete-expiry `GET /v2/option/chain` every 30 s, intraday NIFTY/futures candles once per persisted minute, and one `market_data` row per IST minute.
- Sending literal `current_week` to Upstox returns an empty chain. Resolve relative expiries client-side from unfiltered `GET /v2/option/contract`, then call the chain with the nearest concrete non-expired date. Expiry-bound `NSE_FO|<num>` keys and lot size are refreshed each session.
- One-minute historical requests are split into non-overlapping chunks of at most 29 inclusive calendar dates; Upstox rejects the required 45-day baseline as one request. Historical responses are newest-first `{candles: [...]}` and are sorted/deduplicated locally.
- Candle endpoints: `GET /v3/historical-candle/intraday/:instrument_key/:unit/:interval` and `GET /v3/historical-candle/:instrument_key/:unit/:interval/:to_date/:from_date`.
- The one-year read-only Analytics Token is supplied only as `UPSTOX_ACCESS_TOKEN`. The configured local `.env` is gitignored; the application loads only explicitly allowlisted names and never logs tokens.
- Retry only HTTP 429 and 500/502/503/504 with bounded backoff. Continuous collection retains old data so it ages stale; unexpected code/storage failures terminate visibly.

## Verified market and cost constants (17-Sep-2026)

- Live contract metadata confirms the current NIFTY weekly expiry is Tuesday and current contract lot size is **65**, not the stale 75-unit research assumption. Never hardcode lot size; use current ATM contract metadata.
- Tick size is ₹0.05, currently ₹3.25/tick/lot and ₹65 per option-premium point per lot. Candidate prices are rounded to the exchange tick grid; long stops round upward so rounding cannot widen risk.
- Live ATM contract trades at `15:39:59` confirm the CAS-era equity-derivatives close at 15:40 IST. Continuous index cash data may freeze during CAS; the engine remains conservative and blocks stale data.
- Current option cost configuration: brokerage ₹20/executed order; sell-side STT 0.15% of premium; NSE transaction charge 0.03553%/side; GST 18% on brokerage + transaction + SEBI fee; SEBI ₹10/crore; stamp 0.003% buy-side. Costs and breakeven ticks are derived at runtime with current lot size and quoted spread; they are not stored as authoritative result columns.
- The 2026 NSE calendar is built in, including the 1-Feb special Budget session. Unsupported years, weekends, and holidays fail closed. Re-verify and add each new calendar year before use.

## Collector and deterministic engine

- Main collector: `.venv/bin/python -m trading_bot.collector`; `--once` performs a bounded fetch/compute/persist diagnostic even off-hours. Continuous mode only calls Upstox from ten minutes before a supported session through session close.
- Automatic expiry, ATM±4 chain window, ATM±1 basis quotes, nearest future, dynamic lot size, NIFTY/VIX/futures/options quotes, historical baselines, and completed common NIFTY/futures bars are persisted.
- Implemented features: 15-minute ORB; 20-session relative-volume confirmation (threshold 1.5×); futures VWAP proxy and same-time sigma; first-30-minute return; recomputed PCR; ATM IV and one-day expected move; 10-day realized volatility and IV/RV ratio; 252-session ATM-IV percentile when history exists; synthetic-forward basis; top-two call/put OI walls; local-only GEX regime; and same-time historical 30-minute range for theta gating.
- Local GEX is low-weight context only and retains the unverified dealer-position sign assumption. Market-wide signed GEX is never computed.
- Theta proxy: 30-minute decay = `abs(theta) * 30 / 385`; required underlying move = `(theta decay + cost per unit) / abs(delta)` and is compared with the historical same-time 30-minute NIFTY range.
- Hard gates include stale quote/chain/bar data, unsupported/closed sessions, 09:45 opening block, midday windows, expiry cutoffs/flat time, 15:15 late-entry cutoff, spread ≤2% of mid, strike within ±3% of spot, relative volume, narrow opening range, IVP when available, expected MFE ≥3× cost, daily actual-user P&L, kill-switch file, cost-efficient size, and theta clock.
- Data is fail-closed and missing values are SQL `NULL`, never invented zeroes. Fresh rows remain blocked by the internal `SHADOW_MODE` flag because the user workflow is paper trading. Bootstrap-only blockers for missing IV-percentile, expected-MFE, level-calibration, and theta history can be tolerated while those histories are built. `RISK_BUDGET_TOO_SMALL` and `COST_INEFFICIENT_SIZE` are hard blockers: a paper trade must still fit at least one lot inside the risk and cost rules.

## Agent-harness advisory boundary

- Primary advisory path is the model already running in Devin, Claude Code, or another shell-capable agent harness. It requires no separate LLM API key or model configuration.
- Root `AGENT.md` is the operational runbook for coding agents. Devin project skill: `/nifty-advice`, implemented at `.devin/skills/nifty-advice/SKILL.md`. The portable two-step CLI for any harness is `.venv/bin/python -m trading_bot.agent_tool prepare`, followed by `agent_tool submit` with the harness model's strict JSON through stdin/heredoc.
- `prepare` performs a fresh Upstox collection and all deterministic calculations, then either returns an engine-owned `NO_TRADE` or writes a 90-second `PENDING` request under `data/agent-requests/`. `submit` never calls Upstox or an external model; it validates, demotes if required, and persists the harness output.
- Every tool response includes the exact boundary `SHADOW ONLY - DO NOT EXECUTE`. Invalid output receives at most one harness retry; the second invalid output and a response older than 90 seconds deterministically persist `NO_TRADE` fallbacks.
- Production prompt: `trading_bot/prompts/system_v1.txt`, version `v1`, SHA-256 `88847bbecb7351bdb316705461c90705ef4a901f1baad230e131d25c3cebb2c5`. Engine version is `0.2.0`.
- Snapshot is a compact JSON/CSV envelope: latest 15 unique completed bars, ATM±4 chain, derived features, candidate, and gates; hard limit 12,000 bytes. It excludes lots, risk budget, sized costs, and raw futures price.
- Output is exact strict JSON: `action`, confidence label, A/B/C setup quality, nullable engine levels, one-sentence `idea_fails_if`, `data_conflict`, and reason ≤25 words. No size or order fields.
- LONG action must match the engine candidate and echo tick-valid engine entry/stop/target exactly. Every number in free text must already occur in the snapshot. Unknown numbers are logged as hallucination events.
- Confidence `[0.45,0.55]` and `data_conflict=true` are demoted in code. Database uniqueness and artifact recovery enforce idempotency on `(context_to, prompt_hash)`, including concurrent/crash-recovery paths.
- The fixed-host OpenAI Responses adapter remains optional for standalone automation via `--enable-openai-advisory` (`--enable-advisory` is a hidden compatibility alias). It is not the primary architecture and is not needed by `/nifty-advice`.

## LLM versus deterministic trading evidence (second pass, 17-Sep-2026)

### Durable verdict

- Two independent broad searches plus the repository audit found **no direct public head-to-head** between a frontier LLM and a deterministic algorithm for intraday NIFTY option buying. Do not claim that either approach has demonstrated positive expectancy for this exact task.
- Deterministic Python remains the direction/candidate, arithmetic, levels, costs, sizing, timing, and risk authority. The live agent remains an accept-or-`NO_TRADE` filter. Do not allow the agent to reverse CALL↔PUT or create a second candidate without a separately approved experiment.
- This verdict is about reliability and evidence, not profitability: the filtered ORB Python strategy is also unproven and must pass the same forward, cost-inclusive gates.
- The current prompt is safe but intentionally narrow/generic. No public “NIFTY master prompt” has credible forward, cost-inclusive proof. `system_v1.txt` remains active; an ordered NIFTY-checklist v2 is research work, not an approved prompt change.

### Strong negative/directly cautionary evidence

- `What LLM Trading Agents Actually Do in Production` (arXiv:2609.05663) measured ~7.5M invocations, ~300K on-chain actions, and 3,505 user-funded vaults. The fleet was unprofitable, had 41% round-trip wins versus a 50% matched retail benchmark, frontier models were statistically indistinguishable on 416 paired production scenarios, and a mechanical bracket recovered 39 bps/position. Asset class is crypto, but the live direction/exit failure is decision-relevant.
- FINSABER (KDD 2026, arXiv:2505.07078) re-tested LLM investors over two decades and 100+ equities with broader universes and execution assumptions. Published advantages deteriorated; agents were too conservative in bull regimes and too aggressive in bears. This rejects broad “frontier intelligence implies trading skill” claims.
- RetailAgent (arXiv:2608.28399) found persistent adverse intraday timing when LLMs chose long versus flat on anonymized equity paths; shuffling actions weakened the effect and self-authored memory increased persistence. Treat agent-direction timing as an explicit shadow hypothesis, not an assumed edge.
- `What survives honest evaluation?` (arXiv:2608.27734) used point-in-time universes, realistic transaction/impact/borrow costs, trial logging, and up to 100 candidates across repeated frontier-model runs; it rejected every LLM-discovered strategy. Leakage controls and trial-count correction are both mandatory.
- Finance arithmetic/reasoning benchmarks continue to show nonzero frontier-model errors and spurious predictability. Code must keep every numerical operation and market-world-state transition outside the LLM.

### Credible positive niches that do not justify agent direction control

- `LLM as a Risk Manager` (ACL Industry 2026, arXiv:2602.07048) is the strongest positive filter result: on 554 Kalshi economics markets across 18 rolling evaluations, an LLM semantic filter over a statistical Granger screen raised wins 51.4%→54.5%, reduced average loss $649→$347, and increased reported P&L $4.1K→$12.5K. The gain came from rejecting economically implausible relationships. This supports our agent-veto architecture **when meaningful text/causal descriptions are present**; it does not validate a metrics-only NIFTY direction call.
- A 2026 financial-news study evaluated ~973K tradable US news items across 3,452 firms and reported stronger LLaMA-3 sentiment classification and a positive daily long/short portfolio after a 5-bps cost assumption. It supports a text-event research branch, but is US, daily, cross-sectional, and not an intraday index-option result.
- `Scaling Point-in-Time Language Models` (NBER WP 35247, 2026) trained chronologically restricted models and found positive out-of-sample portfolio information in text embeddings. This establishes that date-safe language signals can exist; it does not establish that a current general chat model times 30-minute NIFTY options.
- RBI communication research (arXiv:2411.04808) found topic-specific language effects in Indian markets: “dovish” wording can be equity-negative when it signals economic weakness. This supports an official-source RBI/Budget event interpreter as context, not automatic direction.
- Dealer/gamma obfuscation research (IEEE Big Data 2025; arXiv:2512.17923) reported 71.5% unbiased structural-pattern detection on 242 SPY days and high forward pattern materialization, but later analysis showed profitability could collapse while detection remained stable. Structural understanding is not alpha. Raw strike structure may preserve information lost by scalar GEX; test only in shadow because Indian dealer sign is unknown.
- PACE (arXiv:2607.28410) reported a 0.65-bps improvement over the strongest parent-order execution baseline on Shenzhen Level-1 data. It concerns institutional order splitting and is irrelevant to the present small, human-executed, no-order-API pilot.
- Constrained LLM factor discovery (arXiv:2604.26747) reported a 2024–2026 crypto OOS Sharpe of 1.55 after 5-bps one-way cost when the LLM proposed hypotheses and deterministic code controlled data, splits, tests, and acceptance. It supports an offline research role only and is counterbalanced by the honest-evaluation rejection above.

### NIFTY-specific adjacent opportunities

- High-frequency GIFT Nifty/NIFTY studies find cointegration and meaningful futures price discovery. GIFT Nifty is a candidate for pre-market context; after domestic open, use measured lead/lag rather than assuming permanent leadership.
- Older NIFTY studies find option-implied/call prices can lead spot, particularly near expiry. The active `synthetic_fwd_basis` implements this hypothesis, but must remain log-then-arm until current lead time is measured.
- A public NIFTY 0DTE remaining-variance project reports expanding-window OOS R²≈0.394 across 313 expiry days using morning realized variance plus prior-day VIX. Treat this as a promising but non-peer-reviewed expiry-day **remaining-movement/no-buy filter** experiment, not an active production rule.
- NIFTY volatility-risk-premium evidence generally favors compensated option selling/defined-risk short-volatility over directional option buying, often with important overnight/intraday asymmetry. That is a separate strategy, capital, and risk product; never silently mix it into the buying-only pilot.
- Classical selective classification/meta-labeling has evidence that a second numerical model can reject weak primary signals. Once enough forward rows exist, a logistic/gradient-boosted filter trained only on our outcomes is a required comparator to the agent veto and may be better suited to structured metrics.
- NIFTY-specific LLM/news papers and IEEE workshop work suggest constituent-news sentiment may improve short-term option valuation, but public results do not establish intraday index-option P&L after realistic costs. Keep as a lead, not evidence of live readiness.

### Rejected or weak evidence guardrails

- Do not import the public `sunnywilson93/nifty-options-analysis` Claude skill. Its checked version uses stale lot size 75, fixed PCR thresholds, unsupported “OI wall holds 70–80%” and max-pain claims, and no audited forward P&L.
- Do not accept 74–95% NIFTY prediction headlines without exact temporal splits, label definitions, all attempted trials, and realistic option fills. OptiSense advertises ~87% but acknowledges approximately 60% under stronger anti-leakage validation; venue and cost evidence remain weak.
- Treat NIFTY sentiment claims such as 68.5% direction accuracy as incomplete when chronological holdout, publication-time alignment, turnover, spread, slippage, STT, and option translation are absent.
- Reject tiny-sample claims such as 100% wins on three trades or high Sharpe on ~15 trades.
- Treat README/blog results, marketing dashboards, “real-like” examples, auto-execution demos, and private/missing RAG modules as implementation leads only—not performance evidence.
- DSR/PBO cannot repair future-data leakage. Feature availability must make look-ahead impossible before statistical correction is applied.

## Research experiments and offline agent workflow (proposed; not active trading logic)

- Record frozen comparison arms on the same timestamp/data/fills: (A) Python direction alone; (B) Python + metrics-only agent veto; (C) Python + official event-text agent veto; (D) independent agent CALL/PUT/NO_TRADE; (E) opposite of independent agent direction as an adverse-timing diagnostic; (F) trained numerical meta-filter once enough data exists; (G) expiry remaining-movement filter; (H) raw chain-structure classification versus scalar GEX.
- Every arm must use identical entry time, instruments, fills, costs, 30-minute outcome rules, and no per-trade prompt changes. Pre-register variants, log every trial, require ≥100 costed forward outcomes per setup/arm, and apply expectancy, DSR, capture-ratio, and stability gates.
- The independent-direction and opposite-direction arms are measurements only. They must never affect the user-facing candidate until separately promoted through the forward gates.
- A future event-text branch may ingest only pre-approved, timestamped official sources (for example RBI/Budget releases). News text is untrusted data; unavailable or late text must not be substituted with model memory or web folklore.
- Proposed offline subagents: (1) Evidence Scout grades new sources; (2) NIFTY Event Analyst interprets official RBI/Budget/election text as context; (3) Options Structure Analyst runs obfuscated raw-chain pattern experiments; (4) Skeptical Reviewer audits leakage, costs, stale constants, and tiny samples; (5) Experiment Judge compares frozen variants and never proposes trades.
- These agents must work independently and produce auditable reports. Do not run live conversational debate: controlled evidence shows persuasive-error propagation and worse consensus accuracy. One harness agent remains the live filter.
- Offline strategy discovery may let an LLM propose falsifiable feature ideas, but only a fixed deterministic DSL/evaluator may execute them; data splits, costs, gates, and trial counts are immutable within a study.
- Prompt optimization remains batch-based and human-approved. The EvolveTrade/self-evolving-prompt line is a research lead only; no agent may rewrite `system_v1.txt` from one trade or auto-apply a proposal.

## Paper order engine and Zerodha Kite (added 24-Sep-2026)

- `python -m trading_bot.paper run` simulates orders for agent-harness decisions. `agent_brain record` writes each LONG decision atomically to `data/paper-inbox/<decision_id>.json` (with lot size, expiry, and VIX from the latest market row); the engine moves processed files to `data/paper-inbox/processed/`. `paper status` shows today's book; `paper report` shows all-time P&L, win rate, and per-day net; `paper dashboard` writes a self-contained `data/paper-dashboard.html` (no external resources) and opens it.
- The engine keeps its own DuckDB file, `data/paper.duckdb` (table `paper_trade`, one row per decision, timestamps as IST ISO text), and opens it per operation. It never opens `data/trading_bot.duckdb`, because DuckDB allows only one read-write process and `agent_brain` holds that file during its Upstox fetch.
- Fills: limit buy at the agent's `entry_price`, filled at the Upstox top-of-book ask when ask ≤ limit, cancelled after 10 minutes or at 15:15. Exits: stop at the bid when bid ≤ stop; target at the target price when bid ≥ target; square-off at the bid at 15:20. MAE/MFE are tracked from the bid at 5-second polls, not ticks.
- Paper-engine failure mode (observed live 25-Sep-2026): ingesting a decision triggers a Kite `GET /instruments/NFO` fetch; an uncaught transport error there (e.g. `ConnectionResetError`) terminates `paper run`. Unconsumed inbox JSON files survive the crash and are re-ingested on restart, so no decision is lost — restart the engine and verify pickup with `paper status`. A resilience fix (catch-and-retry around the fetch) is outstanding.
- `agent_brain context` on Upstox transport failure returns `fetch_status: "FETCH_FAILED:<error>"` and echoes the previous cycle's payload unchanged (same `meta.ts_ist`). Retry once; decide only on a fresh `OK` payload.
- Agent-harness paper risk (user-set 24-Sep-2026): ₹10,000 per trade, halved when India VIX > 16 or unknown; lots sized by the engine; ₹20,000 daily paper-loss stop; one pending/open position at a time. These apply to the `/nifty-agent-advice` path only; the `/nifty-advice` engine keeps its own rules above.
- Kite Connect (`trading_bot/kite`) is used only for calculations: NFO instrument lookup (Upstox strike/expiry → Kite `tradingsymbol`, lot size cross-checked), `POST /margins/orders`, `GET /user/margins/equity`, and `POST /charges/orders` for exact round-trip charges. `KiteClient` enforces an endpoint allowlist and refuses `/orders` and `/gtt`. If Kite is unavailable, charges fall back to the local `CostConfig` model (flagged `LOCAL_MODEL`). Margin shortfall on the real account is noted (`REAL_ACCOUNT_WOULD_LACK_MARGIN`) but does not block a paper trade.
- Kite auth: `KITE_API_KEY`/`KITE_API_SECRET` in `.env`; `python -m trading_bot.kite login` performs the daily OAuth login (redirect `http://127.0.0.1`; macOS denies port 80 to non-root, so paste the redirected URL) and writes `KITE_ACCESS_TOKEN` to `.env`. Tokens expire about 06:00 IST daily.

## DuckDB storage

- `DATABASE.md` is the canonical schema. `trading_bot.storage` initializes exactly three tables in `data/trading_bot.duckdb`: `market_data`, `model_advice`, and `trade_feedback`. DuckDB/WAL and all `data/` runtime artifacts are gitignored. Dependency is pinned to `duckdb==1.4.1`.
- `market_data` is keyed by IST observation minute and upserts the same minute. It stores exact capture/bar times, raw audit bars, resolved instruments/lot, features, chain window, health ages, daily P&L/calibration state, all gate reasons/warnings, and the serialized shadow candidate.
- `model_advice` uses the sole generated ID `advice_id`, preserves exact prompt/snapshot input, byte-exact raw attempts including malformed output, validated/demoted output, prompt version/hash, latency, validation events, and fallback reason. Later feedback never rewrites advice.
- `trade_feedback` is keyed by `(advice_id, evaluation_mode)`: one `USER` actual-fills row and one `SHADOW_30M` modeled-outcome row coexist per advice, each immutable once stored (legacy single-key databases are migrated in place on open, preserving every row). It labels the REST excursion source as `OPTION_1M_LTP_PROXY`.
- No fourth table is used. Harness requests are atomic JSON files under `data/agent-requests/`; prompt-analysis proposals are atomic JSON files under `data/prompt-proposals/`. Both live outside the database and contain no credentials.

## Feedback, outcomes, and evaluation

- Feedback CLI: `.venv/bin/python -m trading_bot.feedback` with `record-not-taken`, `record-trade`, `settle-pending`, `recent-advice`, and `report`. `recent-advice` lists the latest advice with already-recorded `USER`/`SHADOW_30M` results and Python-derived P&L echoes, and backs the natural-language `/trade-result` flow.
- Automated shadow outcomes use a fixed 30-minute horizon plus two-minute publication grace. Only fully completed post-entry one-minute option candles are used. If stop and target occur in one candle, the result is conservatively `STOP_HIT_AMBIGUOUS`; event-candle movement after modeled exit is excluded.
- Settlement/API failures write no terminal `MISSING_DATA` record; they remain pending and retryable. The proxy is not represented as tick-mid accuracy.
- Daily loss uses only cost-complete `USER` trades exited on that IST date. Any incomplete matching user trade makes daily P&L unavailable and blocks new candidates.
- After at least 50 objectively winning, cost-complete outcomes for one action, stops switch to winners' p90 MAE and targets to median MFE. Before that, OR-width levels are explicitly provisional. Graduation still requires at least 100 costed outcomes.
- Reports derive gross P&L, full current costs, net P&L, objective wins, expectancy, MAE/MFE, capture ratio, grouped results, and a trial-count-adjusted deflated Sharpe ratio. Graduation requires ≥100 records, positive cost-inclusive expectancy, DSR >0.95, and capture ratio ≥0.70; unavailable metrics block graduation.

## Prompt-improvement workflow

- Analysis prompt: `trading_bot/prompts/analysis_v1.txt`, version `analysis-v1`, SHA-256 `625a8f0079571e8c9423f0579298a63e533d011a941e7ba1dbcea0874eee96eb`.
- `.venv/bin/python -m trading_bot.prompt_analysis` runs only with 100–200 cost-complete forward cases. Below 100 it skips without loading model credentials.
- User notes are untrusted quoted data. Proposals must cite repeated patterns with valid advice IDs and exact current production-prompt text.
- Valid proposals are written with status `PENDING_HUMAN_REVIEW`. The tool has no approval/apply command and never edits the production prompt; human approval remains mandatory.

## Verification

- Environment: `python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt`.
- Full offline gate: `.venv/bin/python -m unittest discover -s tests -v` (**445 tests**) and `.venv/bin/python -m compileall -q trading_bot tests`.
- CLI help gates: modules `trading_bot.upstox`, `trading_bot.collector`, `trading_bot.agent_tool`, `trading_bot.advisory`, `trading_bot.feedback`, and `trading_bot.prompt_analysis`.
- Devin discovers `/nifty-advice` from `.devin/skills/nifty-advice` and `/trade-result` from `.devin/skills/trade-result`.
- Bounded live Upstox and harness validation passed on 17-Sep-2026: concrete expiry `2026-09-22`, dynamic lot 65, nine-row chain window, historical baselines, features, tick-valid candidate levels, DuckDB write, immediate 2,708-byte snapshot, and `agent_tool prepare` without any model API key. The after-hours request correctly returned engine-owned `NO_TRADE` with the shadow boundary.

## Remaining evidence/configuration gates

- Run `/nifty-advice` during market hours when an eligible candidate exists to validate the first real harness-model `READY → submit → model_advice` cycle; the after-hours engine-owned `NO_TRADE` path is already live-verified.
- Run the continuous collector through a complete live market session to validate minute publication timing, opening-straddle capture, and real-time staleness thresholds.
- IV percentile remains unavailable until 252 completed prior-day ATM-IV observations accumulate.
- MAE/MFE uses a conservative one-minute option-LTP proxy in the REST pilot; true tick-mid excursions require a future WebSocket phase.
- No performance claim or actionable alert is allowed until the forward graduation gates pass. All 2026 market, tax, fee, lot, and calendar constants must be re-verified when they change and before any future live-execution phase.

## Explicit Kite autopilot (03-Oct-2026)

- User authorized building full automation with Kite, not running it now. Agent decisions remain independent via `agent_brain`; `autopilot` schedules a signed-in Codex CLI without per-trade approval. Default mode is paper. No other broker or cloud deployment was added.
- Live startup requires `--mode live --enable-live --config`, matching account, daily credentials, fixed registered outbound IP, and explicit trade-risk/daily-loss/pilot-date settings. The example intentionally contains null activation inputs.
- Starting allocation is ₹10,000 total plus immutable completed bot net P&L, bounded by cash and commitments. Profits can be reused; unrealized gains or deposits cannot raise the allocation. Separate loss and lot ceilings remain enforced.
- Isolated live SQLite journal/inbox, IOC limit buys, confirmed partial-fill protection via broker DAY SL sell limits, single-sell target/exit modifications, timeout tag reconciliation and sticky fail-closed entry halts. Base `KiteClient` remains calculation-only.
- Full startup/recovery/hosting workflow and limitations: `docs/kite-live.md`. Stop limits can gap and remain unfilled; no guaranteed loss cap, atomic entry+stop, overnight protection, profitability or live-readiness claim.

## Private Kite dashboard (03-Oct-2026)

- `python -m trading_bot.live_web` serves a lightweight private mobile page behind HTTPS; `--demo` is a credential-free loopback preview. No deployment, real credentials or live startup was performed.
- Official Kite login returns to registered `/kite/callback`; server-side exchange verifies the account and atomically writes a private `0600` daily token file. The runner reloads this file each tick. Browser sessions and single-use callback state are private and expire.
- Five-second page polling reads persisted broker facts; broker reads refresh at most every 15 seconds and expire after 30 seconds. Cash snapshots are bound to the daily login generation. The same capital calculation powers execution and dashboard; unverified cash/costs remain unknown.
- Stop new trades creates `data/live/PAUSE`; existing protection/exits continue. No web order-write, start or resume route exists. HTTPS origin/password, registered callback, private server secrets and hosting remain operator setup. See `docs/kite-dashboard.md`.
