# 04 — Chinese Corpus Addendum (STE)

## Terms and abbreviations

- **engine** — the deterministic Python process. It computes all numbers and owns all risk limits.
- **Evidence tiers:** A = peer-reviewed. B = corroborated preprint / industry. C = blog or anecdote.
- **CN** — Chinese-language corpus or sources. **EN** — English-language corpus.
- **LLM** — large language model. **CoT** — chain-of-thought. **RAG** — retrieval-augmented generation.
- **NIFTY / BANKNIFTY** — NSE index names. **SEBI** — the Indian regulator. **CSRC** — the Chinese
  regulator. **RA** — SEBI Research Analyst regulations. **NSE** — the Indian exchange.
- **OHLCV** — open, high, low, close, volume bars. **RankIC** — rank information coefficient (a
  forecast-quality score). **TSFM** — time-series foundation model.
- **STT** — Securities Transaction Tax. **bps** — basis points (1 bp = 0.01%).
- **P&L / PnL** — profit and loss. **EOD** — end of day. **UI** — user interface.
- **SDK / REST / WS(wss) / HTTP** — broker API transports. **LoRA / GRPO** — fine-tuning methods.
- **OI** — open interest. **IV** — implied volatility. **PCR** — put-call ratio.
  **θ (theta) / Γ (gamma)** — option decay and convexity. **VWAP** — volume-weighted average price.
  **ATR** — average true range. **MAE / MFE** — maximum adverse / favorable excursion.
- **DSR** — deflated Sharpe ratio. **OOS** — out-of-sample.
- **Tags:** C01–C06 = CN source bundles. E-01–E-17 = edit-register rows. OR-xx = open risks in doc 01.
  FR-xx = feature rows in doc 01. FM-xx = failure modes in doc 01. T1–T8 = transports in doc 01.
  HR-xx = hard rules in doc 01. S-x = storage artifacts in doc 01. SH-01 = the shadow feature log.
- **Chinese phrases in quotes** (e.g., 待核实, 护栏桥) are verbatim source tokens. Keep them byte-exact.

**Status:** decision-grade delta. This document integrates C01–C06 (CN-lab papers/prompts, CN
open-source repos, CN prompt playbooks, DeepSeek-era practitioner playbooks, CN financial foundation
models, CN critiques/regulatory/failures). **This document adds and adjudicates. It restates nothing
already decided in docs 01/02/03, except where it proposes a change (flagged `→ EDIT doc/section`).**

**Tiering:** grade the CN corpus as: verified-repo prompts (B/C), practitioner playbooks (C),
state-media/police/regulator records (B-strong for *risk*, zero for *alpha*), one pre-regime live-uni
record (the HKU FX experiment, B), arXiv model claims (B-claims only). No CN source demonstrates
live-audited LLM trading alpha. The corpus's signal is **operational discipline and failure modes**,
not edge.

---

## What CN sources CONFIRM

