# F5: Prompts & architecture — filtered

Quality-gated merge of R08 (prompt engineering) and R09 (hybrid architecture) into ONE advisory-interface spec for a NIFTY options intraday-scalping advisory bot (Python engine computes snapshots → LLM advises → code validates → human executes).

## Adjudication log

| contested claim | R08 | R09 | verdict | reason |
|---|---|---|---|---|
| Output format tax: freeform-then-reformat (2-pass) vs strict JSON | S7/S8 (A/B): format restriction degrades reasoning, two-pass recovers it on open-weight models; BUT S8: latest closed models show little tax; S10/S11 (A): CoT hurts on finance/pattern tasks | Latency budget demands 1 call (P95 ≈ 3× stage medians, hard timeout 12s); P98 multi-call pipelines compound tail latency | **Single-pass strict JSON schema mode on a frontier closed model; two-pass freeform→reformat kept only as a config flag if the model is ever swapped to open-weights** | The tension dissolves by model class: the tax S7/S8 measures is concentrated in open-weight models; the finance/pattern-task evidence (S10/S11) independently argues against long CoT anyway. Adding a second formatting call doubles the latency tail R09 forbids. Keep rationale ≤25 words, answer-first (S6 Lopez-Lira pattern). Re-validate on our snapshots if a cheap open model is adopted (R08 open question 1). |
| Snapshot encoding: compact structured JSON vs token-cheap CSV | S19–S21 (B/C): pretty JSON costs 2.5–2.6× CSV tokens for dense flat data at equal-or-worse accuracy; BUT JSON/YAML win on hierarchical data | Recommends "compact structured snapshot JSON" (Greeks/IV/ΔOI, flags, window stats) ≤1.5–3k tokens | **Mixed envelope: JSON outer envelope; dense numeric arrays as embedded CSV strings; indicators as flat k=v line; only small hierarchical context (account, meta) as JSON** | Both are right about different layers. R09's "JSON" is about compactness/compression vs raw ticks — not contradicted; R08's token-economics apply to the payload fields. R08's own skeleton already encodes this split. |
| Multi-agent debate vs single agent vs adversarial second opinion | S16 (B, corroborated by S22 A, S24 A): deliberative consensus degrades accuracy 83.4%→76% (persuasive error propagation); independent confidence-weighted voting beats debate; S23 (C): debate improved directional stability on volatile assets | P2 supervisor-firm (TradingAgents) explicitly ruled "overkill and too slow/costly for intraday scalping"; P1 code-as-arbiter is the safe default | **One advisory agent. No in-session debate. Adversarial check = cross-model independent vote, fired only on escalations; never deliberation** | Single agent is forced by R09's latency/cost budgets (TradingAgents: 11 LLM calls/decision). If a second opinion is wanted, it must be an *independent, non-debating* cross-model sample whose disagreement triggers NO_TRADE/human escalation (TrustTrade-style divergence discounting) — this is the defensible reading of "adversarial second opinion," reconciled with R09's rejection of debate topologies in the hot path. S23's stability gain is demoted to C-tier/untested for 1–15min horizons. |
| Who owns numbers/sizing | P2/S2/S4/S9: absolute levels from LLM; size, max-loss and validity enforced in code; LLMs unreliable at arithmetic | P1/S2/S3/S4: LLM never emits an executable order or a number the engine didn't compute; engine = sole arbiter of numbers and risk limits | **LLM outputs levels + qualitative setup grade; engine computes all sizing and gates everything** | Fully consistent across both sources; this is the strongest corroborated design rule in the corpus. |
| Invocation: periodic-only vs event-driven | n/a | S13 (B): empty polls burn tokens, arrive up to one interval late; S11 (B, field numbers): 30s ambient refresh + cached scenarios works in production; S12 (B): event triggers with conviction ledger; needs dedup/cooldown/idempotency | **Hybrid: 30s periodic advisory gated by a deterministic setup pre-filter + event interrupts with dedup and ≥60–120s cooldown; 12s hard timeout with deterministic fallback** | Pure event-driven alone has no production field numbers for our case; the 30s loop is the only documented production cadence (S11). Gating the periodic call behind a cheap engine pre-filter captures S13's anti-empty-poll economics without losing heartbeat coverage. |

