# 02 — LLM Interface, Limitations and Prompts (STE): synthesis of F1 + F5

## Terms and abbreviations

- **engine** — the deterministic Python process. It computes all numbers and owns all risk limits.
- **Evidence tiers:** A = peer-reviewed / major conference. B = strong preprint, industry evidence, or
  multiply corroborated. C = single anecdote / practitioner blog.
- **LLM** — large language model. **CoT** — chain-of-thought (visible reasoning text in the answer).
- **NIFTY** — the NSE index this product trades. **IST** — India Standard Time.
- **OHLC / OHLCV** — open, high, low, close (plus volume) bars. **LTP** — last traded price.
- **OI** — open interest. **IV** — implied volatility. **IV rank** — IV percentile over its history.
  **PCR** — put-call ratio. **Max pain** — the strike where option writers lose least.
- **VWAP** — volume-weighted average price. **ATR** — average true range. **CVaR** — conditional
  value at risk (a risk limit). **SL** — stop loss. **R:R** — reward-to-risk ratio.
- **MAE / MFE** — maximum adverse / favorable excursion of a trade.
- **Sharpe** — return per unit of volatility. **bps** — basis points (1 bp = 0.01%). **pp** — percentage points.
- **JSON / CSV** — payload formats. **P95 / P99** — 95th / 99th percentile of latency.
- **Snapshot** — the single JSON/CSV input envelope the engine sends to the LLM.
- **Source tags (F1, F5, R##, S##, P#)** stay for audit only.

**Status:** decision-grade spec. An engineer can implement the LLM layer of the NIFTY options
intraday-scalping advisory bot from this document alone.
**Inputs:** `research/filtered/F1-llm-capabilities.md`, `research/filtered/F5-prompts-and-architecture.md`.

---

## 1. What the evidence says LLMs can and cannot do

### 1.1 Cannot / must not do

| Finding | Effect size | Tier | Source |
|---|---|---|---|
| **Arithmetic on financial tables fails at frontier scale** | 4–8% residual numeric error incl. reasoning-class models (Claude-Sonnet-4 95.6%); error grows to ~51% with computation depth and +47pp under numeric perturbation; small open models fail 50–70% of masked table values | A (FAITH, ICAIF'25); B (V-FiLLM, FININDICES) | F1 kept #1; R02 S6,S12,S18 |
| **In-training-window backtests are meaningless** (parametric look-ahead) | correcting memorized outcomes cuts in-sample returns **up to −67.1%**; recall probes collapse to ~0 right after the training cutoff; replicated by ≥4 independent groups (Glasserman–Lin, FinCAD, Look-Ahead-Bench, FINSABER) | B, replicated ≥4× | F1 kept #5; R02 S2–S5 |
| **Published LLM-agent alpha is not deployment evidence** | The FINSABER 2-decade/100+ symbol/cost-inclusive re-test reversed FinMem (MSFT Sharpe 1.44 → −1.247); 35/40 system×friction cells unmodeled; net-of-friction reproductions fall below Buy&Hold | A (FINSABER, KDD) | F1 kept #6; R01 S6,S7,S17 |
| **Timing / regime skill is absent or negative** | FinAgent Sharpe 0.12 bull / −0.38 bear; FinMem −0.19/−0.97; a trivial ATR-band beats both in every regime; production fleets are sized volatility-blind (median 5× leverage in all vol sextiles) | A/B | F1 kept #7; R01 S6,S14 |
| **Momentum over-extrapolation from raw price series** — wrong for intraday reversal, resistant to prompt engineering | Feeding raw OHLC and asking for direction is exactly wrong for scalping | B (Gulen et al.) | F1 kept #8; R02 S7 |
| **Multi-agent debate does not pay** | majority voting captures most gains (7 benchmarks); homogeneous debate costs 2.1–3.4× tokens for equal or lower accuracy; sycophancy ≤85.5%, correct→incorrect flips ≤70%; deliberative consensus degraded accuracy 83.4%→76% | A (NeurIPS'25); B | F1 kept #10; F5 adjudication 3; R01 S18,S19; R08 S16 |
| **Raw option chains exceed LLM reliability** | text-to-code over full chains hallucinates invalid tickers/constraints | B (OQL) | F1 kept #11; R01 S21 |
| **Sub-15-minute prediction is unevaluated-to-negative** | the best "fast" framework (QuantAgent) works at 1–4h bars and admits failure on 1–15min; measured LLM decision latency 1.5–3s (≈30× the scalping budget), P99 tails 10–17s | B | F1 kept #12; F5; R01 S16,S22; R09 S8,S10 |
| **Reasoning-model upgrades (o1/R1-class) do NOT fix finance numerics** | FinReason (29 LLMs): o1/R1/GPT-4.5 degrade in financial contexts; an 8B domain-tuned model beat them | B | F1 adjudication 5; R02 S14 |
| **Live profitability unproven-negative** | population-scale record (7.5M invocations, 3,505 vaults): fleet unprofitable, 41% win vs 50% benchmark; single-contest wins demoted to anecdote | B (large-n live record) | F1 adjudication 6; R01 S13 vs S14 |
| **Exits are where agents bleed** | 43.2% of positions reached ≥+300bps favorable excursion, yet ~half of those closed negative; a mechanical ATR bracket recovered +39bps/position | B (large-n live) | F1 kept #13; R01 S14 |

### 1.2 Can do (the positive envelope)

| Finding | Detail | Tier | Source |
|---|---|---|---|
| **Classification on pre-digested inputs works.** | Structured snapshot inputs + analyst-workflow scaffold lifted GPT-4 from 52%→60% directional accuracy (above human analysts at 53–57%); post-cutoff headline classification predicts short-horizon direction (tradable edge thin, ≈34bps/day pre-cost — relevant as evidence that *classification* works, not that it clears our costs) | A (Lopez-Lira & Tang, JFE-forthcoming; FinCon NeurIPS'24); B (Booth working paper) | F1 kept #4,#9; R02 S1,S8,S15 |
| **Risk elicitation is better calibrated than point forecasts.** | 80% intervals are better calibrated than humans'. Elicit invalidation and uncertainty, not predictions | B | F1 kept #9; R02 S7 |
| **Code-computes / LLM-narrates is the validated hybrid.** | FinRobot production pattern (pure-Python operators, numeric provenance) + FinCon external CVaR math | A (FinCon); B (FinRobot industry) | F1 kept #4; R02 S15,S17 |

### 1.3 Adjudicated points (resolved in filtering, restated as law)

- **Debate:** no in-session multi-agent debate. Trust F1's preference for large-n controlled studies over within-paper ablations. (F1 adjudication 2; F5 adjudication 3)
- **Risk math lives outside the LLM loop.** Keep CVaR-style limits in Python. The LLM may only flag. (F1 adjudication 3; R02 S17 is the precise description)
- **The LLM is an interpreter, classifier, and risk-checker. It is never a forecaster.** All positive results are classification on pre-digested inputs. All forecasting and timing claims fail or do not replicate. (F1 adjudication 4)
- **Contamination is the highest-confidence finding in the corpus.** Treat any in-window backtest number as inflated by up to ~2/3. (F1 adjudication 7)

---

## 2. Authority partition

This is the strongest corroborated rule in the corpus; every source agrees with it:
**the LLM never emits an executable order, and never emits a number the engine did not compute.
The engine is the sole arbiter of numbers and risk limits.**

| Decision / computation | Owner | Evidence |
|---|---|---|
| Greeks, OI change %, PCR, max pain, IV rank, ATR, VWAP deviation, candle stats, position P&L — every number in the snapshot | **Engine** (pre-computes; the snapshot contains no arithmetic to perform) | F1 directive 1; F5 adjudication 4 |
| Chain pre-filtering (ATM±4 strikes, liquid expiries, OI threshold) | **Engine** (deterministic) | F1 directive 2; R01 S21 |
| Regime detection, exposure caps, daily-loss limit, kill switch | **Engine** (deterministic, external to the LLM) | F1 directive 4; R01 S6,S14; R02 S17 |
| Bracket SL/target from ATR, attached to every advisory | **Engine** (computed deterministically at advice time) | F1 kept #13 + directive 4; R01 S14 |
| Position sizing, lots, max-loss | **Engine** — `f(stop_loss, risk budget)` in code; the LLM has **no size field** | F5 §B.4; R08 S3/S4/S9; R09 P1 |
| Direction call on a live setup (LONG_CALL / LONG_PUT / NO_TRADE) | **LLM** (classification on a pre-digested snapshot — its one validated strength) | F1 kept #4,#9; directive 6 |
| Setup conviction grade (A/B/C) | **LLM** proposes; the **engine** maps it to a size-multiplier **cap** | F5 §B.4 |
| Entry band / absolute levels / invalidation sentence | **LLM** proposes from snapshot values; the **engine** validates against snapshot + spread | F5 §B, §C |
| Numeric provenance check (every quoted number ∈ snapshot) | **Engine** (string-match; mismatches = logged hallucination events) | F1 directive 3; F5 §C.3 |
| Stale-data / time-of-day / expiry / loss-limit / kill-switch overrides → NO_TRADE | **Engine** (pre-empts the LLM regardless of output) | F5 §C.4 |
| Borderline-confidence demotion ([0.45, 0.55] → NO_TRADE) | **Engine** (code rule) | F5 §C.5; R08 S17/S18 |
| Risk-parameter widening (more size than cap, later square-off) | **Human** (hard confirmation checkpoint; the LLM can never approve) | F5 §C.8; R09 S18 |
| Accept/decline/execute each advisory; daily playbook approval; weekly review | **Human** (advisor, never auto-execution) | F1 directive 7; F5 triggers table |
| Cadence gating (the setup pre-filter decides whether the 30s poll fires) | **Engine** (deterministic pre-filter) | F5 adjudication 5; Invocation § |

---

## 3. The advisory interface contract

### 3.1 Engine → LLM: input envelope

Use a **layered JSON/CSV hybrid** (F5 adjudication 2). The outer envelope is JSON. Carry dense numeric
arrays as embedded CSV strings (−60% tokens vs pretty JSON at equal accuracy, R08 S19–S21). Carry
indicators as one flat `k=v` line. Keep only small hierarchical context (meta, account, regime flags)
as JSON.

**Size budget: ≤3,000 input tokens** (measured 1.5–3k for this shape; ≈$0.005–0.015/cycle at
Haiku-tier, uncached; far less with a cached system prompt). Snapshot minimalism is accuracy
engineering, not aesthetics: extraneous context numbers degrade output by ≥10% (worst −51.55%)
[F1 kept #3, tier B].

**Canonical formatting rule** (F1 kept #2, tier B): use one rounding/format everywhere. Uniform
decimal precision. No mixed units. Tokenization and decimal grouping change model behavior.

Reference payload:

```json
{
  "meta": {
    "ts_ist": "2026-09-16T10:14:30+05:30",
    "snapshot_age_ms": 420,
    "engine_version": "0.3.1",
    "trigger": "periodic | event:iv_spike"
  },
  "regime_flags": {
    "session_phase": "open|mid|close",
    "trend_state": "up|down|flat",
    "vol_state": "low|normal|expanding|spiking",
    "minutes_to_expiry": 1435,
    "data_ok": true
  },
  "spot_1m_csv": "ts,o,h,l,c,v\n10:05,24788.1,24794.2,24781.5,24790.4,152310\n…(last 15 rows max)",
  "chain_csv": "strike,ce_ltp,pe_ltp,ce_oi,pe_oi,ce_doi,pe_doi,ce_iv,pe_iv,ce_delta,pe_delta\n24750,…\n…(ATM ± 4 strikes, 9 rows max)",
  "indicators_csv": "vwap=24801.4,atr14=38.2,rsi5=61.3,pcr=0.94,iv_rank=27,parity_dev_bps=3,rv_5m=…,rv_15m=…",
  "events_csv": "ts,type,detail\n10:11,spot_sigma_move,+2.1σ in 4m\n…(last 8, rolling)",
  "account": {
    "open_positions": 0,
    "daily_pnl_inr": -350,
    "trades_today": 3,
    "kill_switch": false
  }
}
```

Rules:

1. Send the last 15 one-minute bars only.
2. Window the chain to ATM±4 (9 rows).
3. All numbers are engine-computed. The LLM may quote a number. It may never derive one.
4. **Do not ask for direction from raw OHLC** (the momentum-over-extrapolation finding). The raw spot
   bars are context for pattern classification. Pre-computed indicators carry the quantitative content.
5. Optional snapshot hygiene: date anonymization in text fields (low-cost, parked C-tier idea from the
   F1 demoted list).

### 3.2 LLM → output: strict JSON schema

**Mode: single-pass strict JSON-schema structured output, answer-first, no visible CoT.** Keep the
two-pass freeform→reformat path as a config flag *only* if the model is ever swapped to open
weights (F5 adjudication 1).

```json
{
  "action": "LONG_CALL | LONG_PUT | NO_TRADE",
  "confidence": 0.0,
  "setup_quality": "A | B | C",
  "strike": 24800,
  "entry_level": 0.0,
  "stop_loss": 0.0,
  "target_1": 0.0,
  "invalidation": "one sentence, in absolute price terms only",
  "time_stop_minutes": 0,
  "data_conflict": false,
  "rationale": "≤25 words"
}
```

Field semantics. State them in the prompt for consistency. **Enforce them in code.**

| Field | Type | Rule |
|---|---|---|
| `action` | enum | `LONG_CALL \| LONG_PUT \| NO_TRADE`. NO_TRADE is mandatory on mixed signals, stale or missing data, or sub-minimum R:R. The escape hatch is a first-class answer. |
| `confidence` | float ∈ [0,1] | Advisory label only. Show it as a label, **never as a probability**, until calibration data exists (F1 directive 4). Code demotes [0.45,0.55] → NO_TRADE. |
| `setup_quality` | enum `A\|B\|C` | Conviction grade; the engine maps it to a size-multiplier **cap**. |
| `strike` | int | Absolute index points; must be inside the `chain_csv` window. |
| `entry_level`/`stop_loss`/`target_1` | float | Absolute INR **premium** levels. Never %, never ranges. The stop sits on the correct side of entry. The target sits beyond entry. The entry sits within the quoted spread ± slippage buffer. If a field is omitted, the engine treats that leg as NO_TRADE. |
| `invalidation` | string | One sentence, absolute price terms only — the calibrated-uncertainty elicitation (F1 kept #9). |
| `time_stop_minutes` | int | Advisory time-stop; the engine still owns the deterministic bracket. |
| `data_conflict` | bool | `true` if snapshot fields conflict. **Never reconcile silently.** Silent-failure fabrication is the documented catastrophic failure mode. |
| `rationale` | string ≤25 words | A bounded audit trail. No CoT overthinking. |

**There is no size field, no max-loss field, no executable order.** Final lots =
`f(stop_loss, risk budget)` computed in code.

### 3.3 Validation layer (all in code, before a human ever sees advice)

1. **Schema gate.** Rigid JSON-schema parse. On violation: **one automatic re-ask**. A second failure
   gives a deterministic NO_TRADE fallback (FinMem/Guardrails pattern, tier A-corroborated).
2. **Level sanity.** Entry must sit within the quoted spread of snapshot LTP ± slippage buffer. Stop on
   the correct side. Target beyond entry. Reject %- or range-shaped strings. Strike must be inside the
   chain window.
3. **Echo check / numeric provenance.** String-match every number in `rationale`/`invalidation` against
   snapshot values. Log mismatches as **hallucination events** (F1 directive 3; F5 §C.3).
4. **The engine pre-empts the LLM. Force NO_TRADE regardless of output if:** `snapshot_age > 2s` at
   decision time; now > 15:15 IST; `minutes_to_expiry < SCALP_HORIZON`; the daily-loss limit is hit;
   `kill_switch=true`; `data_ok=false`.
5. **Borderline = non-signal.** If `confidence ∈ [0.45, 0.55]`, code demotes to NO_TRADE. (Borderline
   decisions flip ~50% of runs even at low temperature. Tier B, but decision-changing.)
6. **Pin temperature to 0 explicitly on every call.** Never accept the provider default (1.0). T=0 is
   not full determinism: 1–2 of 7 borderline items still flip. Rule 5 exists for this reason.
7. **Latency.** P95 budget ≈8–10s for the single advisory call. **Hard timeout 12s**, then a
   deterministic fallback. Never serve stale advice. (Documented P99 tails: 10–17s. Congestion is
   worst at market open.)
8. **Risk-widening veto.** Any advisory that implies looser risk (more size than cap, later square-off)
   goes to a hard human confirmation checkpoint.

---

## 4. Invocation policy

**Cadence:** one periodic advisory every **30 s**. Call only when the engine's deterministic setup
pre-filter shows a live candidate. If no candidate exists, skip the cycle and make no LLM call.
(Pure event-driven has no production field numbers. The 30s loop is the only documented production
cadence. The gate captures the anti-empty-poll economics.) The LLM is **never in the tick path**.

**Generation settings (pin on every call):** `temperature = 0` (explicit, never the provider default);
`max_tokens` small (output ≤ ~120 tokens); system prompt cached; log every call raw + parsed + latency.

**Event triggers.** These interrupt the 30s loop. All are subject to dedup + **≥60–120s cooldown** +
idempotency. Expect 5–20/day.

| Event | Why | Tier |
|---|---|---|
| \|spot move\| > kσ in m min (default 2σ/5min) | Fast tape invalidates cached advice; documented trigger archetype. Thresholds unvalidated for NIFTY — tunable | B — R09 S12,S13 |
| IV spike / IV-crush | Options-specific: premium and greeks shift faster than the spot cadence catches | B — pattern application; our own threshold |
| OI cliff / ΔOI anomaly at focus strikes | Positioning-regime break; adversarial-flow signal; the engine computes, the LLM interprets | B |
| Open-position P&L breach (unrealized loss > x% of stop budget) | Escalate with fresh advice while the deterministic stop still owns the exit | B |
| `data_conflict` / snapshot staleness / feed gap | Fabrication guard: force NO_TRADE + alert | A-corroborated practitioner, decision-changing |
| Risk-parameter widening request | Mandatory human confirmation | A-practice (frontier-firm supervision norm) |
| Session start / EOD (*offline, not hot path*) | The human approves the daily playbook; a weekly offline critic reviews logged decisions vs outcomes | A — R09 S7 (+31% measured from the reflect loop, applied out-of-band) |

**Timeout/fallback:** on a 12s hard timeout or a second schema failure, send a deterministic NO_TRADE
fallback message to the human. Never serve stale advice.

**T=0 pinning note:** temperature 0 reduces nondeterminism. It does not eliminate it. The [0.45,0.55]
demotion rule neutralizes borderline-flip risk; re-sampling does not. Self-consistency N-way voting is
forbidden in the hot path (latency/cost, plus inter-model error correlation r≈0.53–0.69 caps the
gains). It may exist only as an offline logging experiment at T>0.

---

## 5. The production prompt

Assemble the prompt **only** from kept, evidence-backed elements. Each block carries its evidence source.

```
SYSTEM
You convert machine-generated NIFTY options snapshots into one trade
recommendation for a human scalper. You never compute numbers; every
number you output must appear in the snapshot. Domain context — NIFTY
index options, intraday scalping, INR premiums, IST timestamps —
is given by the field names; answer for this domain only.
                                            [primed domain via field names, NO persona
                                             — R08 S12–S14 (personas: no gain, can cost ~30pts;
                                             priming +2.5%)]

HARD RULES (also enforced in code):
1. action ∈ {LONG_CALL, LONG_PUT, NO_TRADE}. When signals are mixed,
   data is stale/missing, or reward-to-risk looks marginal, answer
   NO_TRADE. Do not manufacture a direction to appear decisive.
                                            [R08 P3 escape hatch + P6 anti-decisiveness;
                                             F1 directive 6 — classification, not forecasting]
2. entry_level, stop_loss, target_1, strike are absolute INR levels.
   Never percentages, never ranges. Omit a level you cannot justify.
                                            [R08 P2 anti-parse-failure rule]
3. Quote snapshot values verbatim. If snapshot fields conflict, set
   data_conflict=true instead of reconciling silently.
                                            [R08 P1 verified-numbers grounding; F1 kept #1 —
                                             the 4–8% numeric-error finding]
4. Do not output any size or max-loss figure. Grade the setup as
   setup_quality A/B/C; sizing is computed by the caller.
                                            [R08 S3/S4/S9 + R09 P1 code-as-arbiter;
                                             F1 adjudication 3 — risk math external]
5. rationale ≤ 25 words; invalidation = one sentence in price terms.
                                            [R08 S6 bounded answer-first (Lopez-Lira pattern);
                                             S10/S11 anti-overthinking on finance/pattern tasks]
6. No reasoning chain in the response. Output the JSON object only.
                                            [R08 S8/S10/S11 CoT-hurts-on-finance;
                                             single-pass structured mode, F5 adjudication 1]

USER (per call)
<trigger: periodic|event:TYPE>               [R09 P4/S13 event context]
Snapshot (JSON envelope with CSV blocks — dense numerics as CSV):
<meta / regime_flags / spot_1m_csv / chain_csv / indicators_csv /
 events_csv / account — exactly per §3.1>
                                            [R08 S19–S21 token economics + R09 S9 compaction]

Respond with ONLY the JSON object of the output contract.
```

**Note on the CoT scaffold:** F1 directive 5 endorses an analyst-workflow scaffold (regime → OI/vol
evidence → bull → bear → invalidation, plus "what kills this trade?"). This prompt honors it
*structurally*: the snapshot's regime flags and indicators pre-stage the analytic steps; the
`invalidation` field carries the adversarial check; evidence ordering does the rest. The prompt does
**not** allow visible long-form CoT in the response. The finance/pattern-task evidence (CoT neutral
to −36pts) and the 12s latency budget both forbid it. The task is classification and interpretation —
continuation vs exhaustion, levels under threat, invalidation. It is never "predict the next candle"
(F1 directive 6).

### Deliberately excluded, and why

| Excluded element | Why (evidence) |
|---|---|
| **Expert personas** ("you are a world-class scalper") | No significant accuracy gain (tier A/B); irrelevant persona details can cost ~30pts. Domain priming via field names is retained instead (+2.5%) |
| **Multi-agent / in-session debate** | Voting captures most gains at a fraction of the cost; debate costs 2.1–3.4× tokens with sycophancy (≤85.5%) and correct→incorrect flips (≤70%); deliberative consensus degraded accuracy 83.4%→76%; 11-call/decision topologies blow the 12s budget |
| **Long / visible CoT in the hot path** | Gains concentrate in math/symbolic tasks; CoT is neutral-to-harmful (up to −36pts) on fast finance/pattern tasks; all arithmetic lives in the engine |
| **Raw OHLC / full chain dumps** | Momentum over-extrapolation (wrong for intraday reversal) + chain hallucination + ≥10% accuracy loss from extraneous numbers |
| **Freeform-then-reformat (2-pass)** | The format tax concentrates in open-weight models; it doubles the latency tail. Kept only as a config flag for open-weight swaps |
| **XML output protocol, multi-agent stop tokens, P&L-conditioned persona switching, hot-path N-way voting** | Era-specific workarounds / intraday-untested / latency-forbidden; see the F5 demoted list |
| **LLM anywhere in the tick/execution path** | 1.5–3s decisions + 10–17s tails vs sub-second scalping requirements |

---

## 6. Evaluation protocol — forward-only shadow log

### 6.1 Log from day one (per invocation)

- The exact snapshot JSON (the input byte-for-byte), model version, **prompt hash**, timestamp, trigger type.
- The raw response + parsed output + per-call latency; the schema-validated final output; the re-ask flag if used.
- The engine-computed bracket (ATR SL/target) attached to the advisory.
- The **hallucination-event flag** (quoted number ∉ snapshot) and the `data_conflict` history.
- A human executes. Log both *advice-as-given* and *execution-as-taken* (accept/decline, fill levels, slippage).

### 6.2 Forward-only, cost-honest scoring

- **Never score on data inside the model's training window.** Treat any such number as inflated by up
  to ~2/3 and label it non-evidence. Grade only realized forward outcomes at fixed horizons
  (5/15/30 min) from engine-recorded prices.
- **Score each component separately:**
  1. **Direction hit rate** vs coin-flip **and** vs a trivial deterministic baseline (e.g., a
     VWAP-side momentum rule). *An LLM layer that cannot beat the trivial baseline is ceremony.*
  2. **Invalidation quality** — how often the stated invalidation/stop preceded the adverse move.
  3. **Bracket capture** — realized MFE/MAE vs the engine's ATR bracket.
  4. **Calibration** — bucket stated confidence vs realized hit rate *before* ever trusting the label.
- **Net of cost, always.** Deduct brokerage, STT, exchange charges, stamp duty, and slippage from every
  hypothetical advisory P&L. Report gross Sharpe only as an upper bound, with a FINSABER-style disclaimer.
- **Human-in-the-loop is the primary endpoint:** advice-acceptance rate, win-rate delta
  accepted-vs-declined, expectancy delta vs the human's unaided trades. The product claim is
  "improves a human scalper".
- **Regime-stratified reporting:** break all metrics out by engine-tagged regime (trend/range,
  high/low India-VIX). This catches the documented conservative-in-bull / aggressive-in-bear
  pathology early.

### 6.3 Release gates and allowed claim language

- **Quarterly masked-value audit** (a FAITH-style probe on *our* schema). Mask or corrupt numeric
  fields, then measure how often the model quotes a number that is not in the snapshot. This
  hallucination rate is a **release-gate metric**. Re-run provenance checks on every model swap,
  including "upgrades" (FinReason: reasoning-class upgrades degrade in finance).
- **Allowed claim language:** in-window backtesting cannot be decontaminated. The system may claim
  only (a) forward shadow-log results, net of cost, with regime stratification and n; (b)
  baseline-relative deltas (vs coin-flip, vs a trivial rule, vs human-unaided); (c)
  hallucination-event and calibration statistics. It may **never** claim backtested alpha, Sharpe, or
  win rates derived from pre-cutoff data. It may never extrapolate paper returns into live readiness.

---

## 7. Open questions (merged, ranked)

1. **Does the advisory beat the trivial VWAP-side baseline and the unaided human?** (F1 eval 3+6) —
   the single question that decides whether the LLM layer exists at all. Only the forward shadow log
   can answer it.
2. **Do the pre-filter + [0.45,0.55] demotion rules cut both noise and real edge?** This needs
   per-bucket forward stats. Tune the demotion band width after calibration data exists.
3. **Event-trigger thresholds (2σ/5min, IV-spike, OI-cliff) for NIFTY** — adopted from generic
   archetypes, unvalidated for index options. Tune against the logged false-fire rate and
   missed-event rate.
4. **Would a cheap open-weight model suffice?** If adopted: re-validate the output-format tax (enable
   the two-pass flag), re-run the masked-value audit, and compare against the same harness. Never
   assume parity with the frontier model.
5. **Offline critic loop cadence/value** (weekly log review, +31% measured in-source but out-of-band)
   — pilot it before productizing; keep it strictly off the hot path.
6. **Snapshot hygiene marginal gains** (date anonymization, indicator ordering) — run these low-cost
   experiments only after the shadow-log baseline exists.
7. **Longer-horizon reflection** (5-min cadence regime summary vs the 30s tactical loop) — does a
   slower second cadence add anything, or is it ceremony?
