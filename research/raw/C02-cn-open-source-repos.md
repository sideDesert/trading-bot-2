# C02: CN open-source trading repos

Research agent C02 — Chinese open-source LLM↔market-data/trading ecosystem. Date: 2026-09-16. All star counts / push dates fetched live from the GitHub REST API today; every URL below was fetched. Searches run in Chinese: 大模型 炒A股 开源, DeepSeek 量化 github, QMT easytrader 大模型, gitee deepseek 股票 agent, akshare 大模型. Headline finding: **the domestic scene defaults to DeepSeek, treats LLMs as a scheduled "慢思考" analysis layer (nobody wires them into tick loops), and the #1 operational pitfall Chinese builders document is NOT auth expiry (as in India) but free-data-source instability + per-minute/per-point rate caps on Tushare.**

## Repo table — # | name | org | stars | last-updated | URL | LLM used | data source | cadence

| # | name | org | stars | last-updated | URL | LLM used | data source | cadence |
|---|------|-----|-------|--------------|-----|----------|-------------|---------|
| 1 | TradingAgents-CN | hsliuping | 31,824 | 2026-07-24 | https://github.com/hsliuping/TradingAgents-CN | DeepSeek (default, "比GPT-4便宜90%以上"), DashScope/Qwen, OpenAI, Google, OpenRouter 60+ | AKShare + Tushare + BaoStock cascade (A股/港股/美股); Finnhub/yfinance for US | On-demand single-stock analysis runs (multi-agent graph, ~dozens of LLM calls, minutes per run); daily data sync into MongoDB+Redis; no tick loop; tool-call counter caps agent loop at 3 calls |
| 2 | TradingAgents-astock | simonlin1212 | 3,347 | 2026-09-05 | https://github.com/simonlin1212/TradingAgents-astock | DeepSeek / Qwen / Doubao (OpenAI-compatible) | mootdx (TCP 7709 直连通达信) + 东财/新浪/同花顺/百度股市通 HTTP + akshare — "全免费直连，零外部服务依赖" | On-demand analysis; 龙虎榜/北向资金 are intraday-refresh tools the agent calls when triggered; no autonomous loop |
| 3 | FinGPT ecosystem | AI4Finance-Foundation | 21,253 | 2026-09-14 | https://github.com/AI4Finance-Foundation/FinGPT | Fine-tuned LoRA (LLaMA2-7B/ChatGLM2-6B); FinGPT-Forecaster-Chinese variant exists (ChatGLM2, A股 data) | Finnhub + yfinance; Chinese variant: A股行情+资讯 | Forecaster paradigm = **weekly**: sample ≤5 news/d from trailing 1–3 weeks, predict next week's move bucket (U1/D1…5+ = 0–1%…5%+) |
| 4 | alphastream | lc2panda | 890 | 2026-08-07 | https://github.com/lc2panda/alphastream | **DeepSeek V4** + LangGraph, 14 agents + 4 大师人格 (巴菲特/芒格/林奇/达摩达兰) | AKShare + BaoStock **双源冗余主备切换** (+Wind可选); 17 search engines; RSS×6 + crawler (雪球/东财股吧/财联社) | SSE streaming of full decision chain (工具调用→推理全程可视化); Flask+Gunicorn; Redis cache w/ memory fallback; daily/morning reports |
| 5 | QuantTradingSystem | guandada123 | 0 | 2026-09-07 | https://github.com/guandada123/QuantTradingSystem | DeepSeek multi-agent w/ **模型调度**: Deepseek-V4-Flash (0.06x) for data cleaning → DeepSeek-V3.2 (0.29x) for sentiment → Pro for multi-agent debate | Tushare (TUSHARE_TOKEN required) + AKShare; MiniQMT for execution | Realtime index quotes pushed via WebSocket **every 3s**; AI analyze = on-demand POST /api/v1/ai/analyze/{ts_code}; 每日复盘 scheduled; microservices (PostgreSQL/QuestDB/Redis/RabbitMQ) |
| 6 | ai-hedge-stock-futures | mapicccy | 94 | 2025-10-31 | https://github.com/mapicccy/ai-hedge-stock-futures | DeepSeek/OpenAI/Groq/Anthropic (DEEPSEEK_API_KEY documented first) | **akshare (free)** replacing paid FinancialDatasets; A股+期货+美股 | CLI batch runs (poetry run python src/main.py --ticker 601360); risk agent is pure-Python position sizing (no LLM) |
| 7 | financial-team-ashare | vango-do | 1 | 2026-03-11 | https://github.com/vango-do/financial-team-ashare | Multi (OpenAI-compatible) | Structured local retrieval (行情/估值/财务/公告/新闻) — **Retrieval-First**: 每次LLM调用前强制本地检索 | Pipeline per run: 7 大师分析师 → 风险管理 (T+1/涨跌停10%/20%校验) → 组合经理 **严格多数票** (LLM只解释理由,不投票) |
| 8 | deepseek-harness-quant | yuanwang589-dev | 180 | 2026-08-17 | https://github.com/yuanwang589-dev/deepseek-harness-quant | DeepSeek HARNESS runtime (LLM = 驱动层; 写死引擎 = 执行层; 数据系统 = 事实层) | Tushare + PIT data w/ local cache + 覆盖率分年核查 | **T+1 低频 decision chain**: L0择时 → L2 Pitch审批 → T+1开盘执行; 一字板过滤; 五池远期验证 T+1/5/20/60 |
| 9 | qmt-trading-skill (+ qmt-bridge) | atorber | 24 | 2026-08-14 | https://github.com/atorber/qmt-trading-skill | Cursor / Claude Code (21 Agent Skills, natural-language driven) | miniQMT/xtquant via **QMT Bridge** HTTP+WebSocket server co-located with QMT client on Windows; LAN-exposed | Bridge streams quotes over WebSocket; skills trigger on chat demand ("今天账户盈亏多少"); 复盘调度 scheduled daily; PM2 daemon on Windows host |
| 10 | qmt-mcp-server | nnquant | 46 | 2025-04-02 | https://github.com/nnquant/qmt-mcp-server | Any MCP-capable model ("赋予大模型执行股票交易的能力！") | 迅投QMT broker terminal (real money!) | MCP over SSE `http://localhost:8001/sse`; tools = 账户查询/持仓/下单/撤单, invoked per chat turn; README warns name→code resolution is unreliable across models |
| 11 | QMT-MCP | guangxiangdebizi | 249 | 2025-07-17 | https://github.com/guangxiangdebizi/QMT-MCP | MCP-connected AI assistants | XTQuant/QMT (实盘+模拟) | FastMCP server; strategy generation + execution + backtest modules; multi-layer risk controls built-in |
| 12 | qmtcli | 2233admin | 6 | 2026-08-16 | https://github.com/2233admin/qmtcli | Any language/agent ("让 AI 用 JSON 跟 QMT 聊 A 股") | QMT/xtquant auto-discovered from broker install dir (falls back QMT-bundled SDK) | stdin/stdout JSON RPC; `server` mode = JSONL line protocol; `watch` = streaming quote push (基于 _whole_quote) until Ctrl+C; stdio MCP mode; **ordering calls pass 护栏** |
| 13 | ashare-agent | sfeng49 | 5 | 2026-08-17 | https://github.com/sfeng49/ashare-agent | DeepSeek Harness (dsh) | AKShare + backtrader; explicit-deny on estimation | 每日晨报 (scheduled, scripts/morning_report.py → output/daily/YYYY-MM-DD-morning.md), 交易复盘 on trades; **AGENTS.md 铁律: 不做买卖决策/禁"目标价·必涨"措辞/数字必须来自脚本/拿不到就明说绝不估算编造** |
| 14 | akshare_stock_analysis (Gitee mirror culture) | samwan_9996 | n/a (gitee) | gitee repo | https://gitee.com/samwan_9996/akshare_stock_analysis | Optional multimodal model via ModelScope (Qwen-VL class, reads generated K-line chart PNGs) | akshare | Full-market batch scan (多线程, top-k scoring); `--ai` flag uploads charts to LLM for analysis — pattern: deterministic scoring THEN vision-LLM explanation |

