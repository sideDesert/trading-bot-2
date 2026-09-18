# C04: DeepSeek/WeChat/Xueqiu practitioner playbooks

Date compiled: 2026-09-16. Scope: Sino-practitioner LLM-trading playbooks that never surface in English — WeChat 公众号 tutorials (accessed via CSDN/toutiao/aggregator mirrors, noted where so), Xueqiu 雪球 threads, Bilibili tutorials, 理想论坛/QQ-group prompt packs, and GitHub CN projects, centered on the 2025 DeepSeek-R1 boom for A-share trading. All links verified live during this search; no WeChat mp.weixin.qq.com originals were directly fetchable, so mirrored/aggregated copies are cited with the mirror noted.

## Source table

| # | Title | Platform | Author tier | URL | Core idea |
|---|-------|----------|-------------|-----|-----------|
| 1 | DeepSeek量化选股实操指南：从提示词到通达信公式落地 | CSDN blog (weixin_30906185) | Practitioner, heavy user (claims 176 screening scenarios across DeepSeek V2→V4-Pro) | https://blog.csdn.net/weixin_30906185/article/details/96415585 | 5-part prompt template + 4 named pitfalls for turning vague retail jargon (三阶倍量柱, 尾盘) into exact TDX formula code; API params (temp 0.3 / top_p 0.85 / max_tokens ≥2048); test keys have brutal QPS limits |
| 2 | 只用DeepSeek辅助选股3个月，复盘效率大变样 | Toutiao 今日头条 (retail diary; WeChat-style content farm but with concrete workflow) | Retail practitioner, self-reported 3-month live use | https://www.toutiao.com/article/7651788843498291764/ | Full daily cadence: pre-market brief prompt → post-close export 6-column CSV from 通达信 → AI screen → fundamentals filter → 10-min human review → AI-generated TDX formula; iron rule "AI初筛、通达信形态、人脑决策" |
| 3 | A股周度复盘与下周策略 的 DeepSeek 提示词模板 (mirror of CSDN kenter1983/147356963, itself a WeChat 公众号 prompt series) | pswp.cn aggregator ← CSDN ← 公众号 | Template author (runs a "deepseek提示词模板" series) | http://www.pswp.cn/news/902060.shtml (orig: https://blog.csdn.net/kenter1983/article/details/147356963) | Structured weekly-review markdown skeleton: 利多/利空 table, 板块轮动热力图, 北向/内资 flows, 技术面关键点位矩阵, 下周策略九宫格 (仓位×板块×操作), 关键事件日历, 风险提示; user fills 【】 placeholders with week's data |
| 4 | 手把手用 DeepSeek Harness (dsh) 搭一个 A 股 Agent 工作台 | jxxy.net 觉醒AI知识库 (tech tutorial site) | Technical practitioner | https://www.jxxy.net/ai/articles/deepseek-harness-a-share-agent/ | AGENTS.md "投资宪法" (you never decide trades; no 买入/卖出/目标价 wording; cite source+date; numbers only from scripts, never mental math; ask before any write/order) + SKILL.md skills for akshare data/morning report/review; headless mode in crontab = 8:30 auto 晨报, post-close auto 复盘 |
| 5 | yuanwang589-dev/deepseek-harness-quant | GitHub | Ambitious OSS practitioner project | https://github.com/yuanwang589-dev/deepseek-harness-quant | LLM=驱动层 (control/factor-mining/audit), deterministic Python=执行层, PIT data=事实层; 123+ factors w/ 9-step admission + 17 falsification records; five-pool T+1/5/20/60 forward validation; seven risk gates; 7 "牛散" persona dialogues (林园/赵老哥/炒股养家…) whose picks go to forward-validation pool |
| 6 | 使用DeepSeek R1大模型编写迅投QMT的量化交易Python代码 | Tencent Cloud dev community | Practitioner (QMT user) | https://cloud.tencent.com/developer/article/2502546 | Web DeepSeek naively emits miniQMT/xtquant code, NOT 大QMT (ContextInfo/handlebar) code — fix: print QMT docs to PDF, build knowledge base in Tencent ima.copilot, then generate |
| 7 | 【小工具】丰富的股票AI提示词 deepseek | 55188.com 理想论坛 (QQ-group-adjacent retail forum prompt pack) | Anonymous pack collector ("deepseek调校好了比小龙虾聪明") | https://www.55188.com/thread-40005923-1-1.html | Verbatim "A股市场分析师" system prompt: anti-fabrication clauses (不得编造任何数据; mark guesses "这是基于当前数据的推测"; say "数据有限" when thin), structured analysis sections, explicit 底线规则 |
| 8 | 实测3个月AI炒股软件：DeepSeek炒股真的有用吗？ | cnblogs (pcdoctor) | Practitioner, honest sim-log (Oct 2024–Jan 2025, 10万 sim) | https://www.cnblogs.com/pcdoctor/p/19902314 | +8.5% vs 沪深300 (−12.3% max DD) over 3 months with named failure episodes: month 1 lost money because AI did 财报-only analysis with no trend/timing; two AI misjudgments in month 2; "correct way to open AI" only found in month 3 |
| 9 | 在2026用AI选股炒股真的可行吗？130%收益背后的真相 | Zhihu 专栏 | Skeptical commentator | https://zhuanlan.zhihu.com/p/2029883900923729074 | Debunks the "DeepSeek 130% Alpha Arena" viral claim; three structural limits (回测≠未来, 政策市 unpredictability, 过拟合); practical rule = AI做因子选股、人工做风控决策, low leverage / diversify / market-neutral borrowed from 幻方 |
| 10 | 靠DeepSeek一天赚20万元？AI炒股"神话"背后藏猫腻 | 北京日报 (state media investigation) | Journalist investigation | https://xinwen.bjd.com.cn/content/s67b69f7ee4b068c68f100725.html | Documents P&L-claim economy: "用DeepSeek赚15万/20万" videos never show proof; a 190k-follower blogger's 100万 AI portfolio never reported results; livestream funnels convert DeepSeek hype into ¥288 "AI荐股软件" and ¥998 投顾 upsells |
| 11 | DeepSeek API 服务器繁忙 (503/429) 完整处理指南 | SegmentFault | Developer | https://segmentfault.com/a/1190000047789836 | 429=caller-side rate (v4-pro 500 / v4-flash 2500 concurrency) vs 503=DeepSeek-side overload; exponential backoff+jitter; 10-min no-inference server disconnect |
| 12 | DeepSeek服务器繁忙第N次了大家都麻了吧 | CocoLoop community thread | Retail users venting | https://www.cocoloop.cn/t/topic/2503 | 服务器繁忙 is chronic at peak hours; web端限流狠于API; coping = switch provider at peak, "只能半夜用" |
| 13 | 无法命中缓存 / context 131072 exceeded (Claude Code + DeepSeek) | GitHub DeepSeek-V3 issue #1102 | Developer field report | https://github.com/deepseek-ai/DeepSeek-V3/issues/1102 | Real context-window wall: 131072-token hard limit error, forced compact, then ¥38 single-day bill from cache-miss blowup |
| 14 | DeepSeek大模型如何赋能量化选股：指令工程实战指南 | framerc.cn (aggregator of quant-practitioner content) | Practitioner tutorial | http://www.framerc.cn/news/2963933/ | 3 "golden templates" (TDX formula conversion, akshare Python w/ error handling + CSV output, formula-debugging with cause/fix/win-rate-impact); KEY compliance note: never say 帮我选股/推荐股票 — DeepSeek's 合规过滤 refuses; use action verbs 生成/转化/筛选/计算 |
| 15 | AI炒股教学：大模型辅助分析与复盘完整指南（2026版） | gitcode.csdn (mirror; partly an EasyClaw promo) | Tutorial writer / tool vendor | https://gitcode.csdn.net/6a0c1807662f9a54cb75a4db.html | 5 scenario prompts (K-line coach w/ 角色, 财报速读 3-sentence limit, 买入逻辑压力测试, post-trade 复盘 incl. "最大认知偏差是什么", learning-path plan) + 5-misconception table ("不提供上下文直接问" is an error) |
| 16 | Aurora-73/QuantAgent | GitHub | CN OSS, production-grade framing | https://github.com/Aurora-73/QuantAgent | Qlib+vnpy+MCP+Skill; explicit doctrine: "LLM是研究员，不是交易员" — LLM does news/research/daily reports, never order signals/sizing/circuit-breakers; strict permission separation |
| 17 | UU114/AI-QTRD | GitHub | CN OSS (VeighNa 4.0-based) | https://github.com/UU114/AI-QTRD | Natural-language strategy → DeepSeek → executable code on vnpy stack; vnpy.alpha ML module; OptionMaster Greeks tracking exists in the same ecosystem |

