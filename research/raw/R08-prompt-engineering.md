# R08: Evidence-backed prompt strategies for market-analysis / trading LLMs

## Sources

| # | Title | Authors/Org | Year | Tier | URL | One-line claim |
|---|-------|-------------|------|------|-----|----------------|
| 1 | TradingAgents: Multi-Agents LLM Financial Trading Framework | Xiao, Sun, Luo, Wang (UCLA/MIT/Tauric) | 2024 (v7 2025) | A (arXiv, heavily cited, 90k★ repo) | https://arxiv.org/abs/2412.20138 | Multi-agent debate + structured decision protocol beats rule baselines by ≥6.1% cumulative return over 3-month backtest |
| 2 | TradingAgents repo prompt files (market_analyst.py, trader.py, aggressive/conservative_debator.py, research_manager.py) | TauricResearch (GitHub) | 2024-26 | A (production-grade open source) | https://github.com/TauricResearch/TradingAgents | Verbatim live prompt templates: tool-verified facts, absolute-price stop-loss rules, 3-way risk debate, judge with explicit rating scale |
| 3 | FinMem: A Performance-Enhanced LLM Trading Agent with Layered Memory and Character Design | Yu et al. (Stevens) | 2023 (AAAI-SS 2024) | A | https://arxiv.org/abs/2311.13743 | Layered memory + character design → TSLA cum. return 61.8% vs −18.6% buy&hold; self-adaptive risk persona Sharpe 2.50 vs risk-seeking −0.79 |
| 4 | FinMem source code (puppy/prompts.py) | pipiku915/FinMem-LLM-StockTrading (GitHub) | 2023-24 | B | https://github.com/pipiku915/FinMem-LLM-StockTrading | Verbatim decision prompt: constrained action set (buy/sell/hold with hold as fallback), conditional risk-seeking/-averse character switch, strict JSON suffix |
| 5 | FinAgent: A Multimodal Foundation Agent for Financial Trading | Zhang, Zhao, Xia et al. (NTU, KDD'24) | 2024 | A | https://arxiv.org/abs/2402.18485 | 10-rule checklist decision prompt in XML (chose XML over JSON because "JSON's strict formatting requirements frequently lead to errors"); +36% avg profit vs 12 baselines |
| 6 | Can ChatGPT Forecast Stock Price Movements? | Lopez-Lira & Tang (U. Florida) | 2023 (rev. 2026) | A | https://arxiv.org/abs/2304.07619 | Minimal persona prompt "Pretend you are a financial expert...Answer YES/NO/UNKNOWN" → long-short strategy Sharpe 3.28 (GPT-4) vs 1.79 (GPT-3.5), 38 bps/day |
| 7 | Let Me Speak Freely? Format Restrictions and LLM Performance | Tam et al. (Appier/AI Research) | 2024 | A | https://arxiv.org/abs/2408.02442 | Forcing JSON/structured formats causes significant degradation of LLM reasoning; stricter formats → more degradation |
| 8 | The Format Tax | Lee et al. | 2026 | B (arXiv preprint) | https://arxiv.org/pdf/2604.03616 | Format-requesting *instructions alone* (before constrained decoding) cause most accuracy loss on open-weight models; decoupling reasoning-then-reformat recovers most of it; latest closed models show little format tax |
| 9 | To CoT or not to CoT? | Sprague et al. | 2024 | A | https://arxiv.org/abs/2409.12183 | Meta-analysis of 100+ papers: CoT helps mainly math/symbolic tasks; on MMLU direct answer ≈ CoT unless an "=" appears; tool-augmented execution beats CoT |
| 10 | Reasoning or Overthinking: LLMs on Financial Sentiment Analysis | (arXiv 2506.04574) | 2025 | A | https://arxiv.org/abs/2506.04574 | Zero-shot Financial PhraseBank: CoT and reasoning models do NOT improve sentiment accuracy; best = GPT-4o with no CoT ("overthinking") |
| 11 | Mind Your Step (by Step) | Liu et al. | 2024 | A | https://arxiv.org/abs/2410.21333 | On tasks where deliberation hurts humans, CoT drops accuracy up to 36.3 pts (o1-preview vs GPT-4o direct) |
| 12 | Playing Pretend: Expert Personas Don't Improve Factual Accuracy (GAIL Fourth Report) | Mollick & Wharton GAIL | 2025 | B (lab report, arXiv 2512.05858) | https://arxiv.org/pdf/2512.05858 | Expert personas ("you are a physics expert") had no significant accuracy effect on GPQA/MMLU-Pro across 6 models; low-knowledge personas hurt |
| 13 | "You are a brilliant mathematician" Does Not Make LLMs Act Like One | (OpenReview) | 2025 | B | https://openreview.net/pdf?id=sVaRgmH8FE | Domain priming consistently helps (+2.5% mean, Gemini); personas volatile, sometimes harmful (−6.1% Gemini, −3.3% GPT-4.1 math w/ CoT); negated personas ≈ positive ones |
| 14 | Principled Personas | (EMNLP 2025 main) | 2025 | A | https://aclanthology.org/2025.emnlp-main.1364.pdf | Expert personas ±positive/insignificant; models sensitive to *irrelevant* persona details with drops up to ~30 pts |
| 15 | TrustTrade: Selective Consensus for LLM Trading Agents | (arXiv 2603.22567) | 2026 | B | https://arxiv.org/html/2603.22567 | Cross-agent consistency weighting (aggregate multiple LLM agents, down-weight divergent/weakly-grounded signals) stabilizes risk-return profile in noisy markets |
| 16 | Multi-Agent AI Oracle Systems for Prediction Market Resolution | (arXiv 2605.30802, thesis) | 2026 | B | https://arxiv.org/html/2605.30802 | Independent aggregation + confidence-weighted voting: 83.43% accuracy (best single model 82.4%); *deliberative consensus* degrades to ~76% via "persuasive error propagation" |
| 17 | The Necessity of Setting Temperature in LLM-as-a-Judge | (arXiv 2603.28304) | 2026 | B | https://arxiv.org/pdf/2603.28304 | Higher temperature decreases judgment consistency and increases format errors; low temp = stability/reproducibility, high temp = exploration in ambiguous cases |
| 18 | Necessary but Not Sufficient: Temperature Control and Reproducibility | (arXiv 2606.26185) | 2026 | B | https://arxiv.org/html/2606.26185v1 | Unset temperature silently defaults to 1.0 → borderline pass/fail flips up to ~50% over 20 runs; even T=0 leaves 1–2/7 borderline items non-reproducible |
| 19 | Stop Feeding Raw JSON to LLMs — 9 Data Formats Measured | Jang Wook Lee (blog, tiktoken-measured) | 2025 | C | https://jangwook.net/en/blog/en/llm-token-cost-data-format-experiment/ | 50 flat records: pretty JSON 4,128 tokens vs CSV 1,650 (−60%) vs TSV 1,568 (−62%); XML +16% |
| 20 | thoeltig/file-format-token-accuracy-benchmark | thoeltig (GitHub benchmark, Claude-4.5-Haiku) | 2025 | C | https://github.com/thoeltig/file-format-token-accuracy-benchmark | CSV: 70.98% weighted accuracy, cheapest tokens, best for dense mandatory data but −15% accuracy on sparse data; YAML highest accuracy 71.96% at 2.62× CSV tokens; pretty JSON adds tokens, not accuracy |
| 21 | Prompt engineering for structured data: comparative evaluation of styles and LLM performance | Schmidt et al. (William & Mary) | 2025 | B | https://www.cs.wm.edu/~dcschmidt/PDF/Optimizing_Prompt_Styles_for_Structured_Data_Generation_in_LLM.pdf | JSON/YAML boost accuracy for hierarchical data; CSV/prefix styles cut token cost and latency with little accuracy loss on flat data |
| 22 | Voting or Consensus? Decision-Making in Multi-Agent Debate | (ACL 2025 Findings) | 2025 | A | https://aclanthology.org/2025.findings-acl.606.pdf | Systematic comparison of aggregation rules in LLM debate; decision protocol choice materially changes outcomes |
| 23 | Dual-Agent LLM Debate for Financial Market Indicators (MDPI Mathematics) | (MDPI 14(8):1393) | 2026 | C | https://www.mdpi.com/2227-7390/14/8/1393 | Proponent–opponent cross-debate (Gemini vs ChatGPT) over 75 FMIs: consensus forecast F2 > single-LLM F1 in accuracy and directional stability, biggest gains on volatile assets |
| 24 | Self-Consistency Improves Chain of Thought Reasoning (Wang et al.) | Wang et al. (Google) | 2022 | A | https://arxiv.org/abs/2203.11171 | Sampling diverse CoT paths + majority vote: +17.9 pts on GSM8K (PaLM-540B), +12.7% StrategyQA etc. — classic ensembling baseline |

## Findings

- [S1, S2] TradingAgents' published/live prompts encode four recurring patterns: (1) separation of *report generation* (analysts, natural language + forced Markdown summary table) from *decision* (trader, structured `TraderProposal` schema); (2) a "source of truth / tool-verified" instruction ("call get_verified_market_snapshot ... treat it as the source of truth for any exact OHLCV, price-level, or indicator-value claim. If another tool's output conflicts ... flag the discrepancy rather than inventing a reconciled number"); (3) hard format rules for numeric levels ("State entry price and stop-loss as absolute price levels in the instrument's quote currency ... never a percentage or a range"); (4) adversarial self-adversity: bull/bear + aggressive/conservative/neutral risk debators argue, then a *Research Manager* judges with an explicit 5-point rating scale (Buy/Overweight/Hold/Underweight/Sell) and an anti-decisiveness instruction ("do not manufacture a direction merely to appear decisive").
- [S1] TradingAgents cost per prediction: **11 LLM calls & 20+ tool calls** → ≥23.21% cumulative return, Sharpe 5.60–8.21 over best baselines (3-month backtest, 3 stocks). Multi-agent prompts work but are expensive and backtest-limited.
- [S3, S4] FinMem's beaten results come from *prompt-time character conditioning*: the test prompt switches the persona mid-prompt based on recent P&L ("When cumulative return is positive or zero, you are a risk-seeking investor... when negative, risk-averse"). Self-adaptive persona: Sharpe 2.4960; fixed risk-seeking: −0.7866; risk-averse: −1.5783; B&H: −2.0845 (TSLA period). Model choice dominates prompt polish: GPT-4 cum. ret. 62.6% vs Llama2-70b −52.7% with identical prompts.
- [S3] FinMem enforces valid actions in *code*, not the prompt: Guardrails AI validation forces output into {"Buy","Sell","Hold"} and validates memory IDs. Combined with the prompt instruction "When it is really hard to make a 'buy'-or-'sell' decision, you could go with 'hold'" — the escape-hatch pattern.
- [S5] FinAgent chose **XML** as the decision output format because "JSON's strict formatting requirements frequently lead to errors" with GPT-4; decision template = 10-numbered hard constraints including a *position/cash feasibility check* ("If your CASH reserve is lower than the current Adj Close Price, then the decision result should NOT be BUY. Similarly, ... NOT SELL if you have no existing POSITION") — a guardrail rule written in natural language. +36% avg profit over 12 baselines; 92.27% return on one dataset.
- [S5] FinAgent Limitation 3: "Result is sensitive to prompt engineering and randomness... controlling the randomness in the responses is not feasible" (OpenAI API). Direct empirical confirmation that trading decisions vary trial-to-trial — mandates ensembling/logging.
- [S6] Lopez-Lira & Tang got publication-grade return predictability from a *two-line* prompt: "Forget all your previous instructions. Pretend you are a financial expert with stock recommendation experience. Answer 'YES' if good news, 'NO' if bad news, or 'UNKNOWN' if uncertain **in the first line**. Then elaborate with one short and concise sentence." Key pattern: answer-first-then-elaborate (bounded rationale, constrained class). Strategy Sharpe 3.28 with GPT-4 vs 1.79 GPT-3.5, negative Sharpe for BERT/GPT-1/2 — capability threshold beats prompt cleverness.
- [S7] "Let Me Speak Freely": restricting generation space (JSON mode, format instructions) causes *significant decline* in reasoning; stricter constraints → greater degradation. Mitigation found: separate reasoning (free-form CoT) stage from formatting stage.
- [S8] The Format Tax (2026, arXiv 2604.03616): the accuracy loss from structured output comes mostly from the *format-requesting instruction in the prompt*, not from constrained decoding. Freeform-reason-then-reformat (2-pass) or extended thinking recovers most lost accuracy across 6 open-weight models. Latest closed-weight models show little format tax.
- [S9] CoT meta-analysis (100+ papers, 20 datasets, 14 models): CoT's big gains concentrate in math/symbolic tasks; elsewhere direct answering ≈ CoT. On MMLU, CoT and direct answer are nearly identical unless symbolic execution is involved. Much of CoT's gain is symbolic *execution*, where a code/solver tool beats pure CoT (see also PoT: +12% avg over CoT on financial QA, arXiv 2211.12588).
- [S10] Directly on-finance result: zero-shot Financial PhraseBank sentiment — reasoning (CoT or reasoning models) does NOT improve accuracy; best combo = GPT-4o **without** CoT. "Overthinking" degrades alignment with human labels.
- [S11] CoT actively *reduces* performance (up to 36.3 pts, o1-preview) on tasks where human deliberation hurts (pattern-recognition-ish, implicit tasks) — relevant to fast intraday tape-reads.
- [S12–S14] Persona evidence is now consistent: expert personas ("you are a world-class X") give **no significant accuracy gain** on objective benchmarks (GAIL: GPQA 198 Qs × 25 trials × 6 models); mismatched or irrelevant persona details can drop accuracy ~30 pts; low-knowledge personas reliably hurt. BUT domain *priming* (task-relevant context without role-play) gives small consistent gains (+2.5% mean). TradingAgents/FinAgent personas are used for *role decomposition & debate diversity*, not for per-call accuracy — that use is not contradicted by these studies.
- [S15, S16, S22, S23] Ensemble voting beats deliberation for accuracy: confidence-weighted independent aggregation hit 83.43% vs 76% for debate-consensus oracle panels (persuasive-wrongness flips correct models; inter-model error correlation r = 0.53–0.69 caps ensemble gains). TrustTrade formalizes this for trading: weight agents by semantic+numerical agreement, discount divergent/weakly-grounded signals. Dual-agent debate (proponent/opponent) still improved directional stability of forecasts on 75 FMIs — debate helps ranking/stability, voting helps accuracy.
- [S17, S18] Temperature: provider default is silently 1.0 → borderline binary decisions flip up to ~50% of runs if temperature unset. T=0 improves but does not guarantee determinism (1–2/7 borderline items still flip; background-temperature/nondeterminism literature). Implication: pin temperature explicitly, log decision distributions, treat borderline signals as non-signals.
- [S19–S21] Data-format economics: pretty JSON costs 2.5–2.6× the tokens of CSV/TSV for flat tabular data (4,128 vs 1,650/1,568 tokens per 50 records); XML is worst (+16% over pretty JSON). Accuracy on flat data: CSV ≈ best-per-token (70.98%; YAML 71.96% but 2.62× tokens); pretty JSON adds cost, not accuracy; CSV accuracy drops ~15% on *sparse* data. Hierarchical data inverts the ranking: JSON/YAML prompt styles score higher accuracy there.
- [S24] Self-consistency (sample N CoT paths, majority vote): +17.9 pts GSM8K — the reference result behind majority-voting trade signals.

## Prompt pattern catalogue

**P1. Verified-numbers-only / "source of truth" tool grounding [S2 market_analyst.py]**
> "call get_verified_market_snapshot for this ticker and the current date, and treat it as the source of truth for any exact OHLCV, price-level, or indicator-value claim. If another tool's output conflicts with the verified snapshot, flag the discrepancy rather than inventing a reconciled number. Do not claim historical validation, support/resistance bounces, or exact percentage moves unless they are directly supported by tool output with concrete dates and prices."

**P2. Absolute-not-percent levels rule (anti-format-parse-failure) [S2 trader.py, GitHub issues #1167/#1288]**
> "State entry price and stop-loss as absolute price levels in the instrument's quote currency (for example 189.5), never a percentage or a range; convert a percentage distance to the price level it implies, or omit the field if you cannot state a number."
Plus grounding instruction: "Ground concrete price levels (entry, stop-loss, position sizing) in the technical market report's price structure — current price, support/resistance, ATR, and volatility."

**P3. Answer-first-then-elaborate, constrained class, escape hatch [S6 Lopez-Lira; S4 FinMem]**
> Lopez-Lira: "Answer 'YES' if good news, 'NO' if bad news, or 'UNKNOWN' if uncertain in the first line. Then elaborate with one short and concise sentence on the next line."
> FinMem: "You should provide exactly one of the following investment decisions: buy or sell. When it is really hard to make a 'buy'-or-'sell' decision, you could go with 'hold' option."

**P4. Numbered hard-constraint checklist incl. feasibility checks in-prompt [S5 FinAgent decision template]**
> "9. Before making a decision, you must check the current situation. If your CASH reserve is lower than the current Adj Close Price, then the decision result should NOT be BUY... 7. When providing the final decision, you should pay more attention to the market intelligence which will cause an immediate impact on the price... You can only output one of BUY, HOLD and SELL." Output as fixed XML: `<output><string name="analysis">...<string name="action">BUY<string name="reasoning">...`

**P5. Conditional risk character switch driven by recent P&L (self-adaptive persona) [S4 FinMem prompts.py]**
> "When cumulative return is positive or zero, you are a risk-seeking investor, positive information have a greater influence on your investment decisions... when negative, you are a risk-averse investor, negative information have a greater influence..." (Empirically the winning variant, Sharpe 2.50 vs −0.79/−1.58 for static personas [S3].)

**P6. Debate-role adversarial prompts + neutral judge with anti-decisiveness instruction [S2 aggressive/conservative_debator.py, research_manager.py]**
> Aggressive: "champion high-reward, high-risk opportunities... respond directly to each point made by the conservative and neutral analysts, countering with data-driven rebuttals." Conservative: "critically examine high-risk elements, pointing out where the decision may expose the firm to undue risk."
> Judge: "Choose Hold when the evidence is balanced, materially conflicting, ambiguous, or insufficient... do not manufacture a direction merely to appear decisive. Weigh the bull and bear cases on their merits, independent of which side spoke first or last." (Recency/neutrality guard.)

**P7. Indicator-selection diet with anti-redundancy rule [S2 market_analyst.py]**
> "Your role is to select the most relevant indicators ... choose up to 8 indicators that provide complementary insights without redundancy... do not select both rsi and stochrsi ... call get_stock_data first." (Curated menu + cap beats dump-everything; fights token-window pain [S19–S21].)

**P8. Freeform-reason-then-format two-pass (mitigate the Format Tax) [S7, S8]**
> Run analysis as unconstrained text (or model's native reasoning), then a second cheap call converts to the JSON schema. Recovers most accuracy lost to JSON-mode in open-weight models; also insulates parse layer from reasoning layer. FinMem achieves the same via `${gr.complete_json_suffix_v2}` + Guardrails validation + reask loop [S3, S4].

**P9. Ensemble vote over deliberative consensus for the actual action [S16, S22, S24, S15]**
> Sample N independent signals (or independent analyst agents), aggregate by confidence-weighted or plain majority vote; use debate only to *improve individual rationales*, not to reach verbal consensus (deliberate consensus degraded accuracy 83.4%→76% [S16]).

**P10. Team-stop protocol token (FINAL TRANSACTION PROPOSAL) [S2]**
> "If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable, prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop." — literal protocol strings to coordinate multi-agent state machines.

## Implications for our bot — recommended prompt skeleton

For a NIFTY intraday options scalping advisory (LLM reads snapshot → advice), the evidence points to a **single-agent, schema-typed, no-persona, low-CoT design** — not a TradingAgents-style swarm (too slow/expensive for intraday; 11 LLM calls per decision [S1]).

```
SYSTEM:
You receive machine-generated NIFTY options market snapshots and return
one trade recommendation as a JSON object. Nothing else.

HARD RULES (code-enforced; stated here for consistent field semantics):
1. All price/level fields (entry, stop_loss, target, invalidation_level) are
   absolute NIFTY index or option-premium levels in INR. Never percentages,
   never ranges. Omit the field if you cannot justify a number.   [P2]
2. Every exact price, OI, IV, or delta claim must come verbatim from the
   snapshot below. If inputs conflict, set data_conflict: true rather than
   reconciling silently.                                       [P1]
3. "action" must be exactly one of: LONG_CALL | LONG_PUT | NO_TRADE.
   Choose NO_TRADE when signals are mixed, data is stale/missing, or R:R
   to stop vs target < MIN_RR.                                 [P3, P6]
4. Position size in lots and max-loss-in-INR are COMPUTED BY THE CALLER
   from your stop_loss; do not output size. (Sizing/invalidation stay in
   code — LLMs are unreliable at arithmetic [S9/PoT]; Guardrails-style
   validation re-asks on schema violation.)                     [S3, S4]
5. If now > 15:15 IST or time_to_expiry < SCALP_HORIZON, action=NO_TRADE.

USER (per call):
SNAPSHOT (CSV, dense numeric blocks; ISO timestamps):       [P7, S19–S21]
spot_ohlc_1m:  ts,open,high,low,close,vol\n...
option_chain_focus: strike,ce_ltp,pe_ltp,ce_oi,ch_oi,ce_iv,pe_iv,delta\n...
indicators: vwap=..., atr14=..., rsi5=..., pcr=..., iv_rank=...
recent_signals: [<pre-computed anomaly events with ts>]
account_context: {open_positions, daily_pnl, session_rr_so_far}

Respond with ONLY this JSON (freeform analysis is done by you internally /
in a prior unconstrained pass if a frontier open-weight model is used):
{action, direction_confidence: 0-1, entry_level, stop_loss, target_1,
 invalidation_condition: "one sentence, in price terms", time_stop_minutes,
 data_conflict: bool, one_line_rationale (<=25 words)}
```

Design rationale mapped to evidence: (i) no persona role-play — use domain *priming* via field names instead [S12–S14]; (ii) answer-first JSON with bounded rationale to avoid CoT overthinking on pattern tasks [S10, S11] but keep `one_line_rationale` for audit; if the model needs computation (Greeks P&L), do it in code/tools, not CoT [S9]; (iii) pin temperature near 0 explicitly AND log N=3–5 samples for borderline cases or use majority vote only as a tie-breaker [S17, S18, S24]; (iv) CSV (not pretty JSON) for numeric snapshots — ~60% token savings at equal accuracy on dense data [S19, S20]; (v) all risk guardrails (percent ranges rejected, +slippage buffer on entry, max daily loss, square-off time) validated in code with Guardrails-style re-ask, mirroring FinMem [S3]; LLM prompt repeats rules only to keep field semantics consistent.

## Open questions

1. Does the Format Tax persist for GPT-5/Claude-4.5/Gemini-3-class models *with* native JSON schema mode on India-market intraday data? (S8 says latest closed models show little tax — verify on our snapshots.)
2. Self-consistency N: what N and what cost budget actually moves scalping-signal stability, given inter-model/intra-model error correlation (r≈0.53–0.69 [S16])?
3. XML output (FinAgent's choice, [S5]) vs JSON-schema mode for reliability — worth a small A/B; XML was pre-structured-outputs-era.
4. FinMem-style P&L-conditioned risk character switch for index-options scalping — does self-adaptive aggression beat fixed risk parameters intraday, or does it create feedback loops?
5. Token-window pain quantified for our exact snapshot: 1-min bars × session + full chain is infeasible; need measured compression (CSV + focus-strike window + pre-computed indicators) and a measured accuracy token curve before freeze.
6. Is ANY debate worth it intraday? S23 shows cross-model debate helped directional *stability* on volatile assets; S16 shows consensus voting hurt accuracy on factual resolution. Which applies to 1–15 min trading horizons is untested.