## Verbatim prompt extracts — per repo, original language preserved

### #1 TradingAgents-CN — market analyst system prompt (`tradingagents/agents/analysts/market_analyst.py`)

```python
"system",
"你是一位专业的股票技术分析师，与其他分析师协作。\n"
"📋 **分析对象：**\n"
"- 公司名称：{company_name}\n"
"- 股票代码：{ticker}\n"
"- 所属市场：{market_name}\n"
"- 计价货币：{currency_name}（{currency_symbol}）\n"
"- 分析日期：{current_date}\n"
"- 标的约束：{instrument_context}\n"
"🔧 **工具使用：**\n"
"你可以使用以下工具：{tool_names}\n"
"⚠️ 重要工作流程：\n"
"1. 如果消息历史中没有工具结果，立即调用 get_stock_market_data_unified 工具\n"
"2. 如果消息历史中已经有工具结果（ToolMessage），立即基于工具数据生成最终分析报告\n"
"3. 不要重复调用工具！一次工具调用就足够了！\n"
"4. 接收到工具数据后，必须立即生成完整的技术分析报告，不要再调用任何工具\n"
"📝 **输出格式要求（必须严格遵守）：**\n"
"## 📊 股票基本信息 ... ## 📈 技术指标分析 ... ## 📉 价格趋势分析 ... ## 💭 投资建议\n"
"⚠️ **重要提醒：**\n"
"- 不要使用'最终交易建议'前缀，因为最终决策需要综合所有分析师的意见\n"
"请使用中文，基于真实数据进行分析。",
```
Companion hard-guard in code (anti-loop, worth copying verbatim as a *pattern*):
```python
tool_call_count = state.get("market_tool_call_count", 0)
max_tool_calls = 3  # 最大工具调用次数
logger.info(f"🔧 [死循环修复] 当前工具调用次数: {tool_call_count}/{max_tool_calls}")
```

