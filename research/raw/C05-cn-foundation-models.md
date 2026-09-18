# C05: CN financial foundation models

Date: 2026-09-16. Research agent C05. Scope: Chinese-domain financial foundation models, their official prompting conventions, and what (if anything) transfers to a NIFTY options advisory bot.

## Model table — # | name | org | year | size | specialty | benchmark numbers | URL

| # | name | org | year | size | specialty | benchmark numbers | URL |
|---|---|---|---|---|---|---|---|
| 1 | FinGPT (v3.x sentiment LoRA family) | AI4Finance Foundation | 2023 | 6B–13B (ChatGLM2-6B, Llama-2-7B/13B chat lovers, QLoRA/8-bit variants) | Instruction-tuned financial sentiment (FPB/FiQA/TFNS/NWGI); cheap LoRA on 1× RTX 3090 | Weighted F1: FPB 0.882, FiQA-SA 0.874, TFNS 0.903, NWGI 0.643 (v3.3); beats GPT-4 (FPB 0.833) and comparable to OpenAI fine-tune; training cost ~$6–23 | https://github.com/AI4Finance-Foundation/FinGPT |
| 2 | Instruct-FinGPT | AI4Finance (Zhang et al.) | 2023 | 7B (Llama-1) | Academic predecessor: instruction-tuning for sentiment; 10 human-written instruction templates | Improvement over zero-shot Llama on FPB/FiQA/TFNS (paper 2306.12659) | https://arxiv.org/pdf/2306.12659 |
| 3 | Fin-R1 | SUFE-AIFLM-Lab + FinStep.AI (财跃星辰) | 2025-03 | 7B (Qwen2.5-7B-Instruct base) | Financial reasoning via SFT + GRPO RL on 60,091 CoT samples (Fin-R1-Data) | FinQA 76.0, ConvFinQA 85.0, Ant_Finance 81.0, TFNS 71.0, Finance-Instruct-500k 62.9, **avg 75.2** (vs DeepSeek-R1 78.2, R1-Distill-Llama-70B 69.2) | https://github.com/SUFE-AIFLM-Lab/Fin-R1 ; https://huggingface.co/SUFE-AIFLM-Lab/Fin-R1 ; https://arxiv.org/abs/2503.16252 |
| 4 | Fin-o1 (FinCoT + FinReason bench) | TheFinAI (Open-FinLLMs community) | 2025-02 | 8B / 14B (Qwen3 base) | Financial reasoning CoT corpus (FinCoT) + SFT/GRPO; first open FinReason benchmark | Outperforms GPT-o1 and DeepSeek-R1 on its FinReason benchmark; notes DeepSeek-scale general models degrade on long financial documents | https://arxiv.org/html/2502.08127v3 ; https://github.com/The-FinAI/Fino1 ; https://huggingface.co/TheFinAI/Fin-o1-8B |
| 5 | FinZero | (arXiv 2509.08742; anonymous multimodal group) | 2025-09 | multimodal | Financial time-series forecasting as **image reasoning** (charts rendered to images) + UARPO (uncertainty-adjusted GRPO) | ~13.48% prediction-accuracy gain over GPT-4o in high-confidence group | https://www.arxiv.org/pdf/2509.08742 |
| 6 | DianJin-R1 (通义点金) | Alibaba / Qwen DianJin | 2025-04 | 7B / 13B / 32B (Qwen2.5-Instruct bases) | Financial reasoning with structured "reasoning + answer" output; compliance checking (CCC); SFT + GRPO with dual (format + accuracy) rewards | CFLUE/FinQA/CCC + MATH-500/GPQA-Diamond; GPT-4o baseline CFLUE 71.68 / FinQA 79.16; DianJin-R1-32B beats non-reasoning counterparts consistently; single-call matches multi-agent CCC systems | https://github.com/aliyun/qwen-dianjin ; https://arxiv.org/abs/2504.15716 |
| 7 | DISC-FinLLM | Fudan DISC Lab | 2023 | 13B (Baichuan-13B-Chat base) | Multi-expert SFT: consulting, financial NLP, computation, RAG-QA; DISC-Fin-Eval benchmark | FinCUGE suite: FinFE 69.3, FinQA 42.4, FinESE 45.3 (vs Baichuan base avg 31.0 → 40.0); FinEval (human tests) ~50–55% vs GPT-4 68.6 | https://github.com/FudanDISC/DISC-FinLLM ; https://arxiv.org/pdf/2310.15205 |
| 8 | AlphaFin (StockGPT-Stage1/2 + Stock-Chain) | AlphaFin-proj (THU-affiliated) | 2024 (LREC-COLING) | LoRA on ChatGLM2-6B | Stock trend prediction + financial Q&A with handwritten CoT; RAG over a real-time "FinDatabase" | AlphaFin reports SOTA trend-prediction Acc/F1 vs GPT-3.5/4-style baselines on its own StockQA + FPB-style sets; bilingual CN/EN | https://github.com/AlphaFin-proj/AlphaFin ; https://aclanthology.org/2024.lrec-main.69/ |
| 9 | Kronos | shiyu-coder (Tsinghua-affiliated), AAAI 2026 | 2025-08 | small/mini/base (~24M–200M+) | **K-line foundation model**: decoder-only transformer over BSQ-tokenized OHLCV(+amount); 12B+ K-line records, 45 global exchanges, 7 time granularities | +93% RankIC vs best TSFM, +87% vs best non-pretrained baseline (price forecasting); −9% MAE volatility; +22% generative fidelity; 34K+ GitHub stars | https://github.com/shiyu-coder/Kronos ; https://arxiv.org/pdf/2508.02739 |
| 10 | Time-MoE | Squirrel AI / Baidu joint (Maple728) | 2024-09, ICLR 2025 | up to 2.4B (sparse MoE) | Universal time-series MoE, decoder-only, point-wise tokenization, context ≤ 4096 | SOTA-ish zero-shot forecasting on Time-300B eval; not finance-specific | https://github.com/Time-MoE/Time-MoE ; https://arxiv.org/pdf/2409.16040v4 |
| 11 | CFLUE (benchmark, not a model) | Alibaba Cloud + Soochow Univ. | 2024 (ACL Findings) | n/a | CN financial language understanding: 38K+ MCQ (knowledge) + 16K+ instances (application: classification, MT, RE, RC, generation) | Only Qwen-72B, GPT-4, GPT-4-turbo exceed 60% on knowledge answer-prediction | https://github.com/aliyun/cflue ; https://arxiv.org/html/2405.10542 |
| 12 | FinEval (SUFE benchmark) | SUFE & Yang Liu | 2023 | 4,661 MCQ | CN financial-domain MCQ across 34 subjects (finance/economy/accounting/certificates); answer-only + CoT, zero-/few-shot modes | GPT-4 avg 68.6; ChatGPT 55.0; Baichuan-13B-Chat 49.4 (via DISC-FinLLM's reproduction) | https://fineval.readthedocs.io/en/latest/ |
| 13 | Fin-Eva (Ant Group eval) | Alipay/Ant | 2023 | 33 subtasks, 5 categories | CN financial evaluation with per-subtask prompt templates (单选理财知识解读, 金融合规判断 etc.) | n/a (evaluation dataset) | https://github.com/alipay/financial_evaluation_dataset |
| 14 | StockBot variants | bklieger-groq (US original), tbdavid2019 (TW fork) | 2024– | Llama-3-70B on Groq | Not CN finance-trained: function-calling UI agent over TradingView widgets; TW fork adds 台股 support, not A-share knowledge | none (tooling demo) | https://github.com/tbdavid2019/stockbot |

Notes: "DeepSeek-Finance builds" as distinct released models were not located — the CN stack overwhelmingly uses **DeepSeek-R1/DeepSeek-V3 directly as the teacher/judge** (Fin-R1 uses it as the bar; DianJin-R1 uses R1 to distill CoT into CFLUE MCQ sets; Fin-o1 compares against R1). "FinMem/FinNews CN variants" and "FinLLM-instruct" as standalone CN releases were not located with confidence and are omitted rather than fabricated. "aipc?" not found.

## Verbatim instruction/prompt templates — per model where published (original language preserved)

### FinGPT v3 (AI4Finance) — training/eval prompt, from FinGPT_Sentiment_Analysis_v3 README
```
Instruction: What is the sentiment of this news? Please choose an answer from {negative/neutral/positive}.
Input: FINANCING OF ASPOCOMP 'S GROWTH Aspocomp is aggressively pursuing its growth strategy...
Answer:
```
Variant for tweets: `Instruction: What is the sentiment of this tweet? Please choose an answer from {negative/neutral/positive}.` Labels derived from numeric score thresholds: `< -0.1 → negative`, `[-0.1, 0.1) → neutral`, `>= 0.1 → positive`. Output is harvested by `o.split("Answer: ")[1]` — i.e. a hard parse contract on "Answer:".

### FinGPT v1 (market-labeled variant) — finer-grained 7-way scale
```
News: '''{news}'''

Instruction: Please 'ONLY' output 'one' sentiment of all the above News from {{ Severely Positive / Moderately Positive / Mildly Positive / Neutral / Mildly Negative / Moderately Negative / Severely Negative }} without other words.

Answer:
```
(Source: FinGPT_Sentiment_Analysis_v1 README. Note the published code contains a typo `prompt = template.format(mews)`.)

### Instruct-FinGPT (paper 2306.12659)
10 human-written instruction paraphrases, composed as: `Human: [instruction] + [input], Assistant: [output]`. Instruction randomly sampled per training sample — deliberate instruction-diversity augmentation.

### Fin-R1 (SUFE) — official usage convention (HF model card / README)
- Based on Qwen2.5-7B-Instruct chat template; recommended system prompt: **"Please reason step by step, and put your final answer within \boxed{}."**
- GRPO training uses dual rewards: format reward (the `\boxed{}` contract + think-before-answer) + accuracy reward, with Qwen2.5-Max as model-based verifier over regex-parseable answers.
- Training mix: ConvFinQA + FinQA SFT → GRPO RL. Scenarios: 金融代码 / 金融计算 / 英语金融计算 / 金融安全合规 / 智能风控 / ESG分析.

### DianJin-R1 (Alibaba) — structured reasoning+answer format
"structured format that generates both reasoning steps and final answers"; GRPO with dual reward signals — one encouraging structured output, one rewarding answer correctness. Training data = CFLUE + FinQA + CCC (private compliance corpus). Eval benchmarks: CFLUE, FinQA, CCC, MATH-500, GPQA-Diamond.

### CFLUE (Alibaba) — evaluation prompt templates (verbatim from repo README)
Single-choice:
```python
假设你是一位金融行业专家，请回答下列问题。
注意：题目是单选题，只需要返回一个最合适的选项，若有多个合适的答案，只返回最准确的即可。
注意：结果只输出两行，第一行只需要返回答案的英文选项(注意只需要返回一个最合适的答案)，第二行进行简要的解析，输出格式限制为：“答案：”，“解析：”。
{question}
{choices}
```
Multiple-choice:
```python
假设你是一位金融行业专家，请回答下列问题。
注意：题目是多选题，可能存在多个正确的答案。
注意：结果只输出两行，第一行只需要返回答案的英文选项，第二行进行简要的解释。输出格式限制为：“答案：”，“解析：”。
{question}
{choices}
```
Builder: `utils/format_example.py`. The "答案：/解析：" two-line contract is the key reusable convention.

### FinEval (SUFE) — evaluation templates (verbatim)
Few-shot answer-only header: `以下是中国关于{banking_practitioner_qualification_certificate}考试的单项选择题，请选出其中的正确答案。` followed by k-shot demos `...答案：D`, then target question ending `答案：`.
CoT mode: append instruction producing `答案：让我们一步一步思考，` with numbered reasoning steps then `所以答案是A。` — enforces a parseable final-answer tail after free reasoning.

### Ant Fin-Eva — per-subtask templates (verbatim from README)
理财知识解读 (single-choice):
```
你是一名专业的理财专家，你对任何理财知识都了解，你需要从A、B、C、D四个选项中选出一个作为问题最恰当的回答，你只能输出一个字符，并且这个字符是A、B、C、D中一个。
理财问题：{question}
选项：
A.{A}
B.{B}
C.{C}
D.{D}
答：
```
金融合规性 (judgement):
```
你是一名专业的金融行业金融合规审核员，你可以判断给定的输入包含的信息是否金融合规。
问题是：{question}
你的输出只能是“是”或者“否”
```

### DISC-FinLLM — four expert modules
DISC-FIN-SFT instruction data in 4 categories (咨询 / NLP任务 / 计算 / 检索问答). Few-shot prompt templates convert FinCUGE tasks (FinFE sentiment, FinQA, FinCQA, FinNA summarization, FinRE relation extraction, FinESE event extraction) into eval form; exact strings live in `eval/evaluator/`.

### Kronos — input encoding convention (not a text prompt)
`KronosPredictor.predict(df, x_timestamp, y_timestamp, pred_len)` where `df` is a pandas DataFrame of OHLCV(+amount); tokenizer quantizes continuous OHLCV into hierarchical binary-sphere-quantized (BSQ) tokens — s1_bits=10 coarse + s2_bits=10 fine (joint vocab 2^20); temporal embeddings for minute/hour/weekday/day/month; context length ~512 bars, typical pred_len ≤ 120. Trained on 45 exchanges / 12B+ K-line records / 7 granularities → **market-agnostic by design**; fine-tuning scripts released 2025-08-17.

### Time-MoE — input convention
Decoder-only, point-wise (scalar) tokenization of raw series; context+horizon ≤ 4096. Fine-tune data as jsonl: `{"sequence": [1.0, 2.0, 3.0, ...]}` — one series per line, no text prompted.

### AlphaFin — Stock-Chain prompt convention
Bilingual CN/EN instruction data; trend-prediction CoT distilled from handwritten analyst reasoning + RAG over real-time FinDatabase via BGE-Large-zh embeddings. Exact trend-prediction template is defined inside `scripts/stage1_trend_prediction.sh` / stage2 QA scripts (not quoted here verbatim).

## Transferability analysis — A-share-trained → NIFTY advisory

**Likely to transfer:**
1. **Prompt/output contracts** — the strongest reusable artifact. CFLUE's two-line `答案：/解析：` , FinEval's `让我们一步一步思考…所以答案是X` tail, FinGPT's `Instruction:/Input:/Answer:` triple, and Fin-R1/DianJin-R1's `\boxed{}` format-reward contract are all market-agnostic discipline mechanisms for parseable, auditable advisory output.
2. **Financial arithmetic/reasoning** — Fin-R1's FinQA/ConvFinQA training is English & US-10-K-based, i.e. numeracy about financial statements, not A-share microstructure. That skill transfers; its cn-benchmark headwinds (Ant_Finance, TFNS) do not matter to us.
3. **Kronos, explicitly** — pre-trained across 45 exchanges incl. crypto/global; OHLCV is language-independent. For NIFTY index bars this is zero-shot-usable and fine-tunable on NSE data. Highest-transfer artifact in this whole survey.
4. **Sentiment-label taxonomy** — FinGPT's 3-way and 7-way graded sentiment scales map 1:1 onto NSE news/social-media sentiment inputs.

**Does NOT transfer:**
1. **Regulation/compliance semantics** — CCC (DianJin), 合规判断 (Ant Fin-Eva), Cert exams (FinEval/CFLUE) encode CSRC/SAC/Chinese-banking rules. An advisory bot tuned on these would import PRC-licensing vocabulary and T+1/price-limit assumptions — actively misleading for SEBI/NSE.
2. **Market microstructure assumptions** — A-share retail-dominated order flow, 涨跌停板 limits, no-derivatives-for-retail conventions; nothing about index options, lot sizes, expiry cycles, or OI semantics of NIFTY weekly expiries.
3. **Language/tokenization** — ChatGLM2/Baichuan/Qwen2.5 CN-tokenizer crutches; NIFTY corpus is English/Hinglish.
4. **Data freshness & hallucination** — AlphaFin's own stated fix for hallucination is RAG over a CN FinDatabase; without an NSE-equivalent database the pattern, not the asset, transfers.

Net: no CN-specialized LLM earns a model seat over strong general models already beating them (DeepSeek-R1/GPT-4-class ≥ Fin-R1 abs scores). Kronos as a *numeric* forecaster is the only plausible component, and even it should sit behind our R02/R09 accuracy gates.

## What's NEW vs our F1/R02 findings
- [NEW] Kronos (arXiv 2508.02739, AAAI 2026): market-agnostic K-line tokenizer (BSQ hierarchical tokens, 10+10 bits) + claimed +93% RankIC over best TSFM; fine-tuning scripts released → candidate numeric-forecast component, pending backtest vs R10 costs.
- [NEW] FinZero (arXiv 2509.08742): RL-tuned multimodal model reasoning over **chart images** with uncertainty-adjusted GRPO; +13.5% over GPT-4o high-confidence subgroup — supports chart-image reasoning as a viable channel (ties to R04/R06 visual-feature ideas).
- [NEW] Dual-reward (format + accuracy) GRPO is the convergent CN convention (Fin-R1, DianJin-R1, Fin-o1) for structured financial output — direct design input for our advisory-output schema if we ever fine-tune.
- [NEW] CN eval suites define strict answer contracts (`答案：/解析：`, `所以答案是`) usable as parseable answer-tail conventions even in English prompts.
- [CONFIRMS] Specialized small models (7B Fin-R1) can approach but not beat frontier general models on finance (75.2 vs DeepSeek-R1 78.2) — consistent with R01/R02's "capable general LLM + tooling beats small domain-tuned LLM" thesis.
- [CONFIRMS] Sentiment via instruction-tuned LoRA beats GPT-4 zero-shot on narrow sentiment F1 (FinGPT v3.3 FPB 0.882 vs GPT-4 0.833) but only for classification-width tasks — matches R02's narrow-task exception.
- [CONFIRMS] Hallucination fix convention is RAG over a real-time financial DB (AlphaFin), not bigger weights — matches R09 hybrid architecture.
- [CONTRADICTS] None material. (Mild tension: FinGPT repo headline claims "better than GPT-4" — true only for weighted F1 on FPB subset, not general analysis; do not over-cite.)

## Sources (≥8)
1. https://github.com/AI4Finance-Foundation/FinGPT (+fingpt/FinGPT_Sentiment_Analysis_v3 README, benchmarks)
2. https://arxiv.org/pdf/2306.12659 (Instruct-FinGPT)
3. https://github.com/SUFE-AIFLM-Lab/Fin-R1 ; https://huggingface.co/SUFE-AIFLM-Lab/Fin-R1 ; https://arxiv.org/abs/2503.16252
4. https://arxiv.org/html/2502.08127v3 ; https://github.com/The-FinAI/Fino1 ; https://huggingface.co/TheFinAI/Fin-o1-8B
5. https://www.arxiv.org/pdf/2509.08742 (FinZero)
6. https://github.com/aliyun/qwen-dianjin ; https://arxiv.org/abs/2504.15716 (DianJin-R1)
7. https://github.com/FudanDISC/DISC-FinLLM ; https://arxiv.org/pdf/2310.15205
8. https://github.com/aliyun/cflue ; https://arxiv.org/html/2405.10542
9. https://fineval.readthedocs.io/en/latest/prompt/few_shot.html ; https://fineval.readthedocs.io/en/latest/prompt/cot.html
10. https://github.com/AlphaFin-proj/AlphaFin ; https://aclanthology.org/2024.lrec-main.69/
11. https://github.com/shiyu-coder/Kronos ; https://arxiv.org/pdf/2508.02739
12. https://github.com/Time-MoE/Time-MoE ; https://arxiv.org/pdf/2409.16040v4
13. https://github.com/alipay/financial_evaluation_dataset (Ant Fin-Eva)
14. https://github.com/tbdavid2019/stockbot (StockBot TW fork — ruled out as finance-trained model)
