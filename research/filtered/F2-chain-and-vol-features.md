# F2: Chain & vol features — filtered

Filter of R03 (option-chain metrics) and R04 (IV & Greeks) for the NIFTY intraday scalping
advisor. Kept claims are tier-A, corroborated across ≥2 independent sources, or
decision-changing risk controls. Adjudication precedence: peer-reviewed large-n > industry
backtest > blog; India-specific > US-inferred.

## Adjudication log

| contested claim | R03 | R04 | verdict | reason |
|---|---|---|---|---|
| NIFTY OI-PCR contrarian thresholds (buy <0.7, sell >1.3) | Rejects for index ([S15] 2022–23 NIFTY study null; [S16] 120-day backtest: all buckets negative post-costs) | Silent | **REJECT** as signal | India-specific peer-reviewed + recent India backtest outrank US-single-stock folklore and retail blogs |
| Volume-/signed-flow PCR predicts index moves | Supported in US **single stocks** only ([S1][S2][S4], tier A); untested/unproven for indices; volume predictors only became significant in later NSE era [S14] | Silent | **DEMOTE to shadow feature** (log, backtest, no gating) | Edge is real but asset-class/venue-transferred; signed classification unavailable from REST quotes (see Open risks); no NIFTY-index validation, and OI-based cousins failed there |
| Max pain attracts expiry close | Rejected: 41.7% closer-rate n=242 + widening distance [S12]; India 47% [S13]; residual = crash-reversal [S11] | Desk blogs call "max-pain pinning observable" [S8, tier C] | **DROP max-pain-as-target**; keep strike-pinning | Large-n industry backtests + preprint reject; merging with pinning is a naming error, not evidence |
| Pinning to high-OI strikes near expiry | Supported, mechanism = MM delta hedging ([S8][S9][S10], tier A incl. index-level) | Corroborated [S10][S11] final-hour gamma spike | **KEEP as expiry-day context rule** | Tier-A mechanism; not an intraday S/R wall claim |
| IV percentile gates buys (high IVP = buyer trap) | Silent (supports ATM IV = expected move [S23]) | Yes: retail losses concentrate in high-IV buys [S13, tier A]; low-IV quintile longs beat high-IV by ~4.7%/trade [S27][S28, tier B]; NIFTY VRP positive [S25, B] | **KEEP as hard filter**; IVP primary, IVR secondary | Corroborated across academic + large data studies; R03 does not contradict — complementary channel. (Metric choice IVP-over-IVR rests on one tier-C blog [S3]; adopted anyway as statistically sound against spike-compression) |
| Rising IV / IV momentum = buy trigger | Silent | Only extreme (>50%/5d) IV spikes carry signal [S29]; intraday ΔVIX largely **coincident** with spot, asymmetric [S24][S26] | **KEEP only as confirmation filter, never trigger** | Avoids direct contradiction: the Granger-causality exists but at 15-min+ scale, not scalping scale |
| Skew predicts direction | Weekly+ and annual horizons, US stocks ([S6][S7], tier A) | Weak next-day at index level; vol dominates skew on conflict [S20][S21]; post-drop put-IV over-inflation penalises late put buys [S19, tier A] | **KEEP as low-weight context only** | Horizon mismatch resolves apparent conflict: tier-A skew results are not scalping-horizon; R04's intraday reading governs here |
| Dealer gamma regime → intraday reversal vs momentum | Supported ([S20] preprint + [S22] thesis + [S19] JFE intraday momentum) | Corroborated [S9] same preprint; [S11] gamma-flip pivot (vendor, C) | **KEEP as regime filter, medium confidence** | Multiple sources but one underlying preprint lineage; no India-specific or public-positioning validation |
| Options-derived prices lead NIFTY cash | Tier-A India: call-implied index leads spot ≤1h, strongest on expiry [S17][S18]; PCP IV-spread edge in US [S6] | Silent | **ADOPT as primary directional feature** (synthetic-forward basis) | Best-tier, India-specific lead-lag evidence in either file; feasibility good (see Feature spec row 1) |
| Deep-ITM > far-OTM for scalping buys | Silent | SPX 0DTE working paper: only deep-ITM call buys median-profitable [S12]; retail OTM buys are the documented losing seat [S13] | **KEEP as instrument-selection guidance, medium confidence** | Tier-A academic but US; NSE ITM spread/liquidity drag untested |