Xueqiu note: direct xueqiu.com search for practitioner DeepSeek prompts returns mostly stock-commentary *about* DeepSeek-the-company (IPO, margins) rather than playbooks — the playbook content lives on Xueqiu as links-out to 公众号 originals; the 公众号 originals are mirrored on CSDN/toutiao/pswp/framerc as cited above (S1, S2, S3, S14).

## Verbatim prompt/workflow library

**P1 — "A股市场分析师" system prompt (S7, 理想论坛 pack, excerpted verbatim):**
> "你现在扮演一名 A股市场分析师…唯一核心要求：不得编造任何数据，不得使用不存在或无法确认来源的信息。…若某部分信息不确定，可以进行推测，但必须明确说明'这是基于当前数据的推测'；若数据不足，应说明'数据有限，判断可能存在偏差'。…底线规则：如果某个结论缺乏数据支持，则必须明确说明，而不是补充假数据。"
- English gloss: You are an A-share analyst. Core rule: fabricate nothing. Label every inference as inference; when data is thin, say so. Bottom line: a conclusion without data support must be flagged, never back-filled with fake data.
- **Verdict: ADOPT.** This is the strongest anti-hallucination scaffold in the CN corpus — stricter than anything in our R08 set because it forces explicit epistemic labels ("推测"/"数据有限") inline rather than relying on a generic "be accurate."

