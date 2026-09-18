# 02 — LLM Interface, Limitations & Prompts (Synthesis of F1 + F5)

**Status:** decision-grade spec. An engineer should be able to implement the LLM layer of the NIFTY options intraday-scalping advisory bot from this document alone.
**Inputs:** `research/filtered/F1-llm-capabilities.md`, `research/filtered/F5-prompts-and-architecture.md`.
**Tier key:** A = peer-reviewed / major conference · B = strong preprint, industry evidence, or multiply corroborated · C = single anecdote / practitioner blog.

---

## 1. What the evidence says LLMs can and can't do

### 1.1 Cannot / must not do

| Finding | Effect size | Tier | Source |
|---|---|---|---|
| **Arithmetic on financial tables fails at frontier scale** | 4–8% residual numeric error incl. reasoning-class models (Claude-Sonnet-4 95.6%); error grows to ~51% with computation depth and +47pp under numeric perturbation; small open models fail 50–70% of masked table values | A (FAITH, ICAIF'25); B (V-FiLLM, FININDICES) | F1 kept #1; R02 S6,S12,S18 |
| **In-training-window backtests are meaningless** (parametric look-ahead) | correcting memorized outcomes cuts in-sample returns **up to −67.1%**; recall probes collapse to ~0 right after the training cutoff; replicated by ≥4 independent groups (Glasserman–Lin, FinCAD, Look-Ahead-Bench, FINSABER) | B, replicated ≥4× | F1 kept #5; R02 S2–S5 |
| **Published LLM-agent alpha is not deployment evidence** | FINSABER 2-decade/100+ symbol/cost-inclusive re-test reversed FinMem (MSFT Sharpe 1.44 → −1.247); 35/40 system×friction cells unmodeled; net-of-friction reproductions fall below Buy&Hold | A (FINSABER, KDD) | F1 kept #6; R01 S6,S7,S17 |
| **Timing / regime skill is absent or negative** | FinAgent Sharpe 0.12 bull / −0.38 bear; FinMem −0.19/−0.97; trivial ATR-band beats both in every regime; production fleets sized volatility-blind (median 5× leverage in all vol sextiles) | A/B | F1 kept #7; R01 S6,S14 |
| **Momentum over-extrapolation from raw price series** — wrong for intraday reversal, resistant to prompt engineering | feeding raw OHLC and asking direction is exactly wrong for scalping | B (Gulen et al.) | F1 kept #8; R02 S7 |
| **Multi-agent debate doesn't pay** | majority voting captures most gains (7 benchmarks); homogeneous debate costs 2.1–3.4× tokens for equal/lower accuracy; sycophancy ≤85.5%, correct→incorrect flips ≤70%; deliberative consensus degraded accuracy 83.4%→76% | A (NeurIPS'25); B | F1 kept #10; F5 adjudication 3; R01 S18,S19; R08 S16 |
| **Raw option chains exceed LLM reliability** | text-to-code over full chains hallucinates invalid tickers/constraints | B (OQL) | F1 kept #11; R01 S21 |
| **Sub-15-minute prediction is unevaluated-to-negative** | best "fast" framework (QuantAgent) works at 1–4h bars, admits failure on 1–15min; measured LLM decision latency 1.5–3s (≈30× scalping budget), P99 tails 10–17s | B | F1 kept #12; F5; R01 S16,S22; R09 S8,S10 |
| **Reasoning-model upgrades (o1/R1-class) do NOT fix finance numerics** | FinReason (29 LLMs): o1/R1/GPT-4.5 degrade in financial contexts; 8B domain-tuned model beat them | B | F1 adjudication 5; R02 S14 |
| **Live profitability unproven-negative** | population-scale record (7.5M invocations, 3,505 vaults): fleet unprofitable, 41% win vs 50% benchmark; single-contest wins demoted to anecdote | B (large-n live record) | F1 adjudication 6; R01 S13 vs S14 |
| **Exits are where agents bleed** | 43.2% of positions reached ≥+300bps favorable excursion yet ~half of those closed negative; a mechanical ATR bracket recovered +39bps/position | B (large-n live) | F1 kept #13; R01 S14 |

### 1.2 Can do (the positive envelope)