## Feature spec

| feature name | definition / formula | data needed | cadence | tier evidence | expected use |
|---|---|---|---|---|---|
| Synthetic-forward basis (PCP lead) | F\* = K + (mid(C_K) − mid(P_K)) (r·T ≈ 0 intraday); basis = F\* − futures LTP (fallback: − spot); median over ATM±1 strikes. Sustained basis shift & divergence from spot = options leading cash | Upstox REST option-chain quotes: per-strike bid/ask (market-quote depth) of calls & puts at ATM±1; futures/spot LTP. Feasible: NIFTY weekly ATM spreads tight; poll-based, no tick feed needed; mids mandatory, LTP unusable inside spread | 5–15 s poll | A India (R03 S17, S18); A US (R03 S6) | **Trigger/confirmation** — direction & timing lead |
| Dealer-gamma proxy & flip level | Σ_strikes OI·Γ(spot,IV,K), + for calls / − for puts (assumes dealers short customer flow); flip level = strike where net gamma crosses 0; regime: +gamma = mean-reversion/low-vol, −gamma = momentum/vol-expansion | Per-strike OI, IV, greeks (Upstox chain), spot | 1–5 min refresh | B+ preprint lineage, JFE-consistent (R03 S19, S20, S22; R04 S9) | **Filter** — gates mean-reversion vs momentum style |
| ATM IV expected move (India-VIX proxy) | EM_1d = S·IV_ATM·√(1/252); also opening ATM straddle = intraday move cap; track % of EM consumed | ATM call+put LTP/mid, IV | Open + each snapshot | A India (R03 S23; R04 S23, S24) | **Context/filter** — vetoes late entries when EM largely consumed |
| IV percentile (252d) + IV rank | IVP = % of past 252d observations below current ATM IV; IVR secondary display only | Persisted daily ATM-IV series (store from day 1; backfill if source available) | Per snapshot | A/B corroborated for the *gate* (R04 S13, S24, S25, S27, S28); C (single blog, S3) for IVP-over-IVR choice | **Filter** — block/penalize buys IVP > ~60–70; prefer IVP < ~30 with rising RV (thresholds provisional, see Open risks) |
| IV/RV (VRP) spread | ATM_IV ÷ trailing realized vol (5–10 d) and ÷ same-time-of-day bucket RV | IV series + spot tick history for RV | 1–5 min | A/B India (R04 S24, S25) | **Filter** — require ratio ≤ ~1 or falling before buys |
| ΔIV momentum | ΔATM-IV over 1h and 5d; VIX/IV spike flags | IV series | 1–5 min | B (R04 S29) + India Granger at 15-min (R04 S24, S26) | **Confirmation only**, act only on extreme moves (>~50%/5d); never a trigger |
| Skew snapshot (RR25) | IV(25Δ put) − IV(25Δ call); intraday Δskew; post-drop put-IV over-inflation flag | Per-strike IV from chain greeks | 5–15 min | A weak (R03 S6, S7 weekly+; R04 S19 intraday asymmetry; S20, S21) | **Context**, low weight; primary use = veto late put buys after NIFTY drops |
| Theta-clock / required-move gate | Required ΔS over holding window = |Θ_window| ÷ Γ (and vega term if event near); block buy if required move > median range of current time-of-day RV bucket | Option greeks per candidate strike + time-of-day RV buckets | Per candidate trade | Theory-tier A (θ ∝ 1/√T; R04 S10, S14) + C corroborated NIFTY decay timing (R04 S5, S6) | **Filter** — converts decay evidence into per-trade arithmetic |
| Time-of-day vol/decay bucket model | Per-15-min realized-vol multipliers (NIFTY U-shape) × expiry-day decay multipliers | Intraday spot series (self-built); desk timing priors to start | Continuous | A India (R04 S31, S32) + B thesis intra-day IV shape (R04 S18) + C desks (R04 S5, S7, S17) | **Context/filter** — scales confidence & powers theta-clock denominator |
| Buy-strike delta band | Long scalps restricted to Δ ≈ 0.5–0.8 (ATM–modestly ITM); far-OTM (Δ < ~0.25) rejected | Chain greeks Δ per strike | Per trade | A preprint (R04 S12, SPX) + A retail-loss study (R04 S13); **not India-validated** | **Execution guidance** at instrument selection, medium confidence |
| High-OI clustering levels (expiry only) | Top 2–3 strikes by total OI on expiry day = pin-risk zones into close | Per-strike OI | 15–30 min on expiry days | A mechanism (R03 S8, S9, S10) | **Context** — expect chop/pin nearby; not breakout walls |

