# C03: CN prompt playbooks (Zhihu/CSDN/Juejin…)

Scan date: 2026-09-16. Coverage: CSDN/GitCode, Juejin, Zhihu专栏, CNBlogs, Tencent Cloud dev community, Kimi official docs, Longbridge Academy, 55188 forum, practitioner blogs (junxinzhang, vcai, jxxy). 15 sources, all URLs verified search-visible. Verbatim CN prompts preserved; gloss in italics.

## Source table — # | title | platform | author tier | URL | core idea

| # | Title | Platform | Author tier | URL | Core idea |
|---|-------|----------|-------------|-----|-----------|
| 1 | 大模型分析公司实战：一套提示词模版全方位拆解基本面与护城河 | vcai.cn (小V学投资) | Retail-educator blogger, methodical | https://vcai.cn/index.php/prompt-20260522/ | 4-element prompt doctrine: 角色设定+结构框架+思维链指引+防幻觉约束; three full templates (基本面三层扫描 / 波特五力护城河 / 四维度挑刺) with 〖事实〗vs〖判断〗 tagging |
| 2 | 【AI+量化实战 #01】AI不是股神？用大模型辅助量化研究的正确姿势与Prompt框架 | CNBlogs (量化分析码农) — mirror: wsisp.com/helps/104914.html | Quant-dev practitioner | https://www.cnblogs.com/quantitative/p/22901245 | "IT化金融 Prompt" 四段式: 角色限定/输入格式化/任务明确化/输出约束; engine computes metrics, LLM only narrates; explicit can/can't-do table |
| 3 | 金融投研智能体设计 (official investment-research agent teardown) | Kimi API Platform docs | Vendor (Moonshot AI), enterprise | https://platform.kimi.com/docs/hosted-agents/official-investment-research-agent | 6-role multi-agent (研究分析师/基本面建模师/回测工程师/组合风险/市场策略/资金流) + 复核层 + judge panel; two-stage routing, ContextEnvelope, guardrails incl. 严禁编造, fact/inference separation, prefix-numbered citations |
| 4 | Qwen3.5单GPU股票筛选实战: llama.cpp部署与结构化输出 | CSDN (weixin_34169322) | Quant-dev hobbyist w/ benchmarks | https://blog.csdn.net/weixin_34169322/article/details/162160401 | 3-layer constraint prompting for deterministic JSON: inline JSON-Schema in system, role lock (10年量化研究员), assistant-prefix priming `{"stocks":[`; claims 98.4% schema success Qwen vs 83.7% Llama-3 |
| 5 | DeepSeek量化选股实操指南：从提示词到通达信公式落地 | CSDN (weixin_30906185) | Practitioner, 176-scenario tested claim | https://blog.csdn.net/weixin_30906185/article/details/96415585 | Five-segment prompt (目标/时间范围/…→输出公式), four named failure traps: vague time windows, slang terms (量能), undeclared definitions, unmarked cross-period refs; demand fully quantified thresholds |
| 6 | DeepSeek 量化交易实战：用标准化提示词模板实现 AI 辅助交易决策 | CSDN/GitCode (weixin-npy8264926) | Retail-trading blogger | https://deepseek.csdn.net/69f073e054b52172bc70869b.html (mirror gitcode.csdn.net/69f073e00a2f6a37c5a692ed.html) | Full verbatim "A股顶级游资量化策略员" mega-template: market-sentiment classification stage → execution plan → T+1 position management → hard stops; explicit A股 T+1 rules in Output Constraints; personalization slot ({stock_code}, {close}, {turnover_ratio}…) |
| 7 | AI量化交易实战（三）：多智能体Prompt工程——如何让Bull和Bear Agent真正"吵"起来 | junxinzhang.com | Quant-dev practitioner | https://junxinzhang.com/ai-quant-multi-agent-prompt-engineering/ | Shows naive bull/bear prompts collapse into "和稀泥" (muddy agreement); 6 fixes: role anchoring with loyalty red-lines, evidence mandate, 3-round rebuttal protocol, adversarial-level calibration (L1–L4 ↔ temperature 0.3–0.9), meta-cognitive self-audit, neutral judge |
| 8 | 【小工具】丰富的股票AI提示词 deepseek | 55188 理想论坛 | Retail forum hobbyist | https://www.55188.com/thread-40005923-1-1.html | Verbatim anti-hallucination system block: no invented data, all citations user-supplied or verifiable, forced "这是基于当前数据的推测" / "数据有限，判断可能存在偏差" disclosure labels |
| 9 | AI分析股票 技术指标…智能体提示词 (可直接放入System或User) | CSDN (kingtok) | Project-dev hobbyist | https://blog.csdn.net/kingtok/article/details/158620317 | Paste-ready indicator-rulebook system prompt: MA/MACD/KDJ/RSI/BOLL/OBV/背离/ATR thresholds spelled out; "技术面不直接下结论"—engine computes, LLM interprets; conclusion reserved for cross-signal synthesis pass |
| 10 | AI炒股教学：DeepSeek+大模型辅助股票分析与复盘完整指南（2026版） | GitCode/CSDN | Retail educator | https://gitcode.csdn.net/6a0c1807662f9a54cb75a4db.html | 5 scenario templates: K-line morphology coach, 3-sentence 财报速读 (盈利质量/现金流/红旗), pre-trade "压力测试" logic review, structured 复盘 (认知偏差 question), learning-path plan; usage mistakes table |
| 11 | 10万美元真实厮杀，DeepSeek用39%收益碾压全场…NoF1实盘赛 | Juejin | Media/hype blogger | https://juejin.cn/post/7563512910044790793 | "复原版" (reverse-engineered, NOT official) autonomous-trading-agent system prompt: risk budget ≤15%/trade, ≤3.5x leverage, SL ≤0.6%, cool-down after 3 losses, Sharpe-rollback self-correction. Evidence status: unverifiable attribution |
| 12 | AI交易员第一步，用Deepseek跑通量化交易 | jxxy.net 觉醒AI知识库 | Practitioner (agent-ops) | https://www.jxxy.net/ai/articles/deepseek-quant-trading-step1/ | Agent-level instruction prompts: data-QC checklist (timestamp dupes/gaps/unclosed bars), no-lookahead `shift(1)` mandate, write-operation firewall (no order tools during backtest), "do not describe backtest as future prediction" |
| 13 | 一键生成股票报告：AI分析师镜像实战体验 | CSDN (weixin_36483050) | Dev hobbyist (Ollama mirror) | https://blog.csdn.net/weixin_36483050/article/details/157701717 | "持牌证券分析师" system prompt: fixed 3-segment report (近期表现/潜在风险 3× verifiable items/未来展望 短中长 +trackable signal each); ban invented numbers—fallback to qualitative words; language constraint (no English abbreviations) |
| 14 | 腾讯云智能体开发平台×DeepSeek：股票分析低代码应用实践 | Tencent Cloud dev community | Vendor platform team | https://cloud.tencent.com.cn/developer/article/2506614 | Task-typed interactive prompt catalog: each query class (基本面/技术/策略/监控/数据管理) carries its own 回复示例 + 回复格式 spec—per-intent format anchoring at enterprise scale |
| 15 | 在2026用AI选股炒股真的可行吗？130%收益背后的真相 | Zhihu 专栏 | Content-farm tier (SEO) | https://zhuanlan.zhihu.com/p/2029927164049608904 and /p/2029883900923729074 | akshare→factor rank→DeepSeek API; prompt asks 行业轮动机会/低PE策略适用性/风险点 + fixed output header 市场判断（看多/看空/震荡). Headline claims (DeepSeek 130% "Alpha Arena") are marketing folklore |
| 16 | 2033121/astock-trading-agents | GitHub (CN community fork of TradingAgents) | Open-source hobbyist | https://github.com/2033121/astock-trading-agents | 4 analysts (技术/新闻/舆情/基本面) → 多空辩论 → 三方风控辩论 → 五级评级 (买入/增持/持有/减持/卖出); Pydantic-typed outputs, akshare/tushare/东方财富 triple-fallback |

