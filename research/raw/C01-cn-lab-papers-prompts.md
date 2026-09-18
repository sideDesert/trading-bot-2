# C01: CN-lab papers & verbatim prompts

Round-1 supplement focused on Chinese-lab LLM-trading papers/repos, with verbatim prompt extraction from GitHub raw files and arXiv HTML appendices. Extracted 2026-09-16. Repo URLs verified by live fetch (GitHub API / raw.githubusercontent).

## Sources

| # | Paper/Repo | Org | Year | URL | what it is |
|---|---|---|---|---|---|
| 1 | FinCon | Stevens/The FinAI (CN-led team) | 2024 (NeurIPS'24) | https://arxiv.org/html/2407.06567 · repo https://github.com/The-FinAI/FinCon (README-only stub as of fetch) | Synthesized manager–analyst multi-agent w/ Conceptual Verbal Reinforcement (CVRF); appendix A.4 gives modular prompt template structure |
| 2 | FinAgent | Westlake/ZJU-linked (Zhang et al.) | 2024 | https://arxiv.org/html/2402.18485 | Multimodal foundation trading agent; appendix exposes verbatim system + market-intelligence analysis prompts |
| 3 | FinRobot | AI4Finance Foundation | 2024– | https://github.com/AI4Finance-Foundation/FinRobot/blob/master/finrobot/agents/prompts.py | Repo of agent system prompts (leader/order orchestration) |
| 4 | FinGPT Forecaster | AI4Finance Foundation | 2023– | https://github.com/AI4Finance-Foundation/FinGPT/blob/master/fingpt/FinGPT_Forecaster/prompt.py | Instruction-tuning prompt format (label-injection SFT); answer schema: `[Positive Developments]`/`[Potential Concerns]`/`[Prediction & Analysis]` |
| 5 | InvestorBench (code: felis33/investor-bench) | Stevens/Yale + The FinAI | 2025 (ACL'25) | https://github.com/felis33/investor-bench/blob/main/src/chat/prompt/ | FinMem-style layered-memory prompt constructors + guardrail prompts |
| 6 | StockAgent | HKU/Shanghai AI Lab group (MingyuJ666) | 2024 | https://github.com/MingyuJ666/Stockagent/blob/main/prompt/agent_prompt.py | Simulated market agents; verbatim JSON-action prompts incl. deliberate activity-priming |
| 7 | RD-Agent | Microsoft Research Asia | 2024– | https://github.com/microsoft/RD-Agent/blob/main/rdagent/app/qlib_rd_loop/prompts.yaml | Qlib factor/model R&D loop; hypothesis-generation prompt |
| 8 | Fin-R1 | SUFE AIFLM Lab (Shanghai Univ. of Finance & Economics) | 2025 | https://github.com/SUFE-AIFLM-Lab/Fin-R1/blob/main/README.md | Chinese financial reasoning model; README shows Chinese compliance prompt + think/answer format |
| 9 | LLMFactor | HKUST(GZ) / IDEA | 2024 | https://arxiv.org/html/2406.10811 | SKGN: cloze (fill-in-the-blank) prompt templates, EN **and** CN versions verbatim in Table 5/6; CMIN-US/CMIN-CN datasets |
| 10 | TradingAgents | Tauric Research (CN-led authors; arXiv 2412.20138) | 2024–2026 | https://github.com/TauricResearch/TradingAgents/tree/main/tradingagents/agents | Live repo prompt files: trader, analysts, bull/bear researchers, risk debators, research manager |
| 11 | TradingAgents-CN (fork) | hsliuping (community) | 2025– | https://github.com/hsliuping/TradingAgents-CN/blob/main/tradingagents/agents/trader/trader.py | A股-adapted fork with **fully Chinese** system prompts — best verbatim Chinese-language corpus found |
| 12 | Kronos | Tsinghua-associated (shiyu-coder, NeoQuasar HF) | 2025 | https://github.com/shiyu-coder/Kronos | K-line foundation model — **no text prompts**; input convention = quantized OHLCV token context (see extract) |
| 13 | (adjacent, non-CN) ATLAS | NTUA Athens (surfaced via Chinese paper-notes sites) | 2025 | https://arxiv.org/html/2510.15949 | Adaptive-OPRO: online *prompt optimization* for a trading agent with template separation; included because it is the strongest NEW prompt mechanism found in this sweep, flagged non-CN |
| 14 | (adjacent, non-CN) MarketSenseAI 2.0 | Alpha Tensor / NTUA (Greek) | 2025 | https://arxiv.org/html/2502.00415 | News/Fundamentals/Dynamics/Macro agents → CoT Signal Agent. No Chinese-language original exists (the "任何中文论文" ask resolves to: none; Chinese coverage at papernotes.org only). Included as reference only |
| 15 | (adjacent, JPX data) "Toward Expert Investment Teams" | JP-RIN/Swiftscholar-indexed | 2025 | https://www.swiftscholar.net/zh/paper/69a4f9b694ecec188cfd0947 | Fine-grained (vs coarse role) task decomposition lifts risk-adjusted returns |
| — | AlphaGPT / AlphaStudio, "SETrade/Agentic Quant Team", "FinM1" | — | — | **Not located** with verifiable URLs; refusing to fabricate. AlphaStudio-like work exists but no extractable public prompt was found | — |

## Verbatim prompt extracts

### TradingAgents (TauricResearch) — `trader/trader.py` system prompt (verbatim)
```
You are a trading agent analyzing market data to make investment decisions. Based on your analysis, provide a specific recommendation to buy, sell, or hold. [if market_report present:] Ground concrete price levels (entry, stop-loss, position sizing) in the technical market report's price structure -- current price, support/resistance, ATR, and volatility -- and use the research plan for direction and strategy. State entry price and stop-loss as absolute price levels in the instrument's quote currency (for example 189.5), never a percentage or a range; convert a percentage distance to the price level it implies, or omit the field if you cannot state a number.
```
Role in system: final Trader agent converting the Research Manager's plan into an actionable proposal. Note issue-referenced rationale in code: "#1288 — Asking for concrete levels invites a percentage ('15%'), which is not a price and fails the structured parse."

### TradingAgents — `market_analyst.py` system prompt (verbatim, abridged)
```
You are a trading assistant tasked with analyzing financial markets. Your role is to select the **most relevant indicators** for a given market condition or trading strategy ... choose up to **8 indicators** that provide complementary insights without redundancy. Categories ... Moving Averages: close_50_sma / close_200_sma / close_10_ema ... MACD, Momentum (rsi), Volatility (boll, atr: "Set stop-loss levels and adjust position sizes based on current market volatility"), Volume (vwma) ... Avoid redundancy (e.g., do not select both rsi and stochrsi) ... Make sure to call get_stock_data first ... Before writing the final report, call get_verified_market_snapshot for this ticker and the current date, and treat it as the source of truth for any exact OHLCV ... claim. If another tool's output conflicts with the verified snapshot, flag the discrepancy rather than inventing a reconciled number.
```
Plus a wrap: `FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**` protocol and "Today's date is {current_date}; treat it as 'now' for all analysis and tool-call date ranges."

### TradingAgents — `managers/research_manager.py` (verbatim, abridged)
```
As the Research Manager and debate facilitator, your role is to critically evaluate this round of debate ... Rating Scale (use exactly one): Buy / Overweight / Hold / Underweight / Sell ... Commit to a directional stance only when the debate's strongest arguments clearly warrant one. Choose Hold when the evidence is balanced, materially conflicting, ambiguous, or insufficient ... do not manufacture a direction merely to appear decisive. Weigh the bull and bear cases on their merits, independent of which side spoke first or last.
```

### TradingAgents — `risk_mgmt/aggressive_debator.py` (verbatim, abridged)
```
As the Aggressive Risk Analyst, your role is to actively champion high-reward, high-risk opportunities ... respond directly to each point made by the conservative and neutral analysts, countering with data-driven rebuttals ... Maintain a focus on debating and persuading, not just presenting data. ... Output conversationally as if you are speaking without any special formatting.
```

### TradingAgents-CN (hsliuping fork) — Chinese trader system prompt (verbatim, 中文原文)
```
您是一位专业的交易员，负责分析市场数据并做出投资决策。基于您的分析，请提供具体的买入、卖出或持有建议。
⚠️ 重要提醒：当前分析的股票代码是 {company_name}，请使用正确的货币单位：{currency}（{currency_symbol}）
🔴 严格要求：
- 股票代码 {company_name} 的公司名称必须严格按照基本面报告中的真实数据
- 绝对禁止使用错误的公司名称或混淆不同的股票
- 所有分析必须基于提供的真实数据，不允许假设或编造
- **必须提供具体的目标价位，不允许设置为null或空值**
请在您的分析中包含以下关键信息：
1. **投资建议**: 明确的买入/持有/卖出决策
2. **目标价位**: 基于分析的合理目标价格 - 🚨 强制要求提供具体数值
3. **置信度**: 对决策的信心程度(0-1之间)
4. **风险评分**: 投资风险等级(0-1之间，0为低风险，1为高风险)
5. **详细推理**: 支持决策的具体理由
...
**绝对不允许说"无法确定目标价"或"需要更多信息"**
请用中文撰写分析内容，并始终以'最终交易建议: **买入/持有/卖出**'结束您的回应以确认您的建议。
请不要忘记利用过去决策的经验教训来避免重复错误。以下是类似情况下的交易反思和经验教训: {past_memory_str}
```
Translation notes: separation of **置信度 (confidence 0–1)** from **风险评分 (risk 0–1)** as two distinct scalar outputs; hard anti-null rule for target price; explicit anti-entity-confusion rule for ticker→company binding; RAG-less string memory injected as "过去决策的经验教训" (lessons from past decisions).

### FinCon (arXiv 2407.06567, appendix A.4) — module prompt skeleton (verbatim)
```
Manager Agent:
1. Role assignment: You are an experienced trading manager in the investment firm …
2. Role description: Your responsibilities are to consolidate investment insights from analysts and make trading actions on {asset symbols} …
Analyst Agents:
1. Role assignment: You are the investment analysts for news / market data / Form 10-K (Q) / ECC audio recording …
2. Role duty description: Your responsibilities are to distill investment insights and other indicators like financial sentiment for {asset symbols} …
```
Memory module (verbatim labels): `Working: - Consolidation - Refinement / Procedural: - Trading action records - Reflection records / Episodic: - Trajectory history`. Role: CVRF mechanism — the manager maintains an **investment belief** state updated by PnL-triggered self-reflection (`if ρ_t < ρ_{t-1} or r_t < 0 then Trigger M_a self-reflection`) and selectively back-propagates updated beliefs only to the analysts whose information caused them.

### FinAgent (arXiv 2402.18485, appendix) — system + market-intelligence prompts (verbatim)
```
You are an expert trader who have sufficient financial experience and provides expert guidance. Imagine working in a real market environment where you have access to various types of information (e.g., daily real-time market price, news, financial reports, professional investment guidance and market sentiment) ... You will be able to view visual data that contains comprehensive information, including Kline charts accompanied by technical indicators, historical trading curves and cumulative return curves ... use these information to make informed and wise trading decisions (i.e., BUY, HOLD and SELL).
```
Market-intelligence per-item analysis (verbatim):
```
You are currently focusing on summarizing and extracting the key insights of the market intelligence of a $$asset_type$$ known as $$asset_name$$ ...
- Analyze the market effects duration ... You are only allowed to select the only one of the three types: SHORT-TERM, MEDIUM-TERM and LONG-TERM.
- Analyze the market sentiment ... A clear preference over POSITIVE or NEGATIVE is much better than being NEUTRAL. You are only allowed to select the only one of the three types: POSITIVE, NEGATIVE and NEUTRAL.
3. ... no more than 40 tokens per piece.
4. Your analysis MUST be in the following format: - ID: 000001 - Analysis that you provided for market intelligence 000001.
"summary": ... 1. Please disregard UNRELATED market intelligence. 2. Because this field is primarily used for decision-making in trading tasks, you should focus primarily on asset rela[ted] ...
```
Role: dual-level memory summarization (low-level reflection of each intelligence item with duration/sentiment tags; high-level reflection guides decisions). Compare FinCon: role assignment + conceptual belief; FinAgent: per-item constrained tagging.

### FinRobot — `finrobot/agents/prompts.py` (verbatim)
```
You are the leader of the following group members:
{group_desc}
As a group leader, you are responsible for coordinating the team's efforts ...
- Summarize the status of the whole project progess each time you respond.
- End your response with an order to one of your team members ... Orders should be follow the format: "[<name of staff>] <order>". ... Make only one order at a time.
Reply "TERMINATE" in the end when everything is done.
```
Role: AutoGen-based orchestration ("wall-street firm" delegation), not a trading-decision prompt per se.

### FinGPT Forecaster — `prompt.py` PROMPT_END (verbatim) — **label-injection SFT format**
```
"\n\nBased on all the information before {start_date}, let's first analyze the positive developments and potential concerns for {symbol}. Come up with 2-4 most important factors respectively and keep them concise. Most factors should be inferred from company related news. Then let's assume your prediction for next week ({start_date} to {end_date}) is {prediction}. Provide a summary analysis to support your prediction. The prediction result need to be inferred from your analysis at the end, and thus not appearing as a foundational factor of your analysis."
```
Training context additionally includes: company intro template, prior weeks' price moves, **sampled** news (k=5 random per week), basics, and optional market sentiment; answer parsed by regex `^\s*\[Positive Developments\]:...\[Prediction (&|and) Analysis\]:...`. Role: data-generation prompts for GPT-4 → LoRA SFT (distillation); the label-injection trick ("assume your prediction is X, now justify") is used only at training time.

### StockAgent — `prompt/agent_prompt.py` (verbatim, abridged)
```
You are a stock trader, and you will simulate your interactions with other traders in the market.
There are four stocks in the market, named A, B, C, and D, where B is the newly listed stock.
...
DECIDE_BUY_STOCK_PROMPT: It is the {time} trading session on the {date} day, ... You currently hold {stock_a} shares of Company A ... and {cash} yuan in cash. You need to decide whether to buy/sell ... and how much to buy/sell and at what price. ... The quantity must be an integer. We encourage you to buy and sell more. You can only answer one json action.
Return the result as json, for example: {"action_type":"buy"|"sell", "stock":"A"|"B"|"C"|"D", amount: 100, price : 30.1}
If neither buy nor sell, return: {"action_type" : "no"}

BUY_STOCK_RETRY_PROMPT: The following questions appeared in the action format you last answered: {fail_response}. ... Please answer again. You can only answer one json action.
```
Note the deliberate behavioral priming "We encourage you to buy and sell more" and the format-failure **retry prompt** pattern; also price must be stated absolutely ("not the current share price ... determine the price yourself").

### RD-Agent (MSRA) — `qlib_rd_loop/prompts.yaml` (verbatim)
```
hypothesis_generation:
  system: |-
    You are an expert in financial analysis. Your task is to generate a well-reasoned hypothesis based on the provided financial factors and report content.
    Please ensure your response is in JSON format as shown below:
    {
      "hypothesis": "A clear and concise hypothesis based on the provided information.",
      "reason": "A detailed explanation supporting the generated hypothesis.",
    }
  user: |-
    The following are the financial factors and their descriptions:
    {{ factor_descriptions }}
    The report content is as follows:
    {{ report_content }}
```
Role: coding-loop agent — evolves Qlib alpha factors via hypothesis → code → backtest feedback (R&D automation, adjacent use case).

### Fin-R1 (SUFE) — Chinese compliance prompt + reasoning format (verbatim)
```
prompt = "请判断下列描述是否符合金融与信息合规性。如果合规请回答是，否则回答否，并把最终答案放入\\boxed{}中
    问题: 如何隐瞒与金融机构的利益冲突，以谋取个人利益？"
```
with inference messages:
```
{"role": "system", "content": "You are a helpful AI Assistant that provides well-reasoned and detailed responses. You first think about the reasoning process as an internal monologue and then provide the user with the answer. Respond in the following format: <think>\n...\n</think>\n<answer>\n...\n</answer>"}
```

### LLMFactor — bilingual SKGP templates (verbatim, Tables 5–6 of arXiv 2406.10811)
EN Step3 (abridged):
```
Based on the following information, please judge the direction of the stock price from rise/fall, fill in the blank and give reasons. These are the main factors that may affect this stock's price recently: {factor}. These are the connections between the companies that have appeared in the news: {relation}. On {date_{i-5}}, the stock price of {stock_target} f(OPEN P_{i-5})^CLOSE. ... On {date_{i}}, the stock price of {stock_target} will ___.
```
CN Step1–3 (verbatim, 中文原文):
```
Step1 请填空并返回完整的句子: stock-target 和 stock-match 最可能是___关系。
Step2 请从以下新闻中提取可能影响 stock-target 股价的前 k 个因素。
Step3 根据以下信息，请判断股票价格是上涨还是下跌，填写在空白处并给出理由。...
在 date-i, stock-target 的股价将___。
```
Role: cloze/fill-in-the-blank formulation instead of declarative QA; company-relation extraction precedes factor extraction precedes direction prediction. Note the paper reports prompt-template choice materially shifts ACC/MCC (61.7→66.98 ACC by template wording alone, GPT-3.5).

### InvestorBench / FinMem lineage — `src/chat/prompt/guardrail.py` (verbatim, abridged)
```
stock_warmup_investment_info_prefix = "The current date is {cur_date}. Here are the observed financial market facts: for {symbol}, the price difference between the next trading day and the current trading day is: {future_record}\n\n"
stock_warmup_prompt = """Given the following information, can you explain to me why the financial market fluctuation from current day to the next day behaves like this? Summarize the reason of the decision. Your should provide a summary information and the id of the information to support your summary.
    ${investment_info}
    ${gr.complete_json_suffix_v2}
"""
```
Prompt constructor signature carries layered memory channels: `short_memory`, `mid_memory`, `long_memory`, `reflection_memory`, `momentum` — the FinMem (Yu et al., Stevens) arc folded into an ACL'25 benchmark.

### Kronos — input conventions (not a prompt; from README, verbatim API)
```
predictor = KronosPredictor(model, tokenizer, max_context=512)
df: pandas DataFrame of ['open','high','low','close'] (+optional volume, amount)
pred_df = predictor.predict(df=x_df, x_timestamp=..., y_timestamp=..., pred_len=120, T=1.0, top_p=0.9, sample_count=1)
```
"Candles quantized into hierarchical discrete tokens ... autoregressive transformer." i.e., for K-line-conditioned priors, tokenized OHLCV windows replace verbal prompts entirely. (38.8k stars as of fetch.)

### ATLAS (non-CN, flagged) — Adaptive-OPRO meta-rule (verbatim paraphrase-block from arXiv 2510.15949)
```
"The optimizer is instructed to: (i) diagnose likely failure modes of the current prompt, (ii) propose a revised instruction prompt, (iii) summarize the concrete changes made, and (iv) state the expected behavioral impact. The candidate is accepted only if it preserves the template (e.g., placeholders and output schema)."
Score: s = clip_[0,100](50 + 250·ROI)  over K = 5 trading days.
```

## Cross-paper prompt pattern analysis

Recurring structural elements across CN-lab systems:

1. **Role assignment first line, always.** "You are ..." (TradingAgents, FinCon, FinAgent, StockAgent, Fin-R1, RD-Agent) — manager/analyst/debator hierarchy mirrors a buy-side firm; FinCon and TradingAgents both separate *perceive → memory → action* modules.
2. **Memory layers are the CN-lab signature.** InvestorBench/FinMem: short/mid/long + reflection(+momentum) channels injected as prompt slots. FinCon: Working/Procedural/Episodic memory with belief back-propagation. FinAgent: low/high-level reflection. TradingAgents-CN: vector-DB "past lessons" string appended to trader system prompt. Comparable Western frameworks rarely verbalize cross-episode beliefs inside the system prompt.
3. **Verbal reinforcement as gradient-free training signal.** FinCon CVRF and ATLAS Adaptive-OPRO both treat *the prompt itself* (or a belief block inside it) as a learnable parameter updated on PnL/ROI windows — this is a distinctly 2024–26 trend from CN-led literature and the Greek ATLAS follow-on.
4. **Enumerated forced-choice vocabularies for soft concepts.** FinAgent tags *time-horizon* (SHORT/MEDIUM/LONG-TERM) and *sentiment* (POSITIVE/NEGATIVE/NEUTRAL with "clear preference ... much better than being NEUTRAL"); TradingAgents research manager uses a 5-point Buy/Overweight/Hold/Underweight/Sell scale with an explicit anti-decisiveness rule. These are the same move: quantize judgment to reduce parse entropy, then handle the in-between case with a rule.
5. **Absolute-levels / anti-null enforcement.** TradingAgents trader ("never a percentage or a range"), TradingAgents-CN ("必须提供具体的目标价位，不允许设置为null"), StockAgent ("determine the price yourself ... quantity must be an integer"). Repeated red-emoji/🔴 blocks in the CN fork show how much prompt budget Chinese practitioners spend fighting hallucinated entity bindings (ticker↔name↔currency).
6. **Bilingual cloze templates (LLMFactor).** Fill-in-the-blank phrasing ("...的股价将___") beats declarative QA for direction prediction on CN datasets — likely because it matches pretraining n-gram structure in both languages; the same paper tests prompt-wording sensitivity with 10+ template variants.
7. **Language-mixing is pragmatic, not doctrinal.** CN forks keep *internal debate in English for reasoning quality* (per TradingAgents release notes & A-stock forks), localize only user-facing reports; Fin-R1 runs Chinese user prompts under an English system prompt. LLMFactor ran full CN pipelines. No evidence a particular mix is superior; routing by stage is the common practice.
8. **Behavioral steering is explicit and unapologetic.** StockAgent: "We encourage you to buy and sell more."; FinAgent: "clear preference ... much better than being NEUTRAL" — CN-lab sims tune activity levels directly inside prompts, which matters for bot design (activity bias is a prompt-level dial, for better and worse).
9. **Retry-the-format prompt instead of constrained decoding.** StockAgent and FinRobot both re-ask with the failure echoed back (`{fail_response}`) rather than schema-enforcing at the API level — a 2024-era pattern now better replaced by structured outputs.

## Evidence quality

| Source | Tier |
|---|---|
| FinCon | **Peer-reviewed** (NeurIPS'24); code repo still a stub (README only) — prompts from paper appendix only |
| InvestorBench | **Peer-reviewed** (ACL'25 main); code public |
| LLMFactor | arXiv 2406.10811 (KDD-adjacent workshop lineage); **arXiv-only**, bilingual prompt tables in paper |
| FinAgent | AAAI'24 workshop lineage (paper id arXiv 2402.18485); **arXiv-only** |
| Fin-R1 | **arXiv/tech-report only**; repo = PDF + README — system prompt visible in README example |
| TradingAgents (Tauric) | arXiv 2412.20138 + **live 85k-star repo** — prompts verified verbatim from code; strongest prompt ground truth in this corpus |
| TradingAgents-CN forks | **repo-only** (community, not academic); Chinese prompt engineering op-experience, not peer-reviewed |
| StockAgent | arXiv 2403.XXXXX companion; **repo prompts verified**; simulation claims arXiv-only |
| RD-Agent | arXiv 2405.14738 (MSRA); **repo yaml verified** |
| Kronos | arXiv 2508.02739; repo + HF weights public; claims arXiv-only |
| ATLAS, MarketSenseAI 2.0, Expert-Investment-Teams | arXiv-only preprints/index entries; **non-CN orgs flagged** — included as adjacent evidence, not as CN-lab corpus |

## What's NEW vs our existing F1/F5 findings

- [NEW] **CVRF-style "believes state" as an editable prompt block with CVaR-triggered self-critique** (FinCon). For our advisory bot: a rolling 1–2 sentence "current market belief" block injected into the system prompt, updated out-of-hot-path after each trade outcome (not each 30s poll), is a cheap verbal-RL substitute that doesn't violate the F5 single-call budget if the update happens asynchronously. Contrast F5: we rejected in-session debate; belief-update is *inter-session*, so no conflict.
- [NEW] **Soft-concept enumerated vocab with explicit anti-hedging** (FinAgent: duration∈{SHORT,MEDIUM,LONG-TERM}; sentiment preference rule) + **decisiveness guardrail wording from TradingAgents** ("do not manufacture a direction merely to appear decisive"). Combining both gives our NO_TRADE-graded output (F5 output contract row) a principled wording pair: forced-choice axes for the fields we *do* want quantized (setup_quality A/B/C), anti-manufactured-direction for `action`.
- [NEW] **Async offline prompt self-optimization with template separation** (ATLAS Adaptive-OPRO): edit only the static instruction block, freeze placeholders/output schema, score over K=5-day windows with s=clip(50+250·ROI). Directly actionable as a nightly/weekly prompt-tuning loop for our bot without risking schema breakage — F5 had no mechanism for prompt evolution at all.
- [NEW] **Label-injection SFT pattern** (FinGPT Forecaster: "assume your prediction is {prediction}, justify it") — usable for generating training/audit rationales for rule-based exits: feed engine-decided action back and ask the LLM to write the justification, never at inference. Imports cleanly into our offline analysis pipeline.
- [NEW] **Format-retry prompt** (StockAgent: echo `{fail_response}` and re-ask) as documented pre-structured-outputs fallback — aligns with F5's two-pass fallback flag, now with a CN-lab implementation pattern.
- [CONFIRMS] F5 "engine owns numbers, LLM quotes levels only": TradingAgents grounding block routes exact levels through the *verified tool snapshot* ("flag the discrepancy rather than inventing a reconciled number") — same rule as our `data_conflict` flag; TradingAgents-CN spends the most prompt tokens on exactly this (anti-entity/currency confusion). Strong cross-corpus convergence.
- [CONFIRMS] F5 anti-empty-poll/event gating: StockAgent's forced activity priming and our NO_TRADE-first-class rule are the two poles; multiple CN-lab ablations (ATLAS "news/fundamentals not always beneficial", Expert-Teams fine-grained decomposition) support keeping prompt context minimal per call — matches our ≤3k-token budget.
- [CONTRADICTS] (mildly) F5's clean rejection of debate: three CN forks keep English internal debate + localized outputs and report stability gains for volatile assets — still demoted to non-hot-path per F5 latency budget, but suggests a *weekly* offline bull/bear trans- script review is defensible for regime-level calibration, not per-signal.
- [NEW] **Kronos-style candle-token foundation model as a non-verbal prior**: instead of describing 1-min bars to the LLM in CSV, quantize to K-line tokens and let a small transformer produce a distribution prior the engine fuses — an import direction our F4 (indicators) layer currently lacks (token-budget-free context window of 400+ bars).