### #1 TradingAgents-CN — risk manager judge prompt (`tradingagents/agents/managers/risk_manager.py`)

```python
prompt = f"""作为风险管理委员会主席和辩论主持人，您的目标是评估三位风险分析师——激进、中性和安全/保守——之间的辩论，并确定交易员的最佳行动方案。您的决策必须产生明确的建议：买入、卖出或持有。只有在有具体论据强烈支持时才选择持有，而不是在所有方面都似乎有效时作为后备选择。力求清晰和果断。

决策指导原则：
1. **总结关键论点**：提取每位分析师的最强观点，重点关注与背景的相关性。
2. **提供理由**：用辩论中的直接引用和反驳论点支持您的建议。
3. **完善交易员计划**：从交易员的原始计划**{trader_plan}**开始，根据分析师的见解进行调整。
4. **从过去的错误中学习**：使用**{past_memory_str}**中的经验教训来解决先前的误判...确保您不会做出错误的买入/卖出/持有决定而亏损。

交付成果：
- 明确且可操作的建议：买入、卖出或持有。
- 基于辩论和过去反思的详细推理。

标的约束：
{instrument_context}
---
**分析师辩论历史：**
{history}
---
专注于可操作的见解和持续改进...请用中文撰写所有分析内容和建议。"""
```
And the production-hardening tail (LLM-failure → deterministic fallback decision, never crash):
```python
# 如果所有重试都失败，生成默认决策
if not response_content:
    response_content = f"""**默认建议：持有** ... 由于技术原因无法生成详细分析...建议对{company_name}采取持有策略。"""
```
(max_retries=3, time.sleep(2) between retries; prompt-size/token accounting logged every call — 中文约1.5-2字符/token.)

### #5 QuantTradingSystem — tiered multi-agent prompts (`strategy-service/services/prompts/multi_agent_prompts.yaml`, hot-reloadable, separated from code "便于非程序员调优")