| Finding | Detail | Tier | Source |
|---|---|---|---|
| **Classification/interpretation on pre-digested inputs works.** | Structured snapshot inputs + analyst-workflow scaffold lifted GPT-4 52%→60% directional accuracy (above human analysts' 53–57%); post-cutoff headline classification predicts short-horizon direction (tradable edge thin, ≈34bps/day pre-cost — relevant as evidence that *classification* works, not that it clears our costs) | A (Lopez-Lira & Tang, JFE-forthcoming; FinCon NeurIPS'24); B (Booth working paper) | F1 kept #4,#9; R02 S1,S8,S15 |
| **Risk/uncertainty elicitation is better calibrated than point forecasts.** | 80% intervals better calibrated than humans'; so elicit invalidation/uncertainty, not predictions | B | F1 kept #9; R02 S7 |
| **Code-computes / LLM-narrates is the validated hybrid.** | FinRobot production pattern (pure-Python operators, numeric provenance) + FinCon external CVaR math | A (FinCon); B (FinRobot industry) | F1 kept #4; R02 S15,S17 |

### 1.3 Adjudicated contest points (resolved in filtering, restated as law)

- **Debate:** no in-session multi-agent debate. Trust F1's precedence of large-n controlled studies over within-paper ablations. (F1 adjudication 2; F5 adjudication 3)
- **Risk math lives outside the LLM loop.** CVaR-style limits in Python; the LLM may only flag. (F1 adjudication 3; R02 S17 is the precise description)
- **LLM = interpreter/classifier/risk-checker, never forecaster.** All positive results are classification on pre-digested inputs; all forecasting/timing claims fail or don't replicate. (F1 adjudication 4)
- **Contamination is the highest-confidence finding in the corpus** — treat any in-window backtest number as inflated up to ~2/3. (F1 adjudication 7)

---

## 2. Authority partition

The strongest corroborated rule in the corpus (agreed by every source): **the LLM never emits an executable order or a number the engine didn't compute; the engine is the sole arbiter of numbers and risk limits.**

| Decision / computation | Owner | Evidence |
|---|---|---|
| Greeks, OI change %, PCR, max pain, IV rank, ATR, VWAP deviation, candle stats, position P&L — every number in the snapshot | **Engine** (pre-computes; snapshot contains no arithmetic to perform) | F1 directive 1; F5 adjudication 4 |
| Chain pre-filtering (ATM±4 strikes, liquid expiries, OI threshold) | **Engine** (deterministic) | F1 directive 2; R01 S21 |
| Regime detection, exposure caps, daily-loss limit, kill switch | **Engine** (deterministic, external to LLM) | F1 directive 4; R01 S6,S14; R02 S17 |
| Bracket SL/target from ATR, attached to every advisory | **Engine** (computed deterministically at advice time) | F1 kept #13 + directive 4; R01 S14 |
| Position sizing, lots, max-loss | **Engine** — `f(stop_loss, risk budget)` in code; LLM has **no size field** | F5 §B.4; R08 S3/S4/S9; R09 P1 |
| Direction call on a live setup (LONG_CALL / LONG_PUT / NO_TRADE) | **LLM** (classification on pre-digested snapshot — its one validated strength) | F1 kept #4,#9; directive 6 |
| Setup conviction grade (A/B/C) | **LLM** proposes; **engine** maps to a size-multiplier **cap** | F5 §B.4 |
| Entry band / absolute levels / invalidation sentence | **LLM** proposes from snapshot values; **engine** validates against snapshot + spread | F5 §B, §C |
| Numeric provenance check (every quoted number ∈ snapshot) | **Engine** (string-match; mismatches = logged hallucination events) | F1 directive 3; F5 §C.3 |
| Stale-data / time-of-day / expiry / loss-limit / kill-switch overrides → NO_TRADE | **Engine** (pre-empts LLM regardless of output) | F5 §C.4 |
| Borderline-confidence demotion ([0.45, 0.55] → NO_TRADE) | **Engine** (code rule) | F5 §C.5; R08 S17/S18 |
| Risk-parameter widening (more size than cap, later square-off) | **Human** (hard confirmation checkpoint; LLM can never approve) | F5 §C.8; R09 S18 |
| Accept/decline/execute each advisory; daily playbook approval; weekly review | **Human** (advisor, never auto-execution) | F1 directive 7; F5 triggers table |
| Cadence gating (setup pre-filter decides whether the 30s poll fires) | **Engine** (deterministic pre-filter) | F5 adjudication 5; Invocation § |

---

## 3. The advisory interface contract

### 3.1 Engine → LLM: input envelope