**P2 — 盘前简报 prompt (S2, verbatim):**
> "现在为A股盘前时段，请整理今日盘前简报，内容包含：隔夜美股三大指数涨跌幅及波动核心原因、A50期指、人民币汇率最新变动；梳理今日所有影响A股的政策公告、行业利好利空；最后预判今日大盘整体情绪，标注偏多、中性、偏空，全文控制300字以内。"
- Gloss: Pre-market brief: overnight US indices + why, A50 futures, CNY; today's policy/sector headlines; end with one sentiment call (bullish/neutral/bearish); ≤300 chars.
- **Verdict: ADAPT.** For NIFTY: swap in SGX/GIFT NIFTY, USDINR, overnight US close, FII/DII flows; the hard 300-char cap + forced trinary sentiment label is the transferable skeleton (answer-first, bounded length — consistent with our F5 output contract).

**P3 — 盘后六宫格初筛 prompt (S2, verbatim core):**
> "根据附件A股行情数据筛选个股，硬性条件：1.当日涨幅2.5%-6%…；2.换手率4%-18%…；3.单日成交额大于2.5亿…；4.量比大于1.2…；5.剔除ST、*ST、上市不足60天新股。最后按成交额从高到低排序，输出代码、股票名称、入选一句话理由。"
- Gloss: Screen the attached CSV against 5 hard numeric filters; sort by turnover; output code, name, ONE-SENTENCE reason per pick.
- **Verdict: ADAPT.** Transferable pattern: LLM as a *filter over engine-exported CSV*, with "一句话理由" (one-line justification) column — cheap explanation discipline. But note the CSV pre-filter itself could be pure pandas; CN crowd uses the LLM where code would do (see Credibility).

**P4 — 买入逻辑压力测试 prompt (S15, verbatim core):**
> "我准备买入一只股票，买入逻辑如下，请帮我找出逻辑漏洞和风险点：…止损价：买入价 -8%；目标价：买入价 +25%。请从技术面、基本面、风险管理三个维度审查这个逻辑。"
- Gloss: Here is my buy thesis with pre-committed stop (-8%) and target (+25%); attack it from technical, fundamental, and risk-management angles before I act.
- **Verdict: ADOPT.** Pre-mortem as a first-class prompt, requiring the user to state stops *before* the critique — this is an adversarial-check pattern our F5 currently only implements as cross-model vote; a same-model "attack this thesis" pass is a cheaper second opinion for escalations.