## Time-of-day / day-of-week hard rules

| rule | action | source tier |
|---|---|---|
| Suppress fresh longs in first 15–30 min (harder block Monday open) | No buy advisories 9:15–9:45; Monday open = full block | A India: Monday India-VIX +2.35–2.44% at open (R04 S4); U-shaped vol, highest first 30 min (R04 S31, S32); B thesis IV-elevated-at-open (R04 S18) |
| Weekend premium is systematically overpriced | Flat by Friday close; no Friday-late long holds through weekend; expect Monday marks ≈ Friday close (decay pre-extracted) | A JoF (R04 S15); B OptionMetrics (R04 S16); C corroboration (R04 S33) |
| Expiry-day buy cutoff ~13:15–13:30 | No new longs after cutoff unless opening straddle EM already broken AND strong momentum tape | C desks ×2, mutually corroborating (R04 S5, S6) + 1/√T decay theory (R04 S10, S14) |
| Midday suppression | Inhibit new directional buys ~12:30–14:00 on expiry days (11:30–13:30 on non-event days) | C desks (R04 S5, S7) consistent with A U-shape lows (R04 S31, S32) |
| Final 60–90 min: pinned regime near high-OI strikes on expiry | Expect mean-reversion to pin zone; veto breakout-chase entries into top-OI strikes | A (R03 S8, S9, S10; R04 S10 on final-hour gamma) |
| Intraday momentum into close (non-expiry trend days) | Last ~30 min favors continuation of rest-of-day move; prefer with-trend entries in final hour | A JFE (R03 S19) |
| Post-drop late-put veto | If NIFTY dropped sharply with instant VIX jump, block new put buys (put IV inflated 1.3–1.5× beyond sticky-strike) | A (R04 S19) + C 15-min evidence (R04 S26) |
| Cost gate | Advise a scalp only if model-expected move ≥ k × round-trip cost (spread + STT + brokerage); default k ≈ 3 pending calibration | A regulator (R04 S30: costs ≈ 28% of retail F&O losses); k is our parameter |
| Extreme-VIX contrarian context | At very high VIX percentile, soften (not lift) the high-IVP buy block for **calls** — documented bounce context | A (R04 S22); subordinate to all rules above |

## Demoted/dropped claims + reasons