**Layered JSON/CSV hybrid** (F5 adjudication 2): JSON outer envelope; dense numeric arrays as embedded CSV strings (−60% tokens vs pretty JSON at equal accuracy, R08 S19–S21); indicators as a flat `k=v` line; only small hierarchical context (meta, account, regime flags) as JSON.

**Size budget: ≤3,000 input tokens** (measured 1.5–3k for this shape; ≈$0.005–0.015/cycle Haiku-tier uncached, far less with cached system prompt). Snapshot minimalism is accuracy engineering, not aesthetics: extraneous context numbers degrade output ≥10% (worst −51.55%) [F1 kept #3, tier B].

**Canonical formatting rule** (F1 kept #2, tier B): one rounding/format everywhere — uniform decimal precision, no mixed units; tokenization/decimal-grouping changes model behavior.

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

Rules: last 15 one-minute bars only; chain windowed to ATM±4 (9 rows); all numbers engine-computed — the LLM may quote but never derive. **No raw OHLC direction-asking** (anti-momentum-extrapolation finding); the raw spot bars are context for pattern classification, with pre-computed indicators carrying the quantitative content. Optional snapshot hygiene: date anonymization in text fields (low-cost, parked C-tier idea from F1 demoted list).

### 3.2 LLM → output: strict JSON schema

**Mode: single-pass strict JSON-schema structured output, answer-first, no visible CoT.** (Two-pass freeform→reformat retained as a config flag *only* if the model is ever swapped to open-weights — F5 adjudication 1.)

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

Field semantics (stated in prompt for consistency, **enforced in code**):

| Field | Type | Rule |
|---|---|---|
| `action` | enum | `LONG_CALL \| LONG_PUT \| NO_TRADE`. NO_TRADE is mandatory on mixed signals, stale/missing data, or sub-minimum R:R. Escape hatch is a first-class answer. |
| `confidence` | float ∈ [0,1] | Advisory label only — displayed as a label, **never as a probability**, pending empirical calibration (F1 directive 4). Code demotes [0.45,0.55] → NO_TRADE. |
| `setup_quality` | enum `A\|B\|C` | Conviction grade; engine maps to a size-multiplier **cap**. |
| `strike` | int | Absolute index points; must ∈ `chain_csv` window. |
| `entry_level`/`stop_loss`/`target_1` | float | Absolute INR **premium** levels. Never %, never ranges. Stop on correct side of entry; target beyond entry; entry within quoted spread ± slippage buffer. Omitted field → engine treats that leg as NO_TRADE. |
| `invalidation` | string | One sentence, absolute price terms only — the calibrated-uncertainty elicitation (F1 kept #9). |
| `time_stop_minutes` | int | Advisory time-stop; engine still owns the deterministic bracket. |
| `data_conflict` | bool | `true` if snapshot fields conflict — **never reconcile silently** (silent-failure fabrication is the documented catastrophic failure mode). |
| `rationale` | string ≤25 words | Bounded audit trail, no CoT overthinking. |

**There is no size field, no max-loss field, no executable order.** Final lots = `f(stop_loss, risk budget)` computed in code.

### 3.3 Validation layer (all in code, before a human ever sees advice)

1. **Schema gate.** Rigid JSON-schema parse. On violation: **one automatic re-ask**; second failure → deterministic NO_TRADE fallback (FinMem/Guardrails pattern, tier A-corroborated).
2. **Level sanity.** Entry within quoted spread of snapshot LTP ± slippage buffer; stop on correct side; target beyond entry; reject %- or range-shaped strings; strike ∈ chain window.
3. **Echo check / numeric provenance.** Every number in `rationale`/`invalidation` string-matched against snapshot values; mismatches logged as **hallucination events** (F1 directive 3; F5 §C.3).
4. **Engine pre-empts the LLM — forced NO_TRADE regardless of output if:** `snapshot_age > 2s` at decision time; now > 15:15 IST; `minutes_to_expiry < SCALP_HORIZON`; daily-loss limit hit; `kill_switch=true`; `data_ok=false`.
5. **Borderline = non-signal.** `confidence ∈ [0.45, 0.55]` → code demotes to NO_TRADE (borderline decisions flip ~50% of runs even at low temperature, tier B but decision-changing).
6. **Temperature pinned to 0 explicitly on every call**; provider default (1.0) never accepted. T=0 is not full determinism (1–2/7 borderline items still flip) — hence rule 5.
7. **Latency.** P95 budget ≈8–10s for the single advisory call; **hard timeout 12s** → deterministic fallback, never stale advice (documented P99 tails 10–17s; congestion worst at market open).
8. **Risk-widening veto.** Any advisory implying looser risk (more size than cap, later square-off) → hard human confirmation checkpoint.

---

## 4. Invocation policy

**Cadence:** periodic advisory every **30 s**, but *only when the engine's deterministic setup pre-filter shows a live candidate*; otherwise the cycle is skipped — no LLM call (pure event-driven has no production field numbers; the 30s loop is the only documented production cadence; gating captures anti-empty-poll economics). The LLM is **never in the tick path**.

**Generation settings pinned on every call:** `temperature = 0` (explicit, never provider default); `max_tokens` small (output ≤ ~120 tokens); system prompt cached; every call logged raw + parsed + latency.

**Event triggers** (interrupt the 30s loop; all subject to dedup + **≥60–120s cooldown** + idempotency; expected 5–20/day):

| Event | Why | Tier |
|---|---|---|
| \|spot move\| > kσ in m min (default 2σ/5min) | Fast tape invalidates cached advice; documented trigger archetype. Thresholds unvalidated for NIFTY — tunable | B — R09 S12,S13 |
| IV spike / IV-crush | Options-specific: premium/greeks shift faster than spot cadence catches | B — pattern application; our own threshold |
| OI cliff / ΔOI anomaly at focus strikes | Positioning regime break; adversarial flow signal; engine computes, LLM interprets | B |
| Open-position P&L breach (unrealized loss > x% of stop budget) | Escalate with fresh advice while deterministic stop still owns the exit | B |
| `data_conflict` / snapshot staleness / feed gap | Fabrication guard: force NO_TRADE + alert | A-corroborated practitioner, decision-changing |
| Risk-parameter widening request | Mandatory human confirmation | A-practice (frontier-firm supervision norm) |
| Session start / EOD (*offline, not hot path*) | Human approves daily playbook; weekly offline critic reviews logged decisions vs outcomes | A — R09 S7 (+31% measured from reflect loop, applied out-of-band) |

**Timeout/fallback:** 12s hard timeout or second schema failure → deterministic NO_TRADE fallback message to the human; never serve stale advice.

**T=0 pinning note:** temperature 0 reduces but does not eliminate nondeterminism; borderline-flip risk is neutralized by the [0.45,0.55] demotion rule, not by re-sampling. Self-consistency N-way voting is forbidden in the hot path (latency/cost + inter-model error correlation r≈0.53–0.69 caps gains); it may exist only as an offline logging experiment at T>0.

---

## 5. The production prompt

Assembled **only** from kept, evidence-backed elements. Every block is annotated with its evidence source.

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

**Note on the CoT scaffold:** F1 directive 5 endorses an analyst-workflow scaffold (regime → OI/vol evidence → bull → bear → invalidation, plus "what kills this trade?"). It is honored *structurally* — the snapshot's regime flags/indicators pre-stage the analytic steps, the `invalidation` field carries the adversarial check, and evidence ordering does the rest — but **not** as visible long-form chain-of-thought in the response, because the finance/pattern-task evidence (CoT neutral to −36pts) and the 12s latency budget both forbid it. The tasking is classification/interpretation — continuation vs exhaustion, levels under threat, invalidation — never "predict the next candle" (F1 directive 6).

### Deliberately excluded, and why

| Excluded element | Why (evidence) |
|---|---|
| **Expert personas** ("you are a world-class scalper") | No significant accuracy gain (tier A/B); irrelevant persona details can cost ~30pts. Domain priming via field names retained instead (+2.5%) |
| **Multi-agent / in-session debate** | Voting captures most gains at a fraction of cost; debate costs 2.1–3.4× tokens with sycophancy (≤85.5%) and correct→incorrect flips (≤70%); deliberative consensus degraded accuracy 83.4%→76%; 11-call/decision topologies blow the 12s budget |
| **Long / visible CoT in the hot path** | Gains concentrate in math/symbolic tasks; neutral-to-harmful (up to −36pts) on fast finance/pattern tasks; all arithmetic lives in the engine |
| **Raw OHLC / full chain dumps** | Momentum over-extrapolation (wrong for intraday reversal) + chain hallucination + ≥10% accuracy loss from extraneous numbers |
| **Freeform-then-reformat (2-pass)** | Format tax concentrated in open-weight models; doubles the latency tail. Kept only as a config flag for open-weight swaps |
| **XML output protocol, multi-agent stop tokens, P&L-conditioned persona switching, hot-path N-way voting** | Era-specific workarounds / intraday-untested / latency-forbidden; see F5 demoted list |
| **LLM anywhere in tick/execution path** | 1.5–3s decisions + 10–17s tails vs sub-second scalping requirements |

---

## 6. Evaluation protocol — forward-only shadow log

### 6.1 Log from day one (per invocation)

- Exact snapshot JSON (the input byte-for-byte), model version, **prompt hash**, timestamp, trigger type.
- Raw response + parsed output + per-call latency; schema-validated final output; re-ask flag if used.
- The engine-computed bracket (ATR SL/target) attached to the advisory.
- **Hallucination-event flag** (quoted number ∉ snapshot) and `data_conflict` history.
- Because a human executes: log both *advice-as-given* and *execution-as-taken* (accept/decline, fill levels, slippage).

### 6.2 Forward-only, cost-honest scoring

- **Never score on data inside the model's training window.** Treat any such number as inflated up to ~2/3 and label it non-evidence. Grade only realized forward outcomes at fixed horizons (5/15/30 min) from engine-recorded prices.
- **Score components separately:**
  1. **Direction hit rate** vs coin-flip **and** vs a trivial deterministic baseline (e.g., VWAP-side momentum rule). *An LLM layer that can't beat the trivial baseline is ceremony.*
  2. **Invalidation quality** — how often the stated invalidation/stop preceded the adverse move.
  3. **Bracket capture** — realized MFE/MAE vs the engine's ATR bracket.
  4. **Calibration** — bucket stated confidence vs realized hit rate *before* ever trusting the label.
- **Net-of-cost always:** deduct brokerage, STT, exchange charges, stamp duty, slippage from every hypothetical advisory P&L. Gross Sharpe reported only as an upper bound with a FINSABER-style disclaimer.
- **Human-in-the-loop is the primary endpoint:** advice-acceptance rate, win-rate delta accepted-vs-declined, expectancy delta vs the human's unaided trades. The product claim is "improves a human scalper."
- **Regime-stratified reporting:** all metrics broken out by engine-tagged regime (trend/range, high/low India-VIX) to catch the documented conservative-in-bull/aggressive-in-bear pathology early.

### 6.3 Release gates and allowed claim language

- **Quarterly masked-value audit** (FAITH-style probe on *our* schema): mask/corrupt numeric fields, measure how often the model quotes a number not in the snapshot. This hallucination rate is a **release-gate metric** — re-run provenance checks on every model swap, including "upgrades" (FinReason: reasoning-class upgrades degrade in finance).
- **Allowed claim language:** because in-window backtesting is contamination-impossible to fix, the system may claim only (a) forward shadow-log results, net of cost, with regime stratification and n; (b) baseline-relative deltas (vs coin-flip, vs trivial rule, vs human-unaided); (c) hallucination-event and calibration statistics. It may **never** claim backtested alpha, Sharpe, or win-rates derived from pre-cutoff data, nor extrapolate paper returns into live-readiness.

---

## 7. Open questions (merged, ranked)

1. **Does the advisory beat the trivial VWAP-side baseline and the human unaided?** (F1 eval 3+6) — the single question that decides whether the LLM layer exists at all. Answerable only by the forward shadow log.
2. **Do the pre-filter + [0.45,0.55] demotion rules cut both noise and real edge?** Needs per-bucket forward stats; demotion band width is tunable after calibration data exists.
3. **Event-trigger thresholds (2σ/5min, IV-spike, OI-cliff) for NIFTY** — adopted from generic archetypes, unvalidated for index options; tune against logged false-fire rate and missed-event rate.
4. **Would a cheap open-weight model suffice?** If adopted: re-validate output-format tax (enable two-pass flag), re-run masked-value audit, compare against the same harness — never assume parity with the frontier model.
5. **Offline critic loop cadence/value** (weekly log review, +31% measured in-source but out-of-band) — pilot before productizing; keep strictly off the hot path.
6. **Snapshot hygiene marginal gains** (date anonymization, indicator ordering) — low-cost experiments only after the shadow log baseline is established.
7. **Longer-horizon reflection** (5-min cadence regime summary vs 30s tactical loop) — does a slower second cadence add anything, or is it ceremony?