## Interface spec

### A. Engine → LLM input schema

JSON envelope with CSV-valued dense blocks. Total budget: **≤3,000 input tokens** (measured: ~1.5–3k for this shape, R09 S9; ≈$0.005–0.015/cycle Haiku-tier uncached, far less with cached system prompt).

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

Size discipline (decision-relevant, from R08 S19–S21 + R09 context findings):
- Last 15 one-minute bars only; chain windowed to ATM±4; pre-computed indicators, never raw ticks or full chains (SMETimes S16 / PatchInstruct S17, tier B: stat/patch summaries beat raw rows).
- Rationale for CSV blocks: −60% tokens vs pretty JSON at equal accuracy on dense numeric data.
- All numbers engine-computed; LLM may quote them but never derive new ones (R09 P1).

### B. LLM → output contract

**Chosen mode: single-pass strict JSON-schema structured output, answer-first, no visible CoT.** (Two-pass freeform-then-reformat retained as a documented fallback flag for open-weight models only — see adjudication row 1.)

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

Hard semantics (stated in prompt for consistency, *enforced in code*):
1. All levels absolute INR (index points for `strike`; premium for entry/stop/target). Never %, never ranges. Optional fields omitted → engine treats as NO_TRADE for that leg. [R08 P2]
2. Any exact level/OI/IV/delta the rationale cites must be a value present in the snapshot; conflicts → `data_conflict: true`, never reconcile silently. [R08 P1]
3. `action` ∈ {LONG_CALL, LONG_PUT, NO_TRADE}; NO_TRADE is the required output on mixed signals, stale/missing data, or engine-flagged R:R below minimum. Escape hatch is a first-class valid answer. [R08 P3/P6 anti-decisiveness rule]
4. No size field. `setup_quality` (A/B/C) is an advisory conviction grade the engine maps to a size-multiplier **cap**; final lots = f(stop_loss, risk budget) computed in code. [R08 S3/S4/S9; R09 P1]
5. `rationale` hard-capped at 25 words — bounded audit trail without CoT overthinking. [R08 S6/S10/S11]

### C. Validation layer (all in code, before a human ever sees the advice)

1. **Schema gate:** rigid JSON-schema parse; on violation one automatic re-ask; second failure → deterministic NO_TRADE fallback (FinMem/Guardrails pattern, R08 S3/S4 — tier A corroborated).
2. **Level sanity:** entry within quoted spread of the snapshot LTP ± slippage buffer; stop on the correct side of entry; target beyond entry; reject % / range-shaped strings. Strike ∈ chain_csv window.
3. **Echo check:** every number in `rationale`/`invalidation` cross-checked against snapshot values; mismatches logged as **hallucination events** (R09 supervisor design, S2/S3/S4).
4. **Engine pre-empts LLM:** action forced to NO_TRADE regardless of output if snapshot_age > 2s at decision time; now > 15:15 IST; minutes_to_expiry < SCALP_HORIZON; daily-loss limit hit; kill_switch; `data_ok=false` (silent-failure fabrication guard, R09 S3).
5. **Borderline=non-signal:** confidence ∈ [0.45, 0.55] → code demotes to NO_TRADE (R08 S17/S18: borderline binary decisions flip ~50% of runs even at low temperature).
6. **Determinism:** temperature explicitly pinned to **0** on every call; provider default (1.0) never accepted; raw response + parsed fields + latency logged per call. T=0 is not full determinism (1–2/7 borderline items still flip) — hence rule 5 (R08 S17/S18, tier B but decision-changing).
7. **Latency:** P95 budget ≈ 8–10s for the single advisory call; hard timeout 12s → deterministic fallback mode, never stale advice (R09 S8/S10: P99 tails of 10–17s documented; provider congestion worst at market open).
8. **Risk-widening veto:** any advisory that would widen a risk parameter (more size than cap, later square-off) → hard human confirmation checkpoint (R09 P1 hybrid checkpoints; Man Group "not unsupervised yet", S18).