- **Static OI-PCR thresholds (0.7/1.3 contrarian rules)** — DROPPED. India-specific null results (R03 S15, S16); reverse-causality critique; all buckets unprofitable post-costs.
- **Volume-PCR / bid-ask-imbalance flow** — DEMOTED to shadow feature. Tier-A edge is US single-stock next-day (R03 S1, S2, S4); NIFTY-index OI cousins failed (R03 S15); signed classification needs trade-side data REST quotes don't provide. Log per-strike volume/OI deltas from day 1; gate nothing until our own backtest.
- **Max pain as expiry magnet/target** — DROPPED. n=242 live backtest (R03 S12), India 47% coin-flip (R03 S13), crash-reversal confound (R03 S11). Retain zero features; do not even render as "target" to the LLM.
- **"Highest Call OI = resistance / highest Put OI = support" as intraday S/R** — DROPPED as stated (uncited folklore; R03 flags "70–80% holds" figure as sourceless). Reframed and kept only as expiry-pinning context (Feature spec row 11).
- **OI-band predictive literature claiming ~99% correlation** — DROPPED, junk methodology (R03 S24). Marker: treat Indian OI-S/R papers as presumptively low quality.
- **ΔOI × price buildup states (long/short buildup) as predictive signal** — DEMOTED to LLM context note only. No peer-reviewed predictive study of buildup states (R03, finding S14-mixed); OI cannot be signed from chain data.
- **O/S (option/stock volume) ratio** — DROPPED for index timing: cross-sectional stock effect only (R03 S3), no NIFTY analogue.
- **Exact intraday IV-compression clock (e.g., "crush resolves by 10:10", event-crush-in-minutes, post-event delay rules)** — DEMOTED to prior heuristics inside the time-of-day bucket model. Single tier-C practitioner source (R04 S17); retained qualitatively via tier-A U-shape + Monday effects.
- **Expiry-day statistics "68% stay inside straddle EM, +25–30% range"** — DEMOTED: single desk blog (R04 S7). The straddle-EM feature itself survives on tier-A footing (R03 S23; R04 S23, S24).
- **"High IVR → probability edge"** — DROPPED: fixed delta already prices it; win rate identical across IVR (R04 S2, n=166k).
- **Vega-based intraday signals** — DROPPED for expiry-day scalps: gamma/theta dominate, vega near-irrelevant except event windows (R04 S10, S14).

## Open risks — where evidence is thin

- **Data availability (blocking for shadow flow feature):** whether Upstox REST polling yields reliable per-strike *intraday* volume deltas and OI (NSE OI update cadence inside snapshots unknown; rate limits cap poll frequency) is unverified. Signed (buyer/seller-initiated) flow is unobtainable from quotes; imbalance proxy error unquantified.
- **Synthetic-forward lead freshness:** R03 S17/S18 are hourly-scale studies on 2009–2017-era data; modern NSE microstructure likely compresses the lead to minutes or less. Must build a basis log first and measure current lead-time before letting it trigger anything.
- **Synthetic-forward noise:** PCP basis from mids at ATM±1 is noisy around spread crossings, roll/expiry transitions, and low-depth minutes; needs outlier filtering before use.
- **IVP/IVR buy thresholds (60–70 block / 30 favor) are imported** from US equity quintile studies (R04 S27, S28); NIFTY-specific calibration is an explicit open item of both raw files.
- **Dealer-gamma sign assumption** (dealers short customer flow) is unverified in India; SEBI loss data imply Indian retail is net *short* premium — the US sign convention may not transfer. No public GEX/positioning exists.
- **Post-2025 Tuesday-expiry regime:** all NIFTY decay/pinning/expiry-range numbers are Thursday-era desk studies (R04 S5, S6, S7); re-derive under current weekly structure.
- **ΔVIX→NIFTY Granger evidence is at 15-min bars (R04 S26);** our scalping horizon is below the demonstrated signal scale.
- **Skew intraday evidence is entirely US/EU** (R03 S6, S7; R04 S19–S21); NIFTY skew behavior untested.
- **Deep-ITM delta guidance** is SPX-derived (R04 S12); NSE ITM strikes have wider spreads — the Δ-band may need narrowing toward ATM.
- **India VIX Monday effect study (R04 S4) is 2019-era,** pre weekly-expiry restructure; magnitude may differ but sign is mechanically plausible.