**P5 — 交易复盘 prompt (S15, verbatim core):**
> "买入：2026-05-10，均线金叉，价格18.5元；卖出：2026-05-20，未突破前高，止损出局，亏损3%。请分析：1) 我的买入逻辑是否合理？2) 止损设置是否合适？3) 有没有更好的买卖时机？4) 这笔交易最大的认知偏差是什么？"
- Gloss: Post-trade review with timestamps, trigger rationale, outcome; four fixed questions, the last one forcing a *named cognitive bias*.
- **Verdict: ADAPT.** Add to our EOD review job; Q4 (name the bias) is the novel bit vs Western trade-journal prompts.

**P6 — 五段式选股→公式 prompt (S1, structure):** ①目标 ②时间范围(精确到交易日数) ③条件(全部量化阈值) ④输出格式(纯代码/带注释) ⑤边界情况(ST/停牌/次新处理). Plus the four pitfalls: 模糊时间定义 / 混用术语(量能) / 隐含前提未声明(三阶倍量柱 must be defined in REF() terms) / 跨周期引用未标注(周线 needs WEEKDAY).
- Gloss: Never say "recently rising" — say "close +8% over 5 sessions". Define folk-technical jargon in primitive indicator terms before asking for code.
- **Verdict: ADAPT.** Directly applies to our prompt→engine contract: every natural-language instruction to the engine layer should pass this quantize-everything lint. Confirms R08's absolute-levels rule from a totally different culture/source.

**P7 — 合规动词绕过 (S14):** DeepSeek's 合规过滤 refuses "帮我选股/推荐股票"; working verbs are 生成/转化/筛选/计算 ("generate/convert/filter/compute").
- **Verdict: REJECT for our bot's intent, NOTE as risk signal.** We don't want to bypass safety filters; but this tells us refusals are keyword-shaped — our own prompts should be phrased as analysis/formatting tasks to avoid spurious refusals, which is legitimate prompt hygiene.

**P8 — AGENTS.md "投资宪法" (S4, verbatim key clauses):**
> "1. 你永远不做买卖决策，只提供分析和事实。最终判断由我做。2. 禁止使用'建议买入/卖出''目标价''必涨'这类措辞。3. 所有结论必须标注数据来源和日期…绝对不许估算、编造…4. 涉及金额、比例、财务数字，一律以脚本实际跑出来的结果为准，不许口算。5. 任何写入/删除文件、执行下单相关操作，必须先问我。"
- Gloss: Agent constitution: analysis-only, no buy/sell/target-price vocabulary; every claim carries source+date; ALL numbers must come from executed scripts, never mental arithmetic; any write/order requires human confirmation.
- **Verdict: ADOPT almost verbatim** as our system-prompt block. Clause 4 ("不许口算" — no mental math, script output only) is R09's code-as-arbiter rule expressed more operationally than any Western source.

**P9 — 公式调试闭环 (S1, S2):** paste TDX formula-manager *error text/screenshot* back to DeepSeek → model fixes syntax (e.g., lowercase `cross` → `CROSS`) → re-test. Iterative compile-fix loop with the trading software as compiler.
- **Verdict: CONFIRMS** standard tool-loop practice; the CN twist is that the "compiler" is the retail terminal itself and the feedback channel is a screenshot.

## The 盯盘/选股/复盘 loop anatomy — CN daily cadence

The dominant CN retail pattern is **not intraday** — it's a fixed-clock daily loop built around the A-share session (S2 is the most explicit, timestamps included; S4 automates the same loop via cron):