## Invocation pattern

**Cadence:** periodic advisory every **30 s** *only when the engine's deterministic setup pre-filter shows a live candidate*; otherwise the cycle is skipped (no LLM call). Model class: Haiku/Sonnet-tier non-reasoning (TTFT < 1.2 s), system prompt cached. Cost: order $1–4 per 3.5 h session (R09 S9/S11/S21). A 5-min cadence is acceptable for regime-level reflection only; the LLM is **never in the tick path** (measured 1.5–3 s decision latency ≈ 30× the scalping budget — R09 S10/S8, decision-changing).

**Event triggers** (interrupt the 30 s loop; all subject to dedup + ≥60–120 s cooldown + idempotency per R09 S13; expected 5–20/day):

| event | why | source tier |
|---|---|---|
| \|spot move\| > kσ in m minutes (default 2σ/5min) | Fast tape invalidates any cached/cadence advice; the documented trigger archetype | B — R09 S12 (σ-deviation triggers), S13 (event > polling); thresholds unvalidated for NIFTY, tunable |
| IV spike / IV-crush detection | Options-specific: premium and greeks shift faster than spot-cadence catches | B — R09 S12/S13 pattern application to our instrument; our own threshold |
| OI cliff / ΔOI anomaly at focus strikes | Positioning regime break; adversarial flow signal | B — same provenance; engine-computed event, LLM interprets |
| Open-position P&L breach (unrealized loss > x% of stop budget) | Escalate to human with fresh advice while deterministic stop still owns the exit | B — R09 escalation design (S12-style triggers + human checkpoint) |
| `data_conflict` / snapshot staleness / feed gap | Silent-failure fabrication is the documented catastrophic LLM failure mode; force NO_TRADE + alert | A-corroborated practitioner — R09 S3, decision-changing |
| Risk-parameter widening request | Any advice implying looser risk → mandatory human confirmation | A-practice — R09 S18/S19 (frontier-firm human supervision norm) |
| Session start / EOD (offline, not hot path) | Human approves daily playbook; critic agent reviews logged decisions vs outcomes weekly | A — R09 S7 (+31% measured from Reflect loop), applied out-of-band |

## Prompt skeleton

```
SYSTEM
You convert machine-generated NIFTY options snapshots into one trade
recommendation for a human scalper. You never compute numbers; every
number you output must appear in the snapshot. Domain context — NIFTY
index options, intraday scalping, INR premiums, IST timestamps —
is given by the field names; answer for this domain only.
                                            [primed domain, no persona — R08 S12–S14]

HARD RULES (also enforced in code):
1. action ∈ {LONG_CALL, LONG_PUT, NO_TRADE}. When signals are mixed,
   data is stale/missing, or reward-to-risk looks marginal, answer
   NO_TRADE. Do not manufacture a direction to appear decisive.
                                            [R08 P3 escape hatch + P6 anti-decisiveness]
2. entry_level, stop_loss, target_1, strike are absolute INR levels.
   Never percentages, never ranges. Omit a level you cannot justify.
                                            [R08 P2 anti-parse-failure rule]
3. Quote snapshot values verbatim. If snapshot fields conflict, set
   data_conflict=true instead of reconciling silently.
                                            [R08 P1 verified-numbers grounding]
4. Do not output any size or max-loss figure. Grade the setup as
   setup_quality A/B/C; sizing is computed by the caller.
                                            [R08 S3/S4/S9 + R09 P1 code-as-arbiter]
5. rationale ≤ 25 words; invalidation = one sentence in price terms.
                                            [R08 S6 bounded answer-first; S10/S11 anti-overthinking]
6. No reasoning chain in the response. Output the JSON object only.
                                            [R08 S8/S10/S11; single-pass structured mode]

USER (per call)
<trigger: periodic|event:TYPE>               [R09 P4/S13 event-context]
Snapshot (JSON envelope with CSV blocks —
dense numerics as CSV for token cost):      [R08 S19–S21 + R09 context-compression findings]
<meta / regime_flags / spot_1m_csv / chain_csv / indicators_csv /
 events_csv / account — exactly per Interface spec §A>

Respond with ONLY the JSON object of Interface spec §B.
```

