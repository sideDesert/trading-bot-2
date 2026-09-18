# R09: Hybrid LLM-supervisor + deterministic-engine architectures for trading

Date compiled: 2026-09-16. Scope: agentic-trading architectures with supervisor/critic patterns, event-driven vs periodic LLM invocation, cost/latency budgets of LLM analysis loops, "LLM as analyst / code as arbiter" production practice, window/context management, and failure cases of periodic calling.

## Sources

| # | Title | Authors/Org | Year | Tier | URL | one-line claim |
|---|-------|-------------|------|------|-----|----------------|
| 1 | TradingAgents: Multi-Agents LLM Financial Trading Framework | Xiao, Sun, Luo, Wang (UCLA/MIT/Tauric) | 2024-2025 | Academic (arXiv, peer-review pending) | https://arxiv.org/abs/2412.20138 | 7-role LLM "trading firm" (analysts, bull/bear researchers, trader, risk team) beats B&H/MACD/SMA baselines on CR/SR/MDD over a 3-month 5-stock backtest |
| 2 | FinRobot: Open-Source AI Agent Platform for Financial Applications | AI4Finance Foundation | 2024 | Academic + OSS repo | https://arxiv.org/html/2405.14767v2 / https://github.com/AI4Finance-Foundation/FinRobot | Core design principle: strict separation of deterministic financial computation (pure-Python operators) from LLM narration; LLM never computes valuation numbers |
| 3 | agentic_TRACE / "LLM-as-Analyst Trap" + Verifiable Orchestrator pattern | AppliedIngenuity.ai | 2025 | Practitioner (repo + blog series) | https://github.com/AppliedIngenuity-ai/agentic_TRACE / https://appliedingenuity.substack.com/p/the-llm-as-analyst-trap-a-technical | LLM should orchestrate deterministic tools and see only metadata (schemas, stats, row counts), never raw data; LLM-as-analyst collapses via fabrication, math errors, no audit trail |
| 4 | The Alpha Illusion: Reported Alpha from LLM Trading Agents Should Not Be Treated as Deployment Evidence | arXiv 2605.16895 | 2026 | Academic (preprint) | https://arxiv.org/html/2605.16895 | LLM-agent reported alpha is contaminated; FinMem total return drops ~71.85% and QuantAgent Sharpe ~51.48% past pretraining cutoff; recommends LLMs as auditable interfaces upstream of deterministic calibration/risk/execution |
| 5 | Profit Mirage: Revisiting Information Leakage in LLM-based Financial Agents | arXiv 2510.07920 | 2025 | Academic (preprint) | https://doi.org/10.48550/arxiv.2510.07920 | Best LLM trading agents lose ~50% of backtested return once evaluated post-knowledge-cutoff ("profit mirage" from pretraining contamination) |
| 6 | FINSABER: Can LLM-based Financial Investing Strategies Outperform the Market in Long Run? | arXiv 2505.07078 | 2025 | Academic (preprint) | https://arxiv.org/html/2505.07078 | 20-yr, 100+ symbol backtests: reported LLM edge largely disappears; LLM strategies too defensive in bulls, too aggressive in bears — regime-blindness worse than framework complexity helps |
| 7 | An Adaptive Multi-Agent Bitcoin Trading System (verbal feedback / Reflect agent) | arXiv 2510.08068 | 2025 | Academic (preprint) | https://arxiv.org/html/2510.08068v2 | Analyst/decision agents + daily/weekly natural-language critic: weekly feedback improved total performance 31%, cut bearish losses 10%; quant agent +30% vs B&H in bullish regimes |
| 8 | Production LLM Latency Budgets: P50/P95/P99 Math for Trading Apps | aiFinHub Research | 2026 | Practitioner blog (numbers partly illustrative) | https://aifinhub.io/articles/production-llm-latency-budgets-trading/ | 3-call research-decide-execute pipeline: median 2.05s, P95 7.6s, P99 ~10.2s end-to-end; use P95 as budget, P99 as timeout; rule: sum-of-medians × 3 ≈ end-to-end P95 |
| 9 | Cost-Per-Validated-Trade / Token-Cost Reality of LLM Trading Research | aiFinHub Research | 2026 | Practitioner blog | https://aifinhub.io/articles/cost-per-validated-trade-framework/ / https://aifinhub.io/articles/token-cost-reality-llm-trading-research/ | Research stage: 30 items × 25k in + 1.5k out on Sonnet-tier ≈ $30 raw, $9–12 with prompt caching; solo 10 ideas/day loop ≈ $27/mo (Haiku) to $134/mo (Opus); measure cost per validated trade, not per call |
| 10 | Scalping with Bots 2026: Why LLM Latency Kills It | openclawtraderpro.com | 2026 | Practitioner blog | https://openclawtraderpro.com/en/strategies/scalping-llm-latency/ | LLM-in-loop decision = 1.5–3s ≈ 30× too slow for scalping (needs sub-100ms); LLM suited to minutes-to-hours judgment, not tick-speed reactions |
| 11 | How to Connect MT5 to ChatGPT (latency & rate-limit field report) | MQL5 community blog | 2025 | Practitioner blog (field numbers) | https://www.mql5.com/en/blogs/post/764232 | LLM API calls 200–500ms avg; documented production pattern: analyze context every 30s in background, cache scenario responses, only call live API for exceptions → effective 50ms for 80% of trades; rate limits (60 req/min OpenAI, 50 Anthropic) force batching/priority queues |
| 12 | ARC-Capital: AI-Native Global Macro Hedge Fund | GitHub (ashcastelinocs124) | 2026 | Practitioner (OSS project) | https://github.com/ashcastelinocs124/ARC-Capital | Multi-layer trigger system fires a 9-stage LLM pipeline on accumulated conviction (12h-decay ledger), macro calendar windows, and >1.5σ speech-deviation — not on a clock; LLM sees uncurated text in exactly one contained agent |
| 13 | Event-Driven Agent pattern | Agent Patterns Catalog / AgentsButWhy | 2025-2026 | Practitioner pattern catalog | https://www.agentpatternscatalog.org/patterns/event-driven-agent/ / https://agentsbutwhy.com/patterns/event-driven-agents | Polling burns tokens on empty checks and delivers up to one polling-interval late; event-driven triggering cuts reaction latency 70–90% vs polling and ~halves compute spend; requires validation/dedup/idempotency |
| 14 | FinMem: Performance-Enhanced LLM Trading Agent w/ Layered Memory | Yu et al. | 2023 | Academic | https://doi.org/10.48550/arxiv.2311.13743 | Layered memory module (shallow/intermediate/deep, recency-weighted summarization) beats algorithmic agents on stock trading — but see [S4][S5] contamination discounts |
| 15 | FinAgent: Multimodal Foundation Agent for Financial Trading | Zhang et al. (NTU) | 2024 | Academic (WWW/KDD) | https://personal.ntu.edu.sg/boan/papers/KDD24_FinAgent.pdf | Tool-augmented agent w/ dual-level reflection: >36% avg profit improvement over 12 baselines on 6 datasets; tools, not the LLM, do the numeric work |
| 16 | SMETimes: Small but Mighty — statistically-enhanced prompts for time series | arXiv 2503.03594 | 2025 | Academic (preprint) | https://ar5iv.labs.arxiv.org/html/2503.03594 | Feeding descriptive-stat summary features in prompts (not raw series) cut long-horizon forecast error 15.7%; patch + stat encoding beats raw-row prompting |
| 17 | PatchInstruct: Patch-Based Prompting for Time Series w/ LLMs | arXiv 2506.12953 | 2025 | Academic (preprint) | https://ar5iv.labs.arxiv.org/html/2506.12953 | Patch tokenization + structured instructions cut token usage and inference time vs raw-series prompting with equal/better short-horizon accuracy |
| 18 | What AI Can (and Can't Yet) Do for Alpha (AlphaGPT) | Man Group | 2025-2026 | Industry (tier-1 quant firm write-up) | https://www.man.com/insights/what-ai-can-do-for-alpha | LLM research workflow generates hypotheses as a "3-person research team" but "we can't leave it unsupervised just yet" — LLM for research breadth, humans/systematics keep decision authority |
| 19 | Balyasny builds AI research platform for hedge fund teams | ITBrief | 2025-2026 | Industry press | https://itbrief.co.uk/story/balyasny-builds-ai-research-platform-for-hedge-fund-teams | 20-person AI group built desk-facing agents with formal eval pipeline (12+ dimensions incl. numerical reasoning, robustness); LLM embedded in research loop under tight controls, not as autonomous trader |
| 20 | To Trade or Not to Trade: Agentic SDE discovery for market risk | arXiv 2507.08584 | 2025 | Academic (preprint) | https://arxiv.org/pdf/2507.08584 | Explicit analyst/trader separation: LLM agents discover stochastic models, code computes risk metrics that gate trades; model-informed gating improves Sharpe vs plain LLM agents |
| 21 | Claude API provider benchmarks (Haiku 4.5, Sonnet 4.6, Opus 5) | Artificial Analysis | 2026 | Benchmark service (measured) | https://artificialanalysis.ai/models/claude-4-5-haiku/providers | Haiku 4.5: TTFT ~0.76–0.86s median, 78–97 tok/s, ~6–7s total per 10k-input call; max-effort reasoning configs (Opus 5): TTFT ~46–54s, ~50 tok/s — minutes-scale full responses |
| 22 | LangGraph multi-agent supervisor / handoff patterns | LangChain docs | 2025-2026 | Framework docs (canonical) | https://github.com/langchain-ai/langgraph-supervisor-py | Supervisor pattern = LLM routes among worker agents via tool-call handoffs over shared state; docs now steer toward supervisor-as-tools with explicit context trimming/summarization hooks |

## Findings

**Supervisor/critic architectures and measured gains**

- TradingAgents [S1] wires 4 analyst agents → bull/bear researcher debate → trader → risk-management team; on AAPL/GOOGL/AMZN Jan–Mar 2024 it reports CR 23.2–26.6% and Sharpe up to 8.21 with MDD ≤2.1%, beating the best rule-based baseline by ~6.1% CR. Caveat: 3-month window, 5 mega-cap stocks, inside training cutoff — see contamination findings below [S4][S5][S6].
- The strongest measured gain of the *critic/supervisor* component itself comes from the Bitcoin multi-agent system [S7]: adding a Reflect agent that writes daily/weekly natural-language critiques injected into future prompts improved total performance 31% and reduced bearish-regime losses 10% — evidence that a cheap supervisory reflection loop beats single-shot LLM decisions.
- Tool-augmented + reflection architectures (FinAgent [S15]) report >36% average profit improvement over 12 baselines; FinRobot [S2] institutionalizes "LLM narrates, Python computes" as its core principle. The winning published designs all put deterministic code between the LLM and money.
- Contamination caveats [S4][S5][S6]: FinMem's total return drops ~71.85% and QuantAgent's Sharpe ~51.48% when evaluated past the LLM's pretraining cutoff; best published agents lose ~50% out-of-window; 20-yr broad-universe backtests (FINSABER) show LLM edge largely vanishes and LLM strategies are regime-blind (too conservative in bulls, too reckless in bears). Conclusion: supervisor/critic gains are real relative to single-agent baselines *in backtest*, but absolute alpha claims need post-cutoff validation.

**Event-driven vs periodic invocation**

- Documented cadences: background context analysis every 30s with cached scenario responses, live LLM only for exceptions [S11]; 5-minute decide-loops in retail GPT trading agents [S11-adjacent]; event-triggered pipelines with decaying-conviction thresholds (12h half-life ledger, 1.5σ speech-deviation triggers, macro-calendar windows) [S12]; TradingAgents-style full firm simulations run per trading day, not intraday [S1].
- Event-driven beats polling quantitatively: triggering on events cuts reaction latency 70–90% vs fixed-interval polling and ~halves compute/token spend, at the cost of needing validation, dedup, rate-limiting, idempotency [S13]. Empty polls "burn tokens and quota; the few that find something arrive up to one polling-interval late" [S13].
- Rate limits force batching: ~50–60 req/min provider ceilings mean a bot analyzing every tick goes blind within seconds during volatility — the documented fixes are request batching, priority queues, cached pre-analysis, and deterministic fallback rules [S11].

**Cost and latency numbers for LLM loops**

- Single-call measured medians [S21]: Haiku-class ≈ 0.8s TTFT, 80–97 tok/s (≈6–7s total for a thinking-light 10k-input task); Sonnet-class non-reasoning ≈ 1.0–1.2s TTFT, ~25 tok/s; max/reasoning configs ≈ 46–160s TTFT and ~1–3min total — reasoning models are categorically unusable for sub-minute cadence.
- Pipeline compounding [S8]: a 3-LLM-call research→decide→execute pipeline has median ~2.05s but P95 7.6s and P99 ~10–17s; provider queues are worst exactly at the market open (an 800ms service-time call shows 4–8s wall-clock in open-window congestion). Rule of thumb: end-to-end P95 ≈ 3× sum of stage medians; budget P95, hard-timeout P99.
- Decision-level numbers [S10]: LLM-in-loop decisions run 1.5–3s each — ~30× the budget for scalping, which needs sub-100ms reactions; LLMs fit minutes-to-hours judgment loops only.
- Cost per cycle [S9]: a research stage at 30 items × 25k input + 1.5k output ≈ $30 raw on Sonnet-tier, $9–12 with prompt caching; full solo loops (10 ideas/day × 5 calls × 8k-in/1.5k-out) ≈ $27/mo Haiku, $62–80/mo Sonnet, $134/mo Opus. Output tokens cost 3–5× input — cap advice verbosity.

**"LLM as analyst, code as arbiter" in production**

- Frontier quant firms put LLMs in the *research* loop, not the execution loop: Man Group's AlphaGPT generates hypotheses with explicit human supervision ("can't leave it unsupervised") [S18]; Balyasny gates desk agents behind a 12+-dimension internal eval pipeline including numerical reasoning and noise robustness [S19]. Neither lets an LLM emit orders.
- Practitioner architecture consensus (TRACE/Verifiable Orchestrator) [S3]: LLM sees metadata-only tool results (row counts, min/max/mean, warnings), all computation is deterministic tool code, and non-LLM summaries of steps provide the audit trail. Motivations: helpfulness paradox (LLM fabricates data when a query fails), probabilistic arithmetic errors, no audit trail, context-window degradation beyond ~40–50% of context.
- Blue-printry confirmation from academia: [S20] separates analyst (LLM discovers risk models) from trader (code-computed risk metrics gate decisions) and beats sentiment-style LLM agents on Sharpe; [S4]'s recommended safe architecture is "LLMs as auditable information interfaces upstream of independent calibration, risk, and execution modules."

**Window/context management**

- Summaries beat raw rows: statistically-enhanced prompts (descriptive-stat features of the series) reduced long-horizon error 15.7% vs weaker encodings [S16]; patch/tokenized compression of raw series cuts token usage and inference time with equal or better short-horizon accuracy [S17].
- Layered memory works for trading agents: FinMem's shallow/intermediate/deep memory with recency-weighted summarization (recent signals verbatim, older context compressed) improved decisions over fixed-window prompting [S14].
- Budget discipline: conversation history and retrieved context are the dominant input-token terms; context >40–50% of window degrades accuracy materially [S3]. Practical rule emerging across sources: feed the LLM a compact structured snapshot (engine-computed metrics + regime flags + short rolling event digest), not tick-level history.

**Failure modes**

- Periodic-only invocation risks: up to one full polling interval of staleness per event [S13]; stale "obvious" prices within the P99-latency tail (10–17s) can wipe out the edge from fast runs [S8]; 1.5–3s decision latency makes the LLM chase moves that already happened on second-scale setups [S10][S11].
- Silent-failure fabrication: when data fetch/calc fails, a helpfulness-tuned LLM invents plausible numbers (documented as the catastrophic failure mode of LLM-as-analyst designs) [S3].
- Backtest-to-live collapse from contamination and regime blindness: 50–72% return/Sharpe drawdowns past the knowledge cutoff [S4][S5]; bull/bear regime maladaptation [S6].

## Architecture patterns

**P1. LLM-as-Narrator/Orchestrator, Code-as-Engine (TRACE / FinRobot style)** [S2][S3][S4]
Deterministic engine computes all metrics/signals; LLM reads metadata/compact stats, interprets, routes, and explains; a non-LLM summary provides auditability. Wire: engine → structured snapshot (stats, flags, deltas) → LLM → structured advisory JSON → engine validates schema + numeric sanity → human/log. Right when: you need interpretability, audit, zero fabricated numbers. This is the safest default for our advisory bot.

**P2. Supervisor–Worker LLM firm (TradingAgents style)** [S1][S22]
An LLM supervisor routes among specialized analyst agents (technical, sentiment, news, risk); bull/bear debate + risk manager gate the trader. Wire: analysts produce structured reports → supervisor merges → debate rounds → risk team approves/vetoes. Right when: decisions are daily/multi-hour cadence, multi-modal inputs, and explainability of the reasoning chain matters; overkill and too slow/costly for intraday scalping.

**P3. Critic/Reflect loop (verbal RL)** [S7][S15]
Deterministic engine scores realized decisions; a cheap LLM writes daily/weekly critiques appended to future prompts (+31% performance measured). Wire: engine logs decision + outcome → periodic reflect-agent → versioned text memory. Right when: you want continuous improvement without fine-tuning; low cost (weekly batch), high leverage.

**P4. Event-triggered pipeline with conviction ledger** [S12][S13]
Deterministic triggers (threshold breach, calendar window, deviation >1.5–2σ, decaying conviction accumulator) fire the LLM stage only when warranted; dedup + rate-limit + idempotency in front. Right when: events are sparse-asymmetric (news spikes, IV crush, OI anomalies) and empty polls dominate cost. This is the correct invocation model for intraday advisory.

**P5. Cached-context / ambient-analysis loop** [S11]
LLM refreshes a "market state brief" on a slow background cadence (30s documented) and caches scenario-conditioned advice; the hot path uses cache + deterministic rules; live LLM call reserved for exceptions. Right when: you need LLM judgment available at ~50ms effective latency. Pairs naturally with P4 (30s ambient refresh + event interrupts).

**P6. Analyst-discovers, code-arbiter-decides (model-discovery)** [S20]
LLM does model/hypothesis discovery offline; code computes risk metrics online and gates actions. Right when: the LLM's comparative advantage is breadth/creativity, not speed. For us: use Claude offline/nearline to propose scalp setups and parameter regimes; the Python engine alone decides in-session.

## Implications for our bot

**Cadence budget (evidence-backed):**

- Never put the LLM in the tick path. Documented LLM decisions are 1.5–3s median [S10] with 7–17s tails [S8]; scalping reaction needs sub-second. Our engine's entry/exit gating, stops, and sizing must be 100% deterministic Python.
- Ambient snapshot cadence 30s (documented in production [S11]) with prompt caching; Haiku/Sonnet-class model (TTFT <1.2s [S21]); snapshot = engine-computed snapshot JSON (Greeks/IV/ΔOI, VWAP deltas, regime flags, rolling 5/15/60min window stats) — fits ~1.5–3k input tokens → ≈$0.005–0.015/cycle uncached, far less with a cached system prompt; ~200–500 cycles per 3.5h session → order $1–4/session on Haiku-tier [S9].
- Event interrupts layered on the 30s ambient loop [S4-style triggers]: fire immediate LLM escalate on |spot move| > kσ in m minutes, IV spike, OI cliff, or position P&L breach; throttle (dedup + cooldown ≥60–120s) per [S13]; expected 5–20 escalations/day. Budget P95 ≈ 3× stage-median sum ≈ 8–10s for a 1-call advisory; hard-timeout at 12s with deterministic fallback advice [S8].
- 5min cadence acceptable for regime/strategy-level reflection only; daily/weekly critic loop (P3) for learning. Any claim of an LLM making second-scale entry/exit calls is contradicted by every measured source.

**Supervisor/human checkpoint design:**

- P1+P3+P4 hybrid: engine = sole arbiter of numbers and risk limits (LLM can never emit an executable order or a number the engine didn't compute [S2][S3]); Claude advisory layer outputs schema-validated JSON {bias, setup_quality, risk_notes, invalidation_levels} which the engine cross-checks against its own computed values; mismatches logged as hallucination events.
- Human-in-the-loop checkpoints: (1) session start — human approves the day's playbook Claude drafts from overnight context; (2) any advisory that would widen a risk parameter → hard human confirmation; (3) end-of-day — critic agent reviews logged decisions vs outcomes [S7]. New strategy discovery runs offline (P6) — Man Group's "not unsupervised yet" [S18] applies in spades to a retail advisor.
- Pre-warm/parallelize the advisory call where possible, and keep an opinionated deterministic fallback so a provider queue spike (worst at [US/India] market open [S8]) degrades to silent deterministic mode, not to stale advice.
- Evaluation hygiene: paper-trade and evaluate only on post-cutoff data; expect published-style backtest gains to shrink 50%+ live [S4][S5][S6].

## Open questions

1. No published source gives measured outcomes (PnL or decision quality) for hybrid event+30s-cadence intraday *options* advisory — cadence numbers above are synthesized from adjacent domains (FX/equity/crypto). Needs our own logged A/B: advisory-on vs advisory-off shadow sessions.
2. What snapshot dimensionality maximizes Claude's marginal value while staying under the ~40–50% context-degradation threshold [S3] on NIFTY chains (which fields of the option chain actually survive summarization)?
3. Optimal trigger thresholds (σ-multiplier, conviction decay half-life) for NIFTY event interrupts — ARC-Capital's 12h half-life and 1.5σ speech triggers are macro-tuned, unvalidated for intraday index options [S12].
4. Whether weekly verbal-reflection gains (+31% [S7]) replicate when the underlying decision policy is deterministic and only the *advisory text* learns.
5. Provider tail behavior during India market hours — all published latency congestion data is US-centric [S8][S21]; measure our own P50/P95/P99 by time-of-day.