## Verbatim prompt library

### E1 — Source #1 (vcai, fundamental three-layer scan). Purpose: full-company scan; `{{}}` slots for name/code/range.
```
【角色设定】
你是一位从业15年的资深基本面分析师，擅长从财报数据中识别企业的真实经营状况。你的分析风格严谨、克制，绝不夸大，绝不省略风险。
【分析框架与思维链指引】请严格按照以下三层次递进分析，先给出每层的具体数据，再进行逻辑推演，最后给出综合判断。
## 第一层：盈利质量 — 1. 列出近3-5年的营业收入、归母净利润及其同比增速 2. 毛利率、净利率、ROE历年数据 3. 判断：盈利增长是来自收入扩张还是成本压缩？
## 第二层：财务健康度 — 资产负债率/流动比率/速动比率；经营现金流与净利润对比（比值是否持续>0.7?）；
## 第三层：运营效率 — 存货周转天数、应收账款周转天数…
## 综合结论 — 1-10分综合评分；3个亮点+3个风险点；3个需进一步核实的问题
【防幻觉约束】
- 财务数据必须来自公开年报，如数据不可得请明确标注"需人工核实"
- 所有判断必须基于数据推演，标注〖事实〗与〖判断〗
- 避免使用"优秀""出色"等主观形容词，改用具体数据支撑
```
*Gloss: 15-yr-analyst persona; forced layer-by-layer CoT (data→inference→synthesis); anti-hallucination = public-annual-report sourcing only, "需人工核实" escape hatch, fact-vs-judgment tags, ban adjectives without numbers.*
Verdict: **ADAPT** — keep the three-layer skeleton, "需人工核实" escape hatch, and 〖事实〗/〖判断〗 tagging (excellent grounding device); drop the persona (R08/F5 evidence says personas don't help); numeric rules like 现金流/净利润>0.7 are A-share-centric, re-derive for NIFTY names.

### E2 — Source #2 (CNblogs, four-segment "IT-ified finance prompt"). Purpose: price/volume digest, zero advice.
```
【角色限定】你是一位拥有10年A股量化研究经验的金融数据分析师，擅长把量价数据翻译成可验证的投资逻辑摘要。你的回答必须基于以下输入数据，不做股价预测，不提供买卖建议，只输出事实梳理与风险提示。
【输入格式化】股票代码…数据区间…共{n}个交易日…最新收盘价…区间最大回撤…年化波动率…20日均线（最新价偏离{pct20}%）…
【任务明确化】1. 概括该股票在过去n个交易日的走势特征。2. 基于均线位置，判断当前价格处于短期/中期趋势的什么位置，并说明这是否构成交易信号（明确说"不是信号"也可以）。3. 列出2-3条投资者在看这段数据时最容易误读的陷阱（例如把波动当趋势、把回撤当利空等）。
【输出约束】- 不输出买入/卖出/持仓建议。- 不预测未来股价。- 总字数控制在250字以内。
```
*Gloss: engine pre-computes all stats inline in the prompt; LLM narrates only; negative-task space is explicit ("不是信号" allowed); misreading-traps section is a calibration gem.*
Verdict: **ADAPT** — the "may explicitly answer no-signal" license and the "most-misread traps" output field are both directly importable; aligns 1:1 with F5's engine→LLM input schema.

### E3 — Source #3 (Kimi official investment-research agent). Purpose: multi-agent routing + guardrails.
```
系统提示词核心（official config, verbatim system field）：
"你是一个二级市场投研助手。
- 所有数据经数据路由获取，输出标注数据来源与取数日期。
- 无法取数或无法核实的内容列入「待核实」并注明原因，严禁编造。
- 只做研究分析，不执行任何交易。
- 区分事实、推断与不确定信息。
- 交付物保存到 output/ 目录。"
路由规则：两段式路由（question-router先判任务类型，只选一个牵头主技能；路由只产元数据不产交付物）；上下文信封（市场、语言、币种、会计准则、数据质量策略、产出目标、是否需人工确认）；护栏：不执行任何交易；缺失数据不当作零；回退数据、陈旧数据、幸存者偏差与重述风险必须披露；建议与事实、计算、假设分开呈现；来源、论断、事项分别使用固定前缀编号，保证整条委派链上的引用可以回溯。
```
*Gloss: vendor-grade guardrails: dated-source labeling, "待核实" quarantine drawer instead of fabrication, fact/inference/uncertainty separation, missing-data-is-not-zero rule, survivorship/restatment-bias disclosure duty, prefix-numbered citation IDs for end-to-end traceability.*
Verdict: **ADOPT** (concepts) — 待核实-list, "missing ≠ 0", and separate-render of fact/computation/assumptions/advice all belong in our advisor prompt. The 6-agent committee itself contradicts F5's single-agent verdict for intraday latency; keep ideas, not topology.

### E4 — Source #4 (CSDN Qwen3.5, deterministic screening JSON). Purpose: machine-readable stock screen.
```
<|im_start|>system
你是一名有10年经验的量化研究员，专注A股基本面分析。所有输出必须严格遵循以下JSON Schema：
{ "stocks": [ { "code": "字符串，格式为'XXXXXX.SZ'或'XXXXXX.SH'，不可省略后缀",
    "name": "字符串，公司全称",
    "reason": "字符串，≤50字，仅陈述客观事实，不出现'可能''或许'等模糊词",
    "confidence": "浮点数，0.0-1.0，根据财报数据确定性打分" } ],
  "summary": "字符串，≤100字，总结筛选逻辑执行情况" }
<|im_end|>
<|im_start|>user
筛选出2024年一季度净利润同比增速＞150%，且机构持股比例较2023年末提升＞5%的科创板股票
<|im_end|>
<|im_start|>assistant
{"stocks":[
```
*Gloss: schema-with-typed-annotations inline (suffix preservation, ≤50-char fact-only reason, ban hedging words "可能/或许", float-typed confidence), plus assistant-prefix priming `{"stocks":[` to kill pre-amble text. Claimed 98.4% schema success (self-reported, single-model test).*
Verdict: **ADAPT** — the annotation style inside schema strings (banned-hedging-words, char caps, dtype literal rules) is better than R08 P8's bare JSON mode; priming trick only works on open-weight completion APIs, not needed for GPT-classStrict-JSON.

### E5 — Source #6 (CSDN 游资 template). Purpose: aggressive momentum trade plan. Verbatim skeleton:
```
# Role: A股顶级游资量化策略员(专攻10万->1000万复合增长)
# Strategy Philosophy: 只做主升浪，不做震荡市；只做龙头，不做跟风股。
# Market Context: 实时行情快照 — 收盘价{close}元 | 涨跌幅{pct_chg}% | 换手率{turnover_ratio}% | 量比{volume_ratio} | MACD {macd_signal} | RSI…关键价位: 上方压力位{key_pressure}元 | 下方支撑位{strong_support}元
# Task: 执行【A股主升浪】交易决策指令
## 1. 市场情绪与地位判别 — 板块效应? 多空博弈属于[缩量回调确认/高位放量分歧/平台放量突破/弱势下跌]哪种? 主升浪启动的概率（0-100%）
## 2. 盘中执行计划 — [竞价抢筹/分时回踩买入/突破追涨/减仓观望/空仓等待]; 若封板概率>70%是否打板?
## 3. T+1动态仓位管理 — 加仓条件/减仓条件/日内T+0价差建议
## 4. 硬性风控与退出机制 — 止损位精确数值(逻辑:跌破MA10或关键支撑); 第一目标位减仓50%; 跌停板→次日竞价清仓触发条件
# Output Constraints:
1. 严格符合A股交易规则: 必须考虑T+1制度
2. 数据精确性: 所有价格、比例保留小数点后2位
3. 拒绝中庸建议: 强势市场必须给出60%以上的重仓建议；弱势市场必须给出明确的空仓警示
4. 每个决策都必须有对应的技术面或基本面依据
```
*Gloss: full decision pipeline in one prompt: regime classification from a closed enum → action from closed enum → next-day add/trim rules → absolute stop/targets; forces 2-decimal prices, forces a T+1 rule, forbids fence-sitting, justifications mandatory.*
Verdict: **ADAPT the chassis, REJECT the soul** — the closed-enum regime classifier + action-menu + absolute-price stop/target + "every decision needs a cited basis" + forced nonzero-hedge structure are exactly F5's output contract done in Chinese. But "拒绝中庸建议/必须60%重仓" and the 10万→1000万 游资 persona are fortune-seeker folklore that R08 P5's evidence (persona-switch risk) punishes; for NIFTY options advisory we keep the structure with a mandatory FLAT/REDUCE license and retail-safe sizing caps.

### E6 — Source #7 (junxinzhang, bull/bear debate repair kit). Purpose: stop agents agreeing with each other. Key verbatim fragments:
```
[Bull red-lines] 你的绝对红线：- 你绝不会说"看空方说得有道理" - 你绝不会用"但是从另一个角度看"来自我削弱 - 即使承认风险存在，你也必须立即给出为什么风险被高估的论证
[Evidence mandate] 每个论点必须遵循：【论点】一句话观点 【数据支撑】具体数字、日期、来源（≥2个独立数据点）【逻辑链】≤3步推理 【反脆弱性】这个论点在什么条件下会失效？
[3-round protocol] 第一轮立论(各3论点) → 第二轮交叉质证，反驳格式：【被反驳论点】原文引用【攻击角度】数据过时/逻辑跳跃/忽略变量/幸存者偏差【反驳证据】【致命问题】对方论点成立所需前提可靠吗 → 第三轮终极答辩：必须承认对方最难反驳的论点；必须回答"如果你错了，最可能错在哪里"
[Adversarial calibration] L1蓝筹-stable→temp0.3"请提出不同看法" … L4事件驱动→temp0.9"假设对方完全错误，找出致命漏洞"
```
Verdict: **ADAPT** — the structured-rebuttal container (quote-then-attack-angle-enum incl. 幸存者偏差/survivorship bias) and the forced "where would I be wrong" closer map neatly onto R08 P6 but add the attack-angle enum we don't have. The L1–L4 temperature dial is CN-folklore-adjacent (no ablation shown); treat as unproven.

### E7 — Source #8 (55188 forum, shared anti-hallucination block). Purpose: let model predict, but label everything.
```
你现在扮演一名A股市场分析师，可以基于已有数据进行分析、判断和预测。唯一核心要求：不得编造任何数据，不得使用不存在或无法确认来源的信息。
数据使用规则：1 所有引用的数据必须来自用户提供或明确可确认来源 2 若某部分信息不确定，可以进行推测，但必须明确说明"这是基于当前数据的推测" 3 若数据不足，应说明"数据有限，判断可能存在偏差"
预测要求:…必须说明依据（基于哪些数据或结构）; 不得使用虚构信息支撑预测
底线规则：如果某个结论缺乏数据支持，则必须明确说明，而不是补充假数据
```
*Gloss: instead of banning speculation, it license-tags it: fixed disclosure strings for "inference" and "insufficient data"; bottom-line rule = announce unsupported conclusions rather than fabricate.*
Verdict: **ADOPT** — the two fixed disclosure tokens ("这是基于当前数据的推测" / "数据有限，判断可能存在偏差") are a cheaper, LLM-reliable version of complicated confidence calibration. No eval shown (forum post) → treat mechanism as plausible, not measured.

### E8 — Source #13 (CSDN licensed-analyst mirror system prompt). Purpose: fixed 3-segment report.
```
你是一名持牌证券分析师，专注科技股研究。请严格按以下三段式结构生成报告：
1.【近期表现】聚焦最近30个交易日价格、成交量、技术形态、相对指数表现；
2.【潜在风险】列出3项具体、可验证的风险点（避免"宏观风险""政策不确定性"等空泛表述）；
3.【未来展望】分短期（3–6个月）、中期（12个月）、长期（3年以上）三层展开，每层至少1个可追踪信号。
禁止编造具体数值（如"净利润增长23.7%"），可用"显著提升""趋于放缓"等定性表述。全文使用中文，禁用英文缩写（如"EPS"需写为"每股收益"）。
```
*Gloss: ban generic risk boilerplate by blacklisting phrases ("宏观风险" etc.); demand one *trackable signal* per horizon; when data absent → qualitative vocabulary, never invented numbers.*
Verdict: **ADAPT** — boilerplate-phrase blacklist + "one trackable signal per horizon" is a sharp anti-fluff device for our daily-brief outputs. The qualitative-fallback rule is dangerous for an advisory (reads as false precision) — prefer E3's 待核实 quarantine instead. [Partly contradicts F5: F5 wants engine numbers or nothing.]

### E9 — Source #12 (jxxy agent-ops instructions). Purpose: trading-agent data hygiene. Verbatim rules:
```
1. 只使用 OKX market skill/CLI 查询行情。…6. 检查时间戳重复、缺失值、时间缺口、排序方向和K线是否已经收盘，写入 logs/market-check.json。
[回测约束] 1. 只允许读取本地数据和执行Python回测；2. 不调用账户、下单、改单、撤单…任何交易写入工具；3. 不使用未收盘K线；4. 不省略手续费、点差、滑点和仓位上限；5. 不把回测结果描述成未来收益预测；7. 用shift(1)把信号推迟到下一根K线执行。
```
Verdict: **ADOPT as system-prompt section for our agent toolchain** — write-tool firewall during backtests, unclosed-bar ban, shift(1) no-lookahead, cost-floor mandate, and "backtest ≠ forecast" phrasing rule. These are agent-permission prompts, an axis R08/F5 largely ignores.

### E10 — Source #5 (CSDN 通达信, four prompt-traps). Verbatim trap fixes:
```
错误: "选出最近上涨的股票" → 正确: "选出过去5个交易日内，收盘价较5日前上涨超过8%，且今日收盘价高于20日均线的股票"。必须量化所有时间窗口和阈值。
错误: "找量能放大的股票" → 通达信没有"量能"函数 → "今日成交量大于过去5日均量150%"
跨周期: 周线逻辑需显式声明 WEEKDAY 切换
```
Verdict: **ADAPT** — for us this becomes: ban retail-slang ("momentum", "breakout") in the engine→LLM contract unless each is bound to a computed field; same lesson as F5's typed input schema, independently discovered C-side.

## Pattern synthesis — recurring motifs across CN playbooks

1. **Four-part prompt spine**: 角色 + 结构化输入（占位符/信封） + 任务拆解（枚举式步骤） + 输出约束 (sources 1,2,3,5,6,13). Every serious CN playbook converges on the same quadruple F5 uses — evidence of convergent evolution, not copying.
2. **Anti-hallucination as first-class section** 【防幻觉约束】: three flavors recur — (a) ban fabrication + source-date labeling (1,3,8,13); (b) fixed disclosure tokens for inference/insufficient-data (8, Kimi's 待核实); (c) fact/judgment inline tags 〖事实〗〖判断〗 (1). CN practitioners obsess over 编造 numerics more than EN playbooks do — likely because CN models confidently emit plausible-sounding financial stats.
3. **Closed-enum classification before verdict**: regime/sentiment enums ([缩量回调确认/高位放量分歧/…], attack-angle enums, 看多/看空/震荡 header) — force classification before free text (4,6,7,15).
4. **消息/公告/财报 summarization blocks**: yes, present — 3-sentence 财报红旗 format (10), 政策语义拆解 (wallstreetcn 王开 course, paid, not fully verbatim), 季度公告 impact markdown (1's 红旗 pattern). Less standardized than price prompts.
5. **情绪/舆情 analysis prompt blocks**: present but thin — mostly 换手率/量比/龙虎榜 proxies embedded in market-context slots (6,9) rather than standalone social-sentiment prompts; Kimi's 资金流分析师 role and astock-trading-agents 舆情 agent are the structured exceptions. No Nordmark-style options-chain sentiment prompting found in CN sources — a genuine gap; CN retail prompting is equity/T+1-centric and rarely touches options Greeks.
6. **Persona inflation is ubiquitous** (从业15年/持牌分析师/顶级游资) despite zero ablation in 14/16 sources — folklore-laden.
7. **Engine-computes-LLM-narrates** division (2,9,12) appeared independently and explicitly ("技术面不直接下结论…结论由LLM综合", CSDN#9) — strongest cross-cultural confirmation of F5's core architecture.

## What's NEW vs our F5/R08 findings

- **[CONFIRMS R08-P1]** Verified-numbers-only grounding: 4 independent CN sources (1,3,8,13) reinvent it; CN-specific twist = fact/judgment inline tags 〖事实〗〖判断〗 (E1) — cheap and worth importing.
- **[CONFIRMS R08-P6]** Bull/bear debate + neutral judge; CN adds the attack-angle enum (数据过时/逻辑跳跃/忽略变量/幸存者偏差) and forced "最难反驳的对方论点" concession — [NEW] refinement worth importing for rationale quality (not for the final vote, per R08-P9).
- **[CONFIRMS R08-P8 / F5 two-pass]** Format-tax mitigation; [NEW] CN variant: assistant-prefix priming `{"stocks":[` + hedging-word blacklist inside schema annotations (E4) — useful for open-weight deployments (Qwen/DeepSeek local), irrelevant for strict-JSON APIs.
- **[CONFIRMS R08-P7]** Indicator diet/rulebook prompting (source 9's paste-ready interpretation rules) — same as curated-menu approach.
- **[NEW] Quarantine-not-fallback pattern**: Kimi's 「待核实」 list and 55188's fixed disclosure tokens — a third way between "invent" and "refuse"; our advisor should carry a 待核实/UNVERIFIED output bucket with reasons.
- **[NEW] "Missing data ≠ zero" + bias-disclosure duty** (survivorship/restatement/staleness must be declared) — explicit in Kimi guardrails; F5 validation layer has nothing comparable.
- **[NEW] Agent-permission prompting** (jxxy): write-tool firewall during backtests, unclosed-bar ban, shift(1) no-lookahead, "backtest ≠ forecast" phrasing — a whole prompt surface (ops safety) F5 doesn't cover.
- **[NEW] Misreading-traps output field** (source 2: list 2-3 ways a retail user would misread this data) — directly improves advisory safety for the R11 personas; no EN analogue in R08.
- **[NEW] T+1/settlement-constraint slot in Output Constraints** — generalizable lesson: put the market's settlement microstructure rules inside the prompt (for us: weekly expiry timing, STT, lot-size rounding), not in a side doc.
- **[CONTRADICTS F5 persona-ban, resolves in our favor]** CN folklore leans heavily on personas; the one CN source with any evidence-toned claim (source 4, schema accuracy) strips persona down to one clause; consistent with R08 finding personas don't help.
- **[CONTRADICTS retail-CN practice]** "拒绝中庸建议，必须重仓" (E6-source6) vs R08-P5 evidence that forced conviction personas degrade performance — ban this motif.

## Folklore sightings — CN-retail-trading superstitions about prompts (ban list)

1. **"调教好了比人聪明" claims**: 55188 title "deepseek调校好了比小龙虾聪明2点" — no benchmark, pure forum boasting. Ban: persona/conviction prompts justified by anecdote.
2. **Headline return attribution**: Zhihu/NoF1 "DeepSeek 130%/39%收益" articles attribute leaderboard PnL to a "复原版" (reconstructed, unofficial) system prompt — correlation-as-causation; the prompt is fabricated by the blogger. Ban: importing "winning prompts" from trading-competition journalism.
3. **Price-prediction demand blocks**: Tencent Cloud catalog legitimizes "预测未来30天的支撑位和压力位" as a query type with a confident numeric reply format — encodes hallucinated precision. Ban: any prompt that demands a future price number without an uncertainty token.
4. **重仓强制 clauses** ("强势市场必须给出60%以上的重仓建议"), 游资 10万→1000万 persona — fortune-content structure dressed as prompt engineering. Ban outright.
5. **涨停/打板 probability queries** ("若封板概率>70%是否执行打板") — asks LLM to produce a calibrated event probability it cannot know. Ban: uncalibrated probability outputs without a model behind them.
6. **Single-word magic**: "第一性原理" inserted into prompts to force original reasoning (source 1 admits it's a talisman against copied 研报套话) — benign, but treat as style hint, not mechanism.
7. **Adversarial-level ↔ temperature ladder (L1-L4)** presented as a calibrated system with zero ablation (source 7) — plausible but folklore-tier; test before adopting.