Generation settings: **temperature = 0 pinned explicitly** [R08 S17/S18]; max_tokens small (output is ≤ ~120 tokens); system prompt cached [R09 S9/S11]; every call logged raw + parsed + latency for the weekly critic loop [R09 S7/P3] and for hallucination-event statistics [R09 S2/S3].

## Demoted/dropped + reasons

- **TradingAgents full multi-agent firm / in-session debate** — demoted to offline research tooling only. 11 LLM calls/decision; P95 latency and cost blow every intraday budget (R09 S8/S10/S1); deliberative consensus measurably *hurts* accuracy (R08 S16: 83.4%→76%). Backtested alpha additionally discounted 50–72% by contamination findings (R09 S4/S5/S6).
- **Expert personas ("you are a world-class scalper")** — dropped. Tier-A/B evidence converges: no significant accuracy gain (R08 S12 GAIL; S14 EMNLP); irrelevant persona details can cost ~30 pts. Domain *priming* via field names retained instead (small, consistent +2.5% — R08 S13).
- **FinMem P&L-conditioned self-adaptive persona switch** — demoted to offline A/B. Winning variant was daily stock trading (finmem Sharpe 2.50 vs −0.79 static) but untested intraday and risks a feedback loop with our own P&L (R08 P5; R08 open question 4; alpha itself −71.85% post-cutoff per R09 S4).
- **Heavy/visible CoT in the advisory call** — dropped. CoT's gains concentrate in math/symbolic tasks (R08 S9); it does not help (S10) and can badly hurt (−36 pts, S11) on fast pattern/finance tasks; all arithmetic lives in the Python engine (R09 P1).
- **Pretty-JSON snapshots** — dropped for dense numerics (−60% tokens with CSV at equal accuracy, R08 S19/S20); JSON retained only for the small hierarchical envelope.
- **XML output format (FinAgent)** — demoted to optional small A/B. Era-specific workaround for pre-structured-outputs GPT-4 quoting fragility; modern JSON-schema mode plus a code re-ask loop subsumes it (R08 S5, open question 3).
- **LLM anywhere in the tick/execution path** — dropped outright. Measured 1.5–3 s decisions, 10–17 s tails vs sub-second scalping requirements (R09 S8/S10); entry/exit gating, stops and sizing are 100% deterministic Python.
- **Published headline returns (FinMem 61.8%, TradingAgents Sharpe ≤8.21, FinAgent +36%)** — demoted from evidence of value to hypothesis only: post-cutoff evaluation erases 50–72% (R09 S4/S5), 20-yr broad backtests show regime-blindness (R09 S6). Rule: paper-trade and evaluate **post-knowledge-cutoff only**.
- **TradingAgents stop-token protocol strings ("FINAL TRANSACTION PROPOSAL")** — dropped; irrelevant with no multi-agent state machine.
- **Self-consistency N-way voting in the hot path** — demoted to a logging experiment (sample offline at T>0); R08 S16's inter-model error correlation (r≈0.53–0.69) caps gains, and latency/cost forbid N>1 live calls. Borderline-flip risk is instead neutralized by the "borderline=non-signal" code rule.