```yaml
# 共享系统提示词（固定前缀→100% KV Cache 命中）
base_system: |
  你是一位专业A股投资分析师，隶属于多智能体交易协作系统。
  分析框架要素：
  - 明确的交易信号：BUY/SELL/HOLD
  - 0-100的置信度评分
  - 至少3个风险点
  - 完整的逻辑推理链
  - 关键指标数据
fundamental: |
  你的专长：基本面分析
  关注指标：PE/PB/ROE/营收增长率/利润增长率/负债率 ...
money_flow: |
  你的专长：资金面分析
  关注指标：北向资金/主力资金流/大单成交/融资融券 ...
bull_debate: |
  你是一位看涨（多头）研究员。请基于分析结果从多头视角进行辩论。
  要求：
  1. 找出支持买入的核心理由（至少3条）
  2. 对看空观点提出反驳
  3. 列出潜在的上涨催化剂
  4. 风险评估与应对
  输出JSON格式：argument（论点）、evidence（证据列表）、confidence（置信度0-100）。
bear_debate: |
  你是一位看跌（空头）研究员。请基于分析结果从空头视角进行辩论。 ...
```
Model-tiering table from README: 数据清洗/指标计算 → Deepseek-V4-Flash 0.06x；新闻情绪分析 → DeepSeek-V3.2 0.29x；多智能体辩论 → Pro。

### #2 TradingAgents-astock — 游资追踪师 (hot-money tracker; an A股-specific agent our pipeline has no analog of) (`tradingagents/agents/analysts/hot_money_tracker.py`)