| CN finding | Existing doc/section it reinforces | Strength of CN corroboration |
|---|---|---|
| LLM never in the tick loop; "slow LLM layer vs deterministic fast layer" (驱动层/执行层/事实层 three-tier) — ≥5 repos converge identically; the FinGPT forecaster runs weekly | 01 header canonical facts + §4 LLM-cadence floor; 02 §4 invocation, excluded table "LLM in tick loop" | **Strong** — independent cross-culture convergence (C02 #3/#5/#6/#13, FinGPT C01) |
| Engine computes / LLM narrates ("技术面不直接下结论，引擎算，LLM综合"; the ashare-agent 铁律 "数字必须来自脚本,不许口算") | 02 §2 authority partition ("engine = sole arbiter of numbers"); 02 §5 HARD RULE 1/2/4 | **Strong** — 5+ independent sources (C02, C03 §pattern-7, C04 P8) |
| No personas ("返角色设定" everywhere but zero ablation; the one condition-measured CN source strips the persona to one clause) | 02 §5 excluded "Expert personas" (R08 S12–S14) | **Moderate–strong** — confirms via folklore saturation + conformity of the single evidence-toned counterexample (C03 E4, pattern 6) |
| Verified-numbers-only grounding; anti-entity-confusion (ticker↔name↔currency); "flag discrepancy rather than invent" (the TradingAgents market_analyst tool-snapshot rule) | 02 §3.2 rule 3 (`data_conflict`) + §3.3.3 echo check | **Strong** — TradingAgents-CN spends the most prompt budget on exactly this (C01) |
| NO_TRADE as first-class, with anti-decisiveness wording ("do not manufacture a direction merely to appear decisive") | 02 §5 HARD RULE 1 (the verbatim same sentence, independently arrived at) | **Strong** — the TradingAgents research-manager prompt (C01) is the same rule, cross-culture |
| Broker SDK isolated from the LLM process; the order path behind a deterministic guardrail daemon ("护栏桥": the qmt-bridge/qmtcli/qmt-mcp cluster) | 01 T8 (order bucket untouched); 03 §5 (the bot never self-executes) | **Strong** — ≥4 repos + broker-QC practice (华泰联合二次校验, 国金 zero-tolerance tier) |
| Boot-time auth probe + loud failure before the session (the 4-step Tushare token cascade; the Upstox 03:30 analog) | 01 FM-03/T6 (re-auth + post-auth verify + fail loud by 09:05) | **Strong** — the same lesson, a different credential class (CN = points/quota rot) |
| Backtest contamination is fatal (利润幻影: LLM-agent alpha collapses outside the knowledge window; the S9 three-limits) | 02 §1.1 row "In-training-window backtests meaningless"; 02 §6.2; 03 §4.2 | **Strong** — independent academic + regulator-validated (C06 S16, #2/#3 enforcement) |
| Live LLM-trading P&L unproven-to-negative (media-audited user losses: −50%/mo, 9/10 next-day down; HKU live FX: benchmark rank decouples from P&L, DeepSeek/MiniMax large losses; 幻方/DeepSeek itself: "AGI不是用来炒股的") | 02 §1.1 population-scale record; 03 §3 expectancy honesty | **Strong** — the single best practitioner data point (DeepSeek's parent) is absent from the EN corpus |
| CSV/field-minimization beats verbose payloads (the 通达信 6-column export rule) | 02 §3.1 mixed envelope (R08 S19–S21) | Moderate — practitioner-side confirmation |
| Fine-grained forced-choice verbalization beats free-form hedge (the CFLUE/FinEval parse contracts; TradingAgents-CN separates 置信度 from 风险评分) | 02 §3.2 fixed schema/enum design | Moderate |
| Low-temp receipts for code/formula tasks (the CN practitioner recipe temp 0.3/top_p 0.85, formula-debug loop) | 02 §3.3.6 temperature pinning; 02 §4 generation settings | Moderate — same direction, same reason |
| max_tokens truncation eats the safety clause (CN field report: the 剔除ST exclusion was cut mid-code when max_tokens was small) | 02 §4 "max_tokens pinned small" — adds a failure instance: structural/safety fields must precede long free-text in field order | New instance of a known rule; worth adding one field-ordering sentence → 02 §3.2 |
| Deterministic fallback on LLM failure (TradingAgents-CN: 3 retries → generated decision stub, never crash; a tool-call counter caps loops at 3) | 02 §4 timeout/fallback = deterministic NO_TRADE; the 12s hard timeout | Strong — the same shape: "an API failure must become an explicit decision, never a hanging advisory" |
| Absolute price levels, no-null-with-omit-license, fixed 2-decimal precision (the TradingAgents trader prompt "never a percentage or a range"; StockAgent "determine the price yourself, quantity integer"; the 游资 template "所有价格保留2位") | 02 §5 HARD RULE 2 + §3.3.2 level sanity | Strong — three independent CN-lab sources converge |
| Debate topologies are a latency/cost trap, but *offline* weekly bull/bear transcript review is defensible (CN forks report stability gains on volatile assets, C-tier intraday) | 02 excluded table: "no in-session debate"; 02 §6.4 weekly critic | Partial — confirms the hot ban, adds one offline license |

---

## What CN sources ADD (prompt/interface)

Format of each item: **mechanism | origin | exact edit into doc 02 | expected benefit | risk**.
Each adjudication is explicit.

1. **Quarantine bucket vs confidence scores — RESOLVED: adopt the bucket, keep the score.**
   The 待核实/UNVERIFIED list (Kimi official agent: "无法核实的内容列入「待核实」并注明原因，严禁编造"; "missing ≠ 0";
   C03 E3, the C02 hot-money 必采清单 "[数据缺失: xxx]"). **→ EDIT 02 §3.2 output schema:** add
   `"unverified": []` — a string array. Each element quotes a fact the model wanted to use but could
   not source *from the snapshot*. Code rule → 02 §3.3 (new #9): if `unverified` is non-empty on a
   LONG_*, demote to NO_TRADE (quarantine is an admission of weak evidence); log it as an
   epistemic-gap event. Benefit: a third state between "fabricate" and "say nothing"; confidence stays
   a unidimensional label for the *direction call* only. Risk: the model parks hard cases in the
   bucket to dodge judgment — mitigated because bucket use forces NO_TRADE (there is no free
   optionality).
2. **事实/判断 inline tagging — ADAPTED (offline only).** The vcai 〖事实〗/〖判断〗 tags + the 55188
   fixed disclosure tokens ("这是基于当前数据的推测" / "数据有限，判断可能存在偏差"). **Hot path: REJECT** —
   the 25-word rationale / JSON-only contract has no room. The echo check (02 §3.3.3) already grounds
   hot output mechanically. **→ EDIT 02 §6, add §6.4 "offline/report outputs":** any human-readable
   prose the bot emits (pre-market brief, EOD review, weekly report) must carry the fixed disclosure
   tokens `[INFERENCE]` / `[DATA-LIMITED]` inline on any claim that is not verbatim from engine
   artifacts. Benefit: cheap epistemic hygiene on the surface that regulators and users actually read.
   Risk: token-spam habituation — cap it at 2 label types.
3. **Debate-judge "no-default-HOLD" clause vs our anti-deliberation — RESOLVED: reject for the hot
   path; import as the *offline*-review inversion.** The CN judge prompt ("choose HOLD only when
   specific arguments strongly support it, never as the fallback when everything seems fine") solves a
   real problem (judge agents collapse into muddy agreement, 和稀泥), but **our asymmetry is the
   opposite**: NO_TRADE costs ~0; a manufactured LONG costs ≥59bps plus the toll (03 §2). The
   HOLD-default is *correct* for an advisory with engine-owned risk. The CN clause would import a
   manufactured-direction bias. **→ EDIT 02 §5 excluded-table row (no change to rule 1); → EDIT 02
   §6.4:** the *weekly* offline critic must justify "keep running setup X unchanged" with fresh
   positive evidence. The status-quo clause lives on the *do-nothing* side of the playbook, not the
   action side. Benefit: kills sycophantic playbook inertia without disturbing hot-path conservatism.
   Risk: none material.
4. **Investment-constitution banned-vocabulary block — ADOPT (as a compliance output contract,
   distinct from NO_TRADE).** The dsh AGENTS.md 投资宪法 verbatim (no 建议买入/卖出/目标价/必涨 wording;
   source+date on every claim; numbers only from executed scripts, never mental math; ask before any
   write). **→ EDIT 02 §5 system prompt: add a new HARD RULE 7 block** (words banned in any free-text
   field: "guaranteed", "sure", "must rise/fall", target-price-as-fact, size/leverage advice);
   **→ EDIT 03 §3.3:** a user-facing claim-language section — all bot prose and app copy enforce the
   same banned list (see §4 below). Benefit: one banned-vocab block covers both parse hygiene and
   regulatory optics. Risk: over-cautious phrasing reads as uselessness; bounded by keeping the JSON
   advisory itself intact.
5. **Pre-mortem adversarial pass vs cross-model vote — RESOLVED: the cross-model vote wins hot
   escalations; the pre-mortem wins the human surface.** F5 adjudication 3 keeps the independent
   cross-model vote for live escalations. Independence is the whole value; a same-model attack shares
   biases (C04's own credibility section warns that model-generated critique self-agrees). The CN
   contribution (C04 P4) is **pre-committed stops/targets stated before the critique**, plus
   attack-the-thesis as a *human-facing* prompt. **→ KEEP 02 §4 escalation = the cross-model vote,
   unchanged; → EDIT 03 §5, add §5.4 "pre-trade pre-mortem ritual":** the daily playbook and any
   user-initiated check require the user to state entry/stop/target in absolute terms before the bot
   critiques. The bot attacks from the tape-structure / vol-regime / risk-arithmetic axes (the CN
   3-axis enum). Benefit: commits the human *before* the model speaks (anti-anchoring); gives user
   value at zero hot-path cost. Risk: pseudo-adversarial theater — flagged as C-tier practice, not
   evidence.
6. **Misreading-traps field — ADOPTED as a NO_TRADE-context field only.** CNBlogs E2: "list 2–3 traps
   a retail reader would fall into with this exact data." **→ EDIT 02 §3.2:** add a new optional
   field `"misread_trap": "≤12 words"`, populated **only when action = NO_TRADE on a pre-filtered
   candidate**. These are the moments when a scalper is most likely to over-read a dead setup ("chop:
   trend read is hindsight"; "expiry pin: breakout chase is bait"). Benefit: converts a denial into
   teaching; the advisory-safety surface (03 §3.3) gains a hook. Risk: the LLM writes plausible-wrong
   didactics — bounded by the word cap plus snapshot-only grounding (extend the echo check to this
   field).
7. **Agent-permission prompting — ADOPT as a new ops-safety section.** The jxxy rules verbatim
   (unclosed-bar ban, write-tool firewall during backtest, `shift(1)` no-lookahead, "backtest ≠
   forecast" phrasing). **→ EDIT 02, add §4.1 "Agent-permission rules (offline tooling)":** any agent
   scaffold that touches our data/backtest path runs under these constraints: read-only on live
   account state; no order/write tools in analysis or backtest context; signals shifted `shift(1)`;
   unclosed bars excluded; backtest results never phrased as forward prediction. Benefit: closes a
   whole attack surface (tool permissions) that doc 02 does not cover. Risk: none — pure constraint
   text.
8. **Label injection for offline rationale generation — ADOPT.** The FinGPT Forecaster PROMPT_END
   ("assume your prediction is X, now justify it; the analysis must be inferred, not the premise").
   **→ EDIT 02 §6.4:** a weekly offline job feeds engine-decided outcomes back as assumed labels, and
   the LLM writes audit rationales; **never at inference**. Benefit: a cheap rationale corpus for the
   critic loop, and training data if we fine-tune (ties to the dual-reward item in §5). Risk: post-hoc
   storytelling mistaken for causality — store it in an S-7-style shadow namespace; never show it to
   users as live advice.
9. **The CVRF belief block as a weekly offline loop — ADOPT as a gated experiment.** FinCon: a
   1–2-sentence "investment belief" block, updated on PnL-triggered self-reflection, injected into the
   system prompt. **→ EDIT 02 §7 open questions (#5 merged):** pilot a `market_beliefs` block (≤2
   sentences, weekly cadence, derived from S-8 advice-log outcomes by the offline critic), prepended
   to the system prompt. A/B it against the frozen prompt via the 02 §6.1 prompt-hash log. Promote it
   only if the forward shadow shows lift with no hallucination-rate regression (the §6.3 masked-value
   audit stays unchanged, run first). Benefit: gradient-free verbal reinforcement learning with no
   hot-path cost. Risk: a self-modifying prompt is a new untracked drift vector — prompt-hash gating
   is mandatory.
10. **ATLAS prompt self-optimization guardrails — ADOPT the guardrail shape, not the optimizer yet.**
    Adaptive-OPRO: the optimizer may edit only the instruction block; placeholders and the output
    schema stay frozen; each change logs (diagnosis, diff, expected impact); scoring over K=5-session
    windows. **→ EDIT 02 §6.3:** add a release-gate row. Any system-prompt edit must pass:
    a template-preservation check (schema bytes identical), a change-log entry, a masked-value audit
    re-run, and a forward-window comparison vs the previous hash. Benefit: docs 02/03 had *no*
    prompt-evolution governance; the CN+Greek labs wrote it. Risk: ROI-shaped scoring
    (s = clip(50+250·ROI)) tempts a return to contaminated backtests — our scoring window is the
    forward shadow only.

---

## What CN sources ADD (data/cadence) — adopt/adapt/reject per doc 01

| Item | Verdict → edit target | Notes |
|---|---|---|
| **盘前/盘中/盘后 two-speed loop** (the S2/S4 CN retail cadence: pre-open brief → human + pre-generated deterministic alerts intraday (LLM absent) → post-close screen/plan → weekly review) | **ADAPT → 01 §4 (add an "LR-01 long-run cadence" paragraph) + 02 §6.4** | Our 60s gated advisory stays (that *is* the product segment). CN field evidence says the demonstrated-useful LLM surfaces are pre-open and post-close. We add: an 08:45 pre-open brief job (one LLM call: SGX/GIFT-NIFTY proxy, USDINR, overnight risk, a trinary day-bias → the human approves the playbook) and a 15:45 review job (a closed-trade 4-question protocol, incl. "name the cognitive bias"). The weekly belief-block job rides on 02 §6.4. The CN evidence is retail-A-share (T+1, no options) — do NOT demote our intraday loop on its strength; mark it as corroboration for the two-speed *hot/cold* split only. |
| **Boot-time auth/effective-permission probe cascade** (TradingAgents-CN 步骤1→4: DB token → .env token → probe call → auto-degrade; it also treats quota/`429`-class denial as an auth failure) | **ADOPT → 01 FM-03 + FM-07 edit** | Extend FM-03's "one cheap authed REST call" into an ordered probe: (1) token from store → (2) authenticated cheap probe → (3) treat inexplicable 429/quota errors as credential-rot, escalate loudly → (4) explicit degrade path (feature-free warmup only → NO_TRADE day announced by 09:05 per HR-13). The CN version exists because points/tokens rot silently. That is the same failure ontology as our 03:30 death. |
| **Missing-data contract** (the 必采清单 with a required "[数据缺失: xx]" annotation; Kimi "missing ≠ 0") | **ADOPT → 01 §4 payload spec + generalize the FR-28 note** | Rule: every FR/P-group field has an explicit missing sentinel. Serialize a field that is absent from a source as `null`/`[DATA_MISSING]` — never 0. Never carry the last value forward unless flagged `carried`. This generalizes FR-28's "unavailable-not-0" to the whole payload. It pairs with the 02 §3.2 `unverified` bucket and the FM-04/05 staleness gates. |
| **Per-source staleness/latency table as a first-class design input** (dsh-quant-workbench publishes per-feed lag: free HTTP 3–5s, Yahoo 15min) | **ADOPT → 01 T1–T8 table: add an "expected staleness" column** | ltpc ≈ tick; full ≈ tick; chain REST = 30–60s by design (CR-2); historical candles = settled bars only; CDN master = daily. This is a spec-honesty edit, not an architecture change. OR-06 already carries the risk. |
| **AkShare/Tushare-class free-data reality check (3–5s lag, silent fallback defaults, price=10 poisoning PE/PB)** | **ADOPT as a design constraint + REJECT the fallback** | Confirms the Upstox-only single paid source as correct. **→ EDIT 01 FM-04/FM-08 + new FM-14:** "silent-default poisoning" — recompute every derived value (PCR, IV aggregates, walls) from raw primitives and range-validate it. If a source returns implausible constants or a hard-coded default, trip the same gate as staleness. Policy: no free/scraped HTTP feed (the NSE scrape stays T7-optional) may ever sit on any advisory-critical path. This was CN's #1 documented pitfall class; we inherit the guard, not the bug. |
| Intraday WebSocket quote push every 3s (QuantTradingSystem) | **REJECT** | Subsumed by the wss-streaming T1/T2 at push rate; a 3s poll is strictly worse. |
| 龙虎榜/游资/北向 money-flow analyst agents | **REJECT** | A-share microstructure; no NIFTY-options analog at our horizon; a pale shadow of the FR-13 hedge-flow already in doc 01. |

---

## What CN sources ADD (economics/risk) — new guardrails for doc 03

1. **Regulatory liability for AI-generated market content — ADOPT. → EDIT 03 §3.3 (allowed claim
   language) + §7 risks.** CSRC 2026 precedents: ¥200k–450k fines + a 5-year market ban for
   AI-generated/rewritten false securities info; the "AI生成，我没核实" ("the AI wrote it, I did not
   check") defense is explicitly rejected. Assume the SEBI analog (RA regs + the IT Act) follows. New
   guardrails: (a) every bot prose output carries source+date and passes the banned-vocab block
   (§2.4 above); (b) **no-guarantee wording is absolute** — 稳赚不赔-class phrasing ("sure-shot",
   "guaranteed returns", "X% monthly") is the exact enforcement trigger pattern on both sides;
   (c) marketing compares only forward-shadow, net-of-cost, n-stated results (02 §6.3 already);
   (d) never frame bot output as sharing market "news" — advisory only, no republishing of scraped
   headlines (the CN newsroom test: self-media citations are toxic; grounding ≠ credibility).
2. **Fraud-economy findings — ADOPT as user-protection positioning. → EDIT 03 §3.3 + onboarding.**
   The CN fraud stack (虚拟盘 fake balances, tampered backtests 后台篡改回测数据, AI换脸 analyst videos,
   "AI荐股" upsell funnels ¥288→¥998, the `100万 AI portfolio` that never reports results) is the
   reputational neighborhood. Bake these anti-patterns into onboarding/disclosure: independently
   re-computable results only (no screenshots, no "proprietary backtest"); the explicit statement
   "the bot never executes, never touches funds"; the advisory-vs-returns framing per 03 §3.3. The
   CSRC documenting backtest-tampering as a standard scam component validates our §4.2
   mandatory-independent-recompute rule.
3. **Hallucinated portfolio-state failures — ADOPT, the highest-priority CN risk. → EDIT 02 §3.3.3 +
   the 01 P8 account-block provenance.** The 李超 case: the model invented PDF holdings, mixed other
   users' symbols into his portfolio, miscounted trading days (holidays/suspensions), conflated A/H
   dual listings — and persisted after challenge. Our exact analogs: NIFTY vs BANKNIFTY chains,
   weekly vs monthly expiry, Tuesday-rollover confusion, strike drift. Guards: (a) the engine alone
   serializes the `account`/positions block; the LLM never asserts positions from chat history;
   (b) extend the echo check: any strike/expiry/instrument name in model output must string-match
   snapshot values; mismatches = hallucination events (already §3.3.3 — extend the enum);
   (c) calendar facts (weekly-vs-monthly, holidays) come from regime_flags, and the prompt gains the
   rule: "Do not assert dates, expiries, or positions not present in the snapshot" (→ EDIT 02 §5,
   into the HARD RULE 1 block).
4. **Stale-data kill rules — ADOPT the display-side guard. → EDIT 03 §5.1 + a 02 §3.3.4 note.** The
   Larry case: morning advice computed from the prior close was stale and worthless by the session;
   the UI had no kill. We already force NO_TRADE at decision time (02 §3.3.4). Add the missing half:
   **advisory display expires**. The UI must tombstone any advisory older than ~90s, or any advisory
   whose snapshot_age breached 2s before the human acted. Do not auto-surface "yesterday's plan" the
   next morning without regeneration. The CN muted-vs-explained lesson: silence is fine; stale
   confidence is the harm.
5. **Broker-QC hallucination-tolerance tiering — ADOPT as an architecture ratification. → no edit
   (cites into the 03 §7 risk table).** The 国金 4-dim framework: execution/regulatory surfaces =
   zero-tolerance, human-reviewed (matches T8/02-§2); internal tooling = medium tolerance with a
   multi-model cross-check. 华泰: hallucination is structural (达摩克利斯之剑), patched by a source
   whitelist + 二次校验 + trace-back. We already satisfy this; cite it as industry-benchmark
   corroboration in 03 §7.
6. **Issuer gaming of LLM sentiment (算法迎合) — ADOPT as an input-hygiene clause. → EDIT 01 §1 note +
   02 §3.1.** If/when we add any text/news channel: a source whitelist is mandatory. Issuers write
   strategically to game sentiment parsers. Treat unstructured text as *poisoned-by-design*. No
   current edit to the feature register (no news feature exists); the clause pre-registers the guard.

### CN→NIFTY failure-mode translation (from C06; informs the 03 §7 wording)

| CN-documented failure | Maps to us as | Guard now in place |
|---|---|---|
| Hallucinated holdings / mixed symbols / miscounted trading days | Strike/expiry mixup, weekly-vs-monthly expiry confusion, NIFTY/BANKNIFTY chain crossover | 02 rule 3 + new rules 7/8; the echo check as a Stage-gate |
| Intraday advice built on the prior close (stale-context catastrophe) | Advisory shown late / the playbook carried to the next session | 02 §3.3.4 snapshot_age gate + §4.4 display tombstone (NEW) |
| 虚拟盘/edited-balance Ponzis, tampered backtests | The product-trust surface: any result we publish must be independently re-computable from logged artifacts | 03 §6.1 logging spec already qualifies; disclosure copy per §4.2 above |
| RAG grounding on promotional self-media | Any future text/news channel default-poisons sentiment inputs | The §4.6 whitelist pre-registration |
| Benchmark-rank ≠ P&L (HKU live FX) | Model-swap temptations ("the new model is smarter") | 02 §6.3 release gates; the finance-numerics degradation note is already in §1.1 |
| T+1/涨跌停-specific retail loss patterns | **Do not map** — NIFTY options are T+0 derivatives; the CN-specific loss mechanics (limit-down lockups) have no analog; our equivalent is theta/gamma acceleration, already in 01 FR-02/FR-07 | — |

---

## Models — stack seats verdict

- **Kronos (Tsinghua-affiliated, AAAI-2026, 38.8k★): the only CN artifact that earns an experiment
  seat.** A market-agnostic BSQ-tokenized OHLCV forecaster (45 exchanges, 12B+ candles), with a
  claimed +93% RankIC over the best TSFM — the claims are arXiv-only. **Experiment protocol
  (→ referenced from 01 §7 / the OR-list as an OR-16 candidate; the evaluation gates from 03 §4.2
  apply):**
  1. Run shadow-only under the S-7 namespace.
  2. Predict NIFTY 1-min/5-min returns, horizon 15–60 min, from a 512-bar context.
  3. **Audit the cutoff first.** Training-window contamination is our corpus's highest-confidence
     finding. Inspect Kronos's exchange/date coverage for NSE overlap. On any overlap, evaluate
     strictly post-cutoff, or discard.
  4. Compare vs trivial baselines (VWAP-side momentum, ATR-band, FR-15/16 triggers) on RankIC plus
     cost-aware advisory-P&L terms.
  5. Promote only via the 03 §4.2 gates (DSR>0.95, OOS decay ≥0.5).
  6. If it is ever armed, its output is a bounded prior feature that the *engine* fuses — never a
     prompt-visible verdict.

  Expected result: it unseats nothing on day 1. Worst case: another SH-01.
- **No CN LLM displaces the frontier general-model seat.** Fin-R1 (finance-tuned 7B): avg 75.2 <
  DeepSeek-R1 78.2. This is consistent with 02 §1: small domain-tuned models approach the frontier
  but do not beat it (CF). DianJin-R1/Fin-o1/FinGPT carry CN-market and CN-compliance semantics
  (CCC, T+1 assumptions, PRC licensing vocabulary) that would *actively mislead* a SEBI/NSE product
  (C05 transferability). The HKU live experiment: reasoning rank ≠ trading P&L; DeepSeek-class models
  lost real FX money. We keep the frontier-class general model plus tooling (doc 02's thesis),
  uncontradicted.
- **Borrowable evaluation conventions (→ EDIT 02 §6, adopted into the offline harness):** the CFLUE
  two-line contract `答案：/解析：` (EN: `ANSWER:` line 1, `RATIONALE:` line 2) for any model-graded
  eval prompt; the FinEval CoT-with-parseable-tail pattern (`let's think step by step… so the answer
  is X` → tail-extracted) for offline reasoning evals; and the **Fin-R1/DianJin dual-reward (format +
  accuracy)** GRPO convention as the design spec, if 02 §7 question 4 (cheap open-weight swap →
  fine-tuning) ever graduates to training.
- **FinZero** (chart-image reasoning over rendered K-lines, +13.5% in the high-confidence subgroup vs
  GPT-4o): log it as a parked hypothesis only (02 §7 open-list-adjacent). No chart-image channel
  exists in the stack to feed it. Its confidence-conditioned claim is exactly the pattern our
  calibration gate (02 §6.2 component 4) would have to re-measure on NIFTY renders.
- **The FinGPT sentiment LoRA family** is the narrow-task exception already encoded in 02 §1.2
  ("classification works on pre-digested inputs"): FPB weighted-F1 0.882 > GPT-4 0.833, at
  classification-width tasks only. Verdict for us: if we ever add a headline/sentiment channel
  (subject to the §4.6 whitelist), a small fine-tuned classifier is the *correct* component class —
  and a CN-trained one is the *wrong* instance (CN tokenization + PRC-regulatory priors). Train ours
  on Indian-market text instead.

---

## Revised production prompt — minimal diff on 02 §5

**Diff summary (3 additions, 0 deletions):** +HARD RULE 7 (banned vocabulary + no asserted
positions/dates outside the snapshot); +HARD RULE 8 (missing/unverified → the `unverified` bucket,
never fill from memory); +output fields `unverified` (schema) and `misread_trap` (NO_TRADE-only).
Everything else stays byte-identical to 02 §5.

```
SYSTEM
You convert machine-generated NIFTY options snapshots into one trade
recommendation for a human scalper. You never compute numbers; every
number you output must appear in the snapshot. Domain context — NIFTY
index options, intraday scalping, INR premiums, IST timestamps —
is given by the field names; answer for this domain only.
                                            [unchanged — primed domain, no persona]

HARD RULES (also enforced in code):
1. action ∈ {LONG_CALL, LONG_PUT, NO_TRADE}. When signals are mixed,
   data is stale/missing, or reward-to-risk looks marginal, answer
   NO_TRADE. Do not manufacture a direction to appear decisive.
                                            [unchanged — anti-decisiveness (both sides agree)]
2. entry_level, stop_loss, target_1, strike are absolute INR levels.
   Never percentages, never ranges. Omit a level you cannot justify.
3. Quote snapshot values verbatim. If snapshot fields conflict, set
   data_conflict=true instead of reconciling silently.
4. Do not output any size or max-loss figure. Grade the setup as
   setup_quality A/B/C; sizing is computed by the caller.
5. rationale ≤ 25 words; invalidation = one sentence in price terms.
6. No reasoning chain in the response. Output the JSON object only.
7. Banned vocabulary in every text field: no "guaranteed", "sure",
   "must rise/fall", "target price", size or leverage advice. Never
   assert positions, dates, expiries, or strikes not present in this
   snapshot.                                   [NEW — CN 投资宪法 banned-vocab block
                                                (C04 P8) + 李超-portfolio-hallucination guard
                                                (C06 #6): portfolio-state must be engine-serialized]
8. If a fact you want to cite is not in the snapshot, or a needed
   field is null/[DATA_MISSING], list it in "unverified" with a
   one-line reason — never fill from memory, prior turns, or
   general knowledge. Missing is not zero.
                                            [NEW — CN 待核实 quarantine + missing≠0
                                             (C03 E3, C02 必采清单); enforced: unverified
                                             on LONG_* → code demotes to NO_TRADE]

OUTPUT FIELDS (beyond the base contract):
- "misread_trap": ≤12 words, ONLY when action=NO_TRADE on a live
  pre-filtered candidate: the single most likely way a scalper would
  over-read this tape right now. Omit otherwise.
                                            [NEW — CNBlogs E2 misreading-traps (C03)]

USER (per call)                        [unchanged]
<trigger: periodic|event:TYPE>
Snapshot (JSON envelope with CSV blocks — meta now may carry null
fields; any null = [DATA_MISSING], see rule 8):
<meta / regime_flags / spot_1m_csv / chain_csv / indicators_csv /
 events_csv / account — exactly per 01 §4 payload spec>
Respond with ONLY the JSON object of the output contract.
```

**Explicitly NOT added** (with reasons): no default-HOLD clause (adjudication §2.3 — harmful here);
no `confidence`/risk-score split (TradingAgents-CN separates 置信度/风险评分 — ours already separates
risk to the engine; one scalar avoids false precision; 02 §3.2 semantics unchanged); no
assisted-prefix priming (an open-weight-only trick, E4); no persona.

---

## Updated banned/folklore list — CN-specific additions (→ merge into the 02 §5 excluded table / the 03 folklore register)

1. **重仓-forcing personas** — "强势市场必须给出60%以上重仓建议 / 拒绝中庸建议" (the 游资 template, C03
   E5) and all "顶级游资/牛散" persona packs (the 7-persona pantheon, C04 S5). Conviction-forcing +
   persona = the folklore the evidence punishes (~30pt persona cost, forced-conviction degradation).
   **Banned.**
2. **Fabricated "winning prompt" packs** — the NoF1 "复原版" system prompts, the Alpha-Arena "DeepSeek
   +130%" articles, the ¥288 AI荐股软件 funnels, the "一天赚20万" short videos. These are
   blogger-reconstructed prompts attributed to leaderboard PnL; the 北京日报/21财经 investigations +
   Zhihu debunk them all. **Banned as a source class: journalism/QQ-group prompt packs.**
3. **Price-prediction demand blocks** — the TradingAgents-CN "必须提供具体目标价位，不允许null /
   绝对不允许说无法确定" is the *inverse* of 02 rule 2's omit-license. CN repos adopted it to fight
   parse-nulls, at the cost of fake precision. **Our omit-a-level-you-cannot-justify rule stays. The
   CN anti-null motif is banned.**
4. **NoF1 / trading-competition folklore generally** — treat any mechanism sourced to a competition
   leaderboard ("Sharpe-rollback self-correction", risk-budget numbers from the reverse-engineered
   prompt) as fiction until independently ablated. The attribution is unverifiable.
5. **"AI 炒股" guarantee language** — 稳赚不赔 / "年化246.9%" / monthly-150% claims. These are not just
   false; they are *the* regulator red-flag lexicon (CSRC scan patterns; the SEBI ads-code analog).
   Banned from all product copy per §4.1.
6. **L1–L4 temperature dials for adversarial agents** (junxinzhang) — no ablation; CN-folklore
   adjacent. Banned pending evidence.
7. **公告/舆情 persona-analysts as signal inputs** — CN retail sentiment prompting is equity/T+1
   centric, with no options-Greeks corpus. Importing the *frame* buys us nothing. (No Nordmark-style
   options sentiment prompting exists on the CN side either — a genuine gap, not a lever to pull.)

---

## Open risks from the CN corpus — ranked

1. **Portfolio-state hallucination (blocking-adjacent).** 李超-class failures (invented holdings,
   conflated instruments, miscounted sessions) are persistent and confident, and they survive user
   challenge. The NIFTY analogs are *worse* (weekly-vs-monthly expiries, NIFTY/BANKNIFTY, the Tuesday
   rollover). Mitigation lives in the 02 §3.3 echo check + rules 7/8 above. Residual risk: make
   hallucination events a Stage-gate metric (03 §6), not a log curiosity.
2. **AI-content regulatory liability.** The CSRC now fines AI-generated false market info, and
   rejects the "the AI wrote it" defense. Unlicensed AI 荐股 is prosecuted regardless of tech framing.
   Our SEBI-RA exposure plus the marketing language are the controllable surface (§4.1). The
   uncontrollable part: regime precedent drift.
3. **Self-modifying prompt loop drift** (the CVRF/ATLAS adoption). A system prompt that rewrites
   itself on its own P&L is a new contamination channel: beliefs overfit the last 5 sessions and feed
   back into the advice that generated them. Prompt-hash audits gate it. It is still the
   least-instrumented new surface.
4. **Poisoned text inputs (算法迎合 + self-media RAG).** If we ever add a news/sentiment channel, the
   CN evidence says grounding reaches *promotional* sources by default, and issuers write to game the
   parsers. A whitelist plus treat-text-as-adversarial is mandatory.
5. **Free/low-cost data contagion.** This was CN's #1 pitfall class (silent scraper fallbacks
   poisoning derived metrics, 3–5s stale feeds, quota death at boot). The §3 edits guard it. The risk
   is regression: any future "let's add a cheap secondary source" proposal must re-litigate against
   this list.
6. **CN-model substitution pressure.** If cost pressure ever pushes a DeepSeek/Qwen-class swap:
   compliance-filter refusals are keyword-shaped (荐股 verbs) and cause spurious NO_TRADE storms; CN
   tokenizer/regulatory priors mismatch NSE. Any swap re-runs the full 02 §6.3 gate suite (the
   masked-value audit, format-tax re-validation, refusal-rate logging as a first-class failure mode).
7. **Solo-maintainer OSS fragility** if we vendor any CN repo component (incl. Kronos):
   TradingAgents-CN = 31k★, one maintainer, 218 open issues; akshare has a garbage-data history. Pin
   versions. Vendor hashes. Expect breakage PRs.
8. **Advisory-behavior corruption by imported fight/conviction culture.** The CN retail corpus fights
   fence-sitting ("必须重仓", anti-default-HOLD) because its business model sells decisiveness. Our
   economics sell the opposite. Test every future CN import with one question: "does this push the
   agent toward action beyond evidence?" If yes, §6.1/§6.3 bans it automatically.

---

## Edit register — every proposed change to docs 01/02/03, at section level

This is the working list for whoever applies the deltas. Nothing in this addendum edits those files
directly.

| # | Target doc/section | Change (one line) | Origin |
|---|---|---|---|
| E-01 | 01 §1 ingestion / T1–T8 table | Add an "expected staleness" column per transport | §3 latency-table row |
| E-02 | 01 §4 payload (P-groups) | Global missing-data contract: `null`/`[DATA_MISSING]` sentinels; never 0, never silent carry | §3 missing-data row |
| E-03 | 01 §4 + 02 §6.4 | Two-speed loop: add an 08:45 pre-open brief job + a 15:45 closed-trade review job alongside the intraday loop | §3 two-speed row |
| E-04 | 01 §6.1 FM-03/FM-07 | Ordered boot probe cascade; quota/429-class errors treated as credential-rot; NO_TRADE-day degrade | §3 cascade row |
| E-05 | 01 §6.1 FM-04/FM-08 + new FM-14 | Silent-default poisoning rule: derive from primitives, range-validate, treat implausible constants as staleness | §3 free-data row |
| E-06 | 01 §1 note + 02 §3.1 | If a text/news channel is ever added: source whitelist mandatory; treat text as adversarial | economics §4.6 (算法迎合) |
| E-07 | 02 §3.2 output schema | Add `unverified: []` and the conditional `misread_trap`; add the field-order note for truncation resilience | §2.1, §2.6 |
| E-08 | 02 §3.3 validation | New #9: `unverified` non-empty on LONG_* → demote to NO_TRADE; extend the echo-check enum to strike/expiry/instrument/dates | §2.1, economics §4.3 |
| E-09 | 02 §3.3.4 + 03 §5.1 | Display-side staleness kill: tombstone advisories >90s old, or advisories whose snapshot breached pre-use | economics §4.4 |
| E-10 | 02 §5 system prompt | HARD RULE 7 (banned vocabulary + no asserted positions/dates) + HARD RULE 8 (quarantine/missing≠0) — the final text is in the §6 tour above | §2.4, §2.1 |
| E-11 | 02 §4.1 (new subsection) | Agent-permission rules for offline tooling (write firewall, shift(1), unclosed-bar ban, backtest≠forecast) | §2.7 |
| E-12 | 02 §6 add §6.4 | Offline/report disclosure contracts (`[INFERENCE]`/`[DATA-LIMITED]`), the label-injection rationale generator, the weekly belief-block spec, the offline bull/bear transcript license | §2.2, §2.8, §2.9, confirm-row |
| E-13 | 02 §6.3 release gates | Prompt-evolution gate (template-preservation + change-log + masked-value re-audit + forward-window compare) | §2.10 |
| E-14 | 03 §3.3 | Compliance phrasing: banned-vocab in all user-facing prose, source+date mandate, no news-republish framing | economics §4.1 |
| E-15 | 03 §5 add §5.4 | Pre-trade pre-mortem ritual: the user states stop/target before critique; the 3-axis attack | §2.5 |
| E-16 | 03 §7 | Add the CN-sourced risks (AI-content liability, portfolio-state hallucination as a Stage-gate, fraud-adjacency positioning) | economics §4, risks §8 |
| E-17 | 01 §7 OR-list | Candidate OR-16: a Kronos shadow-experiment per the §5 protocol (cutoff audit first) | §5 |

**Beyond scope — parked:** CN options-sentiment prompting (does not exist on the CN side; a gap, not
an import); the FinZero chart channel (no feed exists); intraday-loop reversion to EOD-only
(rejected — the CN retail evidence is T+1 equity; it does not outrank our instrument-specific design).