1. **盘前 (pre-open, ~08:30–09:15, or 8:30 cron in S4):** AI brief prompt (P2-style) → go/no-go sentiment for the day. If brief shows macro/policy headwinds, *reduce trade frequency* — the LLM's first job is deciding whether today deserves trading at all.
2. **盘中 (intraday):** essentially no LLM. DeepSeek web is too slow/服务器繁忙 (S11, S12) and retail admits AI can't do 盘口. The only intraday artifact is TDX 预警公式 (alert formulas AI wrote *last night*) firing mechanically. Intraday judgment = human + pre-generated alerts.
3. **盘后 15:05–15:20:** export 6-column CSV from 通达信 → LLM hard-filter screen (P3) → 15–25 candidates → optional fundamentals pass (3yr profit growth, ROE>12%, 资产负债率<60%, 应收账款 vs 营收 growth, 解禁/减持 flags).
4. **盘后 15:20–15:40:** *human* technical review in TDX — pressure levels/筹码, intraday 分时 vs VWAP line, RPS trend. Explicitly labeled "this is the step AI can't replace."
5. **盘后 15:40–15:50:** shortlist 3–5 names back to LLM for next-day plan: per-name support/resistance levels and operation notes → fill personal trade-plan sheet (低吸/观望/止盈/止损 points pre-committed).
6. **Weekly (S3):** structured 周度复盘 markdown template — macro 利多/利空 ledger, sector rotation heatmap, capital flows, strategy 九宫格 (position sizing × sector × operation mode incl. e.g. "5成仓位 = 2防御+2政策催化+1机动"), event calendar, risk section.
7. **Per-trade (P5):** closed-trade review with the 4 fixed questions.

The repeated meta-rule across S2, S8, S9, S16: **AI负责筛选缩池，软件负责形态/计算，人脑负责最终决策** (AI narrows the pool, software computes, human decides). "LLM是研究员，不是交易员" (S16) is the identical Western doctrine arrived at independently.

## Data-feeding patterns

- **CSV from the retail terminal is the canonical feed** (S2): 通达信 → 报表分析 → 历史行情报表 → right-click export CSV, **only 6 columns** (代码/名称/涨跌幅/换手率/成交额/量比), explicit rationale "字段越少，AI筛选速度越快" — field-minimization for speed and reliability. Confirms our F5 mixed-envelope/CSV decision from practitioner side.
- **File upload, not paste**, for the screener (DeepSeek web accepts CSV attachments); paste for short text (financial-statement core numbers, K-line description, trade log).
- **Screenshots are the error channel, not the data channel**: formula-manager error screenshots → code fix (P9). Charts-as-images for analysis appear in tutorial misconceptions tables ("不提供上下文直接问" listed as user error; one tutorial answers "把股票截图发给AI有用吗" with *limited value vs text data*).
- **Knowledge-base PDFs** for platform-specific code (S6): QMT official docs printed to PDF → ima.copilot knowledge base → RAG-grounded code gen, to fix the miniQMT-vs-大QMT confusion. Pattern = ground the model in vendor docs before asking it to write platform code.
- **Script-executed data only in the agent setups** (S4, S5, S16): akshare via Python venv, data落盘 to data/ then read by agent — no numbers typed by the model.
- **Pain points they actually hit** (S11, S12, S13): (a) web UI 服务器繁忙 at peak hours — chronic, community coping = use API not web, or run at night/morning (which conveniently matches their pre-open cron); (b) 429 vs 503 confusion, fixed with exponential backoff + jitter; API concurrency caps (v4-pro 500 concurrent, flash 2500) and test-key QPS clamping that "直接熔断" batch screening (S1); (c) 131,072-token context wall with real money damage — ¥38/day from cache misses after a forced compact (S13); (d) output truncation when max_tokens too small — exclusion clauses (剔除ST) getting cut mid-code (S1).

## Credibility assessment

Grade harshly; the CN ecosystem has a documented P&L-fraud economy (S10):