```python
system_message = (
    "你是一位专注于 A 股市场的游资与资金流向追踪分析师。你的核心任务是通过分析成交量异动、股东变化和市场新闻，追踪主力资金和游资的动向，判断短期资金博弈格局。"
    "⚠️ A 股游资分析框架："
    "- **量价异动识别**：突然放量（日成交量超过 20 日均量 2 倍以上）、换手率飙升（>10% 为异常活跃）、涨停板放量/缩量特征"
    "- **龙虎榜信号**：通过股东变化和交易数据推断机构/游资席位动向。知名游资席位的买入是强势信号"
    "- **连板分析**：首板放量 vs 缩量的含义不同（放量代表分歧，缩量代表一致）；二板确认强度；三板以上进入「妖股」模式需特别谨慎"
    "- **板块资金流向**：资金从一个板块撤出往往流入另一个板块，跟踪轮动节奏有助于预判下一个热点"
    ...
    "📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]："
    "1. 近 5 日成交量变化趋势（放量/缩量/平稳）"
    "2. 当日北向资金净流入金额（沪股通 + 深股通）"
    "3. 个股主力资金净流入（超大单 + 大单）"
    "4. 所属概念板块及当日板块涨幅"
    "5. 当日是否上榜热门股及题材归因"
    "6. 资金面总体判断"
)
```
Note the outer scaffold stays in English (fork's deliberate choice — README: "中文报告（内部辩论保持英文以保证推理质量）"):
```python
"You are a helpful AI assistant, collaborating with other assistants."
" If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
" prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
```

### #3 FinGPT-Forecaster — weekly-prediction system prompt (`fingpt/FinGPT_Forecaster/app.py:57`)

```python
SYSTEM_PROMPT = "You are a seasoned stock market analyst. Your task is to list the positive developments and potential concerns for companies based on relevant news and basic financials from the past weeks, then provide an analysis and prediction for the companies' stock price movement for the upcoming week. " \
    "Your answer format should be as follows:\n\n[Positive Developments]:\n1. ...\n\n[Potential Concerns]:\n1. ...\n\n[Prediction & Analysis]\nPrediction: ...\nAnalysis: ..."
```
Key structural trick in `prompt.py` (PROMPT_END): prediction is framed as an *assumption the model must justify a posteriori* — "let's assume your prediction for next week ... is {prediction}. Provide a summary analysis to support your prediction. The prediction result need to be inferred from your analysis at the end, and thus not appearing as a foundational factor of your analysis." — this is how they build RLSP-style LoRA training data (input = news, label = realized move bucket mapped via map_bin_label: "up by 0-1%", "down by 4-5%", "more than 5%").

### #13 ashare-agent — AGENTS.md investment iron rules (verbatim from README)

```
铁律约束——不做买卖决策、禁用「目标价/必涨」措辞、数字必须来自脚本、数据拿不到就明说
```
Skills are SKILL.md-format dsh plugins: `ashare-data`（数据获取）、`ashare-report`（每日晨报）、`ashare-review`（交易复盘）. Review prompt skeleton: "分析 data/trades/ 下过去一年的交割单：1. 总体：胜率、盈亏比、平均持仓天数、总收益 vs 同期沪深300 2. 亏损归因：亏损…"

### #12 qmtcli — guardrail framing (README verbatim) — the CN equivalent of our "LLM never owns the order"

```
给 QMT / XtQuant 装一层稳定的接口，让任何语言、任何 Agent 都能安全稳定的调用它。
一句话：让 AI 用 JSON 跟 QMT 聊 A 股——行情账户随便查，下单有护栏。
...对只读调用、escape hatch、下单、撤单做明确标记
```

## Architecture patterns observed (repeated ≥2 repos get named patterns)

1. **"委员会/debate parliament"（辩论委员会）** — ≥5 repos (TradingAgents-CN, TradingAgents-astock, QuantTradingSystem, alphastream, financial-team-ashare): N specialist analysts (technical/fundamental/money-flow/sentiment[+政策/游资/解禁]) → bull vs. bear debaters → judge (risk manager/组合经理) with **explicit no-default-hold rule** ("只有在有具体论据强烈支持时才选择持有，而不是...作为后备选择"). Debate history is passed as a single concatenated `history` string to the judge.
2. **"护栏桥"（broker bridge with guardrails）** — ≥4 repos (qmt-trading-skill/qmt-bridge, qmt-mcp-server, QMT-MCP, qmtcli): the broker SDK (xtquant/miniQMT) is **never imported by the LLM process**; it lives in a daemon co-located with the logged-in Windows QMT client, exposed over HTTP/WebSocket/SSE-MCP/stdio-JSON with read-only vs. order commands explicitly tagged. Rationale quoted verbatim from qmtcli: xtquant is buried in the broker's install dir; broker's silent client upgrades change DataFrame serialization — isolate it in a restartable subprocess. This is CN's answer to "don't let the model own the socket/account".
3. **"免费源级联+健康自检"（data-source cascade with boot-time self-test）** — ≥4 repos (TradingAgents-CN, alphastream AKShare+BaoStock双源主备, TradingAgents-astock mootdx+东财+新浪+同花顺, dmsobtl/dsh-quant-workbench 新浪/东财/Yahoo/Binance): provider priority chain, boot-time token/context probe (TradingAgents-CN logs 步骤1→4.1: DB token → .env token → stock_basic test call → auto-degrade to next source), 60s timeout + 3-retry AKShare wrapper.
4. **"慢层LLM / 快层引擎分离"（slow LLM layer vs deterministic fast layer）** — ≥5 repos (deepseek-harness-quant minimal-trust 三层: 驱动层LLM/执行层写死引擎/事实层数据; finGPT weekly forecaster; ai-hedge-stock-futures keeps risk sizing 100% pure Python; StockAgent scores first, vision-LLM explains second; ashare-agent analysis-only). Nobody in CN runs LLMs on ticks either — same as our F4.
5. **"结构化判决 schema"（structured verdict）** — ≥4 repos: BUY/SELL/HOLD + 0-100 置信度 + ≥3 风险点 (QuantTradingSystem base_system), FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** prefix-stop convention (TradingAgents family), JSON {argument, evidence, confidence} for debaters. Uniform verdict schema is what makes the parliamentary aggregation code-parseable.
6. **"kimino KV-cache prompt 分层"** — QuantTradingSystem puts a fixed BASE_SYSTEM prefix ahead of each specialist suffix explicitly for "100% KV Cache 命中"; prompts live in hot-reloadable YAML outside Python so non-programmers can tune them.
7. **"A股制度注入 prompt"（market-institution injection）** — ≥3 repos embed T+1, 涨跌停(10%/20%), 手数, ST flags, 龙虎榜 frames directly into system prompts or as instrument_context (TradingAgents family via `build_instrument_context`, financial-team-ashare risk gate, deepseek-harness-quant 一字板过滤 in backtest engine).
8. **SSE/streaming transparency** — alphastream streams every tool call + reasoning step to frontend over SSE; vibe check in CN land = show the debate, not just the verdict.
9. **Analysis-only advisory + 免责 framing** — nearly every repo banner: "不构成投资建议，仅供学习研究"; several (ashare-agent, StockAgent) hard-ban buy/sell directives entirely — matches our advisory-bot scope.

## Documented pitfalls from issues/READMEs (auth expiry, rate limits, data gaps — anything about their flavors of "token dies at 3:30AM")

- **Tushare points + per-minute caps = CN's token-expiry equivalent** (TradingAgents-CN problems #109/#412/#561): free/low-point tokens rate-limit to "**您每分钟最多访问该接口1次**" and block whole endpoints ("抱歉，您没有接口访问权限") — failure appears at *boot test*, killing startup. Maintainers built a 4-step cascade (DB token → .env token → probe call → auto-degrade to akshare) precisely because tokens/points rot without notice. Issue #109 user demand: "tushare很多接口都受积分限制，建议默认别用这个了."
- **akshare silent garbage data** (TradingAgents-CN issue #267): when akshare price parse fails it **returns a hardcoded fallback price=10**, destroying downstream PE/PB (寒武纪 reported PE 4 vs real hundreds); user complaint "设置根本不生效" because source-selection preference was ignored and akshare short-circuited tushare (issue #714). Maintainer verdict: "ak的数据不准，建议正式用，就用tushare". Class of bug: **fallback defaults inside scrapers poison derived metrics** — validate derived values against ranges, never trust silent defaults.
- **akshare/tushare empty-DataFrame & short-circuit bugs** (#139, #714): empty df from one source must trigger degrade, but preference ordering was buggy — the multi-source manager needs an explicit probe-then-commit protocol, not try/except soup.
- **Free public APIs have 3–5s delay** (dsh-quant-workbench README): 新浪/东财 free feeds lag 3–5s; US Yahoo 15min — they publish a **latency table per source**; treat "free" as "stale-tolerant context only".
- **miniQMT is Windows-bound and dies with the client** (qmt-bridge/qmtcli/qmt-trading-skill): xtquant only works inside the broker's logged-in client on the same Windows machine → the entire bridge pattern (daemon + PM2 + LAN HTTP/WS + PM2 restart) exists to contain this instability. Broker silent client updates change SDK pandas/numpy serialization — qmtcli isolates SDK in a restartable subprocess with a version-stable JSON contract. Client login session expiring = "券商自己的3:30AM".
- **LLM name→code resolution is unreliable** (qmt-mcp-server README warning): "由于不同大模型的差异，部分情况下可能无法正确转换股票名称到股票代码，使用股票名称下单请谨慎" — always resolve symbol via a search/master-list tool before order construction.
- **Agent tool-call infinite loops** (TradingAgents-CN market_analyst hard-coded 死循环修复 counter, max 3 calls): LLMs re-call tools forever on flaky data; they cap calls in state and force report generation — replicate this guard.
- **Hallucinated numbers** (ashare-agent AGENTS.md): "所有数字来自数据接口实际输出，拿不到就明说，绝不估算编造" + TradingAgents-astock's 必采清单 with explicit "[数据缺失: xxx]" annotation requirement — both are in-prompt anti-hallucination contracts for missing-data gaps.
- **Solo-maintainer fragility** (TradingAgents-CN README, 27k-31k stars): "一直由我一个人开发维护...每次发布新版本...仍然会有一些隐藏的bug没有被发现" + 218 open issues — high-star ≠ production-safe; pin versions, expect data-source breakage PRs.
- ** traded-real-money disclaimers**: every execution repo (qmt-*) ships risk-control modules and paper/sim first; qmt-mcp-server is real-money-capable with only natural-language guardrails — the riskiest pattern observed; all others interpose deterministic checks (护栏/风控七道/多层风险控制).

## What's NEW vs our existing F4/R12 findings — tagged [NEW]/[CONFIRMS]/[CONTRADICTS]

- [CONFIRMS] **Slow-layer LLM, deterministic signals** (F4 demoted #8 "LLM banned from tick loop"): entire CN lineage converges identically — deepseek-harness-quant writes it as architecture (驱动层/执行层/事实层), FinGPT runs weekly, ai-hedge forks size positions in pure Python. Strong cross-culture corroboration.
- [CONFIRMS] **Isolation of order path from any flaky dependency** (R12 zAck isolated-worker, qmt bridge cluster): same instinct — broker SDK in a daemon/process the LLM can't crash or rate-limit.
- [CONFIRMS] **Boot-time auth probe + loud failure** (F4 ops spec post-auth verification; R12 upstox-auth-pro): CN does 4-step Tushare token probing at startup; same lesson, different credential type (points/quota vs 3:30AM token death).
- [NEW] **Source-selection hijack bugs** — CN's dominant pitfall class: scraper cascades where the wrong source wins and silently-default values (=10 price) corrupt derived metrics. Our stack (Upstox single paid source) doesn't have this exact bug, but the PCR-from-payload lesson generalizes: **recompute derived values from primitives; make preference ordering enforced and logged** [partially CONFIRMS R12 PCR pitfall, extended].
- [NEW] **Per-source public latency table** — CN repos document feed staleness per source (3–5s free HTTP feeds) as a first-class design input, not an afterthought. Add a staleness column to our F4 ingestion spec.
- [NEW] **Debate-judge prompt with anti-HOLD-default clause** — "don't pick HOLD as a fallback when everything seems fine" is a concrete, verbatim-importable clause for our advisory LLM judge; our R08/adversarial prompts don't have it.
- [NEW] **Verdict schema: signal + confidence 0-100 + ≥3 risks** — QuantTradingSystem base_system is a ready-made system-prompt contract; CN consensus schema. Import for our analyst snapshot prompt (helps downstream parse/aggregate).
- [NEW] **Anti-loop tool-call counter in agent state** (max 3) — concrete guard seen in production CN code; add to our agent loop if/when we use tool-calling.
- [NEW] **Missing-data annotation contract** — "[数据缺失: xxx]" mandatory field list (必采清单) is a cleaner anti-hallucination mechanic than generic "don't hallucinate" wording; pairs with our staleness flags.
- [NEW] **Hot-reloadable YAML prompt files tuned by non-programmers + KV-cache-stable shared prefix** — prompt-ops pattern worth adopting if our advisor's prompt set will be iterated by non-devs.
- [NEW] **A股舆情 agents have no NIFTY analog, but the FII/DII + F&O-participant + institutional-flow triangulation in R12 does** — CN 游资/龙虎榜/北向 agents = order-flow-context LLM agents; skips/"游资席位" are available free in CN, whereas NIFTY equivalents (FII/DII cash+F&O, participant-wise OI) exist via NSE/Upstox — so the *agent pattern* ports even though the data shapes differ. [CONFIRMS the value of a dedicated "participant-flow context agent" in our architecture.]
- [CONTRADICTS] **English-internal-debate claim**: TradingAgents-astock upstream README asserts keeping internal debates in English "以保证推理质量", but the same repo's own CN-localized agents (hot_money_tracker) run fully in Chinese with no documented reasoning loss; TradingAgents-CN runs end-to-end Chinese at 31k stars. So: language choice is not a quality blocker for DeepSeek/Qwen-class domestic models — pick user's report language throughout.
- [CONFIRMS] **Market-hours gating** (F4 market-hours gate): CN repos schedule 晨报/复盘 jobs and gate quote collection to trading hours; same practice independently.
- [NEW] **Model-cost tiering inside one pipeline** (Flash for cleaning → mid for sentiment → Pro for debate, with documented cost multipliers 0.06x/0.29x/1x) — a domestic-scale cost-engineering pattern we can map onto whatever mix we self-host vs. call.