- **Outright-false/marketing tier (reject all numbers):** "上周靠DeepSeek赚了15万/一天赚20万" short-video claims — S10's state-media investigation found zero verification, and the funnels end in ¥288 "AI荐股软件" and ¥998 投顾 upsells. The "Alpha Arena DeepSeek +130%" viral figure (debunked in S9) is a leaderboard artifact, not a retail-replicable return.
- **Plausible-but-unverifiable tier:** S2's "复盘时间缩短80%，选股容错率明显提升" — no P&L number is claimed at all (deliberately: "不编造暴利收益"), only *efficiency* and *error-rate* claims. Treat efficiency gains (2-3h → 15min daily review) as credible; treat any implied alpha as unproven. S1's "176 scenarios tested" is effort documentation, not results.
- **Best-in-corpus tier:** S8's 3-month sim log (+8.5%, −12.3% DD, and honest month-by-month failure narrative where the AI was *right on fundamentals and wrong on timing*) — small sample, simulated money, but the failure log is what makes it believable. S5's repo is the only source with a *falsification culture*: 17+ factors documented as falsified, five-pool forward validation (T+1/5/20/60) before a strategy is trusted. This is the credibility ceiling in the CN retail corpus and it's still not live-audited P&L.
- **Cross-check with Western evidence:** S9's three limits (backtest≠future, policy-shock unpredictability, overfitting) match R09's contamination findings (R09 S4–S6). Nobody in this corpus — honest or otherwise — demonstrates that an LLM improves *trade selection* beyond being a faster screener/analyst.

## What's NEW vs our F5/R09 findings

- **[NEW] The daily-cadence loop with LLM excluded from intraday**: the CN crowd independently converged on "LLM = pre-market brief + post-close screen/plan; intraday = pre-generated deterministic alerts + human." F5 designs a 30s periodic intraday advisory loop; the CN practitioner evidence says the *demonstrated-useful* cadence is EOD/pre-open, with intraday value carried by formulas the LLM wrote offline. Worth treating as a field-data point for a two-speed design.
- **[NEW] Pre-committed stop/target forced *inside* the pre-mortem prompt** (P4): user must state 止损价/目标价 before requesting critique — commits the human before the LLM speaks. F5's adversarial check doesn't demand this of the human.
- **[NEW] Epistemic labeling vocabulary** (P1/P8): mandatory inline tags "这是推测" / "数据有限" / "不许口算，以脚本跑出为准". Sharper than R08/R09's generic source-of-truth instruction; cheap to add to our system prompt.
- **[NEW] Compliance-keyword refusal landscape** (P7): DeepSeek refuses on 荐股-shaped verbs. If we ever front DeepSeek-class CN models, phrase advisory tasks as filter/format/analysis operations to avoid spurious refusals — and log refusals as a first-class failure mode (not in F5's spec).
- **[NEW] Vendor-doc RAG for platform code** (S6): the miniQMT/大QMT dialect confusion shows frontier models *confuse sibling APIs in the same product family*. Analog for us: NSE/broker API dialects — ground code-gen in our own vendored docs, don't trust param memory.
- **[NEW] Persona pantheons** (S5's 7 牛散 personas): distilled-trader personas are hugely popular in CN (赵老哥/炒股养家 prompt cards circulate in QQ groups). **[CONTRADICTS]** R08's persona evidence (S12–S14: personas don't improve factual accuracy, sometimes hurt). Verdict: reject as decision input; tolerable only as hypothesis-generators feeding a forward-validation pool, which is exactly what S5 does.
- **[CONFIRMS] LLM-as-analyst-not-trader** (S4, S16 vs R09 P1/S2/S3): independent CN convergence on code-as-arbiter, human-executes, LLM never sizes or orders.
- **[CONFIRMS] CSV/field-minimization beats verbose payloads** (S2's 6-column rule vs F5's token-economics adjudication R08 S19–S21).
- **[CONFIRMS] Low temperature for code/formula tasks** (S1's temp 0.3/top_p 0.85 recipe vs R08 S17–S18 temperature-reproducibility findings); max_tokens truncation of safety clauses (S1) is a new concrete failure instance of output budgeting.
- **[CONFIRMS] Rate-limit/availability engineering** (S11/S12 vs R09 S11's field numbers): exponential backoff + jitter, off-peak scheduling, web-tier throttles harder than API — same operational reality, CN flavor adds "schedule the cron before open partly because that's when DeepSeek is idle."
- **[CONTRADICTS] None fundamental** — the serious CN practitioners contradict none of F5/R09's core adjudications; the *retail hype layer* contradicts everything (P&L claims), but our corpus already discounts that layer.
