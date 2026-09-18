# S01 — Data, Features and Cadence (STE): build spec

## Terms and abbreviations

- **engine** — the deterministic Python process. It computes all numbers. This document uses this one term for it.
- **Evidence tiers:** A = peer-reviewed. B = corroborated preprint or industry evidence. C = blog or anecdote. T1/T2 = mechanism-tier tags kept from the sources.
- **NIFTY, BANKNIFTY** — NSE index names. **IST** — India Standard Time. **NSE / BSE** — Indian exchanges.
- **LLM** — large language model (the advisory layer).
- **wss** — WebSocket stream. **REST / CDN / HTTPS** — network transports. **OAuth / TOTP** — authentication items.
- **LTP** — last traded price. **LTPC** — wss mode that pushes LTP plus last-traded quantity.
- **OI** — open interest. **IV** — implied volatility. **PCR** — put-call ratio. **GEX** — gamma exposure.
- **CE / PE** — call option / put option. **ATM / ITM / OTM** — at / in / out of the money. **fut** — futures.
- **VWAP** — volume-weighted average price. **ORB** — opening-range breakout. **ATR** — average true range.
- **RV** — realized volatility. **EM** — expected move. **IVP / IVR** — IV percentile / IV rank over 252 days.
- **OFI** — order flow imbalance. **CVD** — cumulative volume delta. **VPIN** — volume-synchronized probability of informed trading.
- **RSI** — relative strength index. **EMA / MA** — (exponential) moving average. **STT** — Securities Transaction Tax.
- **θ (theta), Γ (gamma), Δ (delta), σ (sigma), vega** — option greek letters used in formulas.
- **BSM** — Black–Scholes–Merton model. **Lee–Ready-lite / tick rule** — methods that infer trade sign.
- **Row tags:** T1–T8 = transports. FR-01–28 = features. SH-01 = shadow log. CR-1–5 = conflict decisions.
  B-01–15 = banned items. HR-01–13 = hard rules. P1–P9 = payload groups. S-1–10 = storage artifacts.
  FM-01–13 = failure modes. OR-01–15 = open risks.
- **Source tags (F2, F3, F4, S##, R##)** stay for audit only.

This document combines F2 (chain and vol), F3 (microstructure and GEX), and F4 (indicators and engineering).
The reader is the engineer who builds the engine. This document is self-contained. Each section tells you what to build. Build exactly this.

**Canonical facts for the whole document:**

- NIFTY weekly expiry is **Tuesday** (since 1-Sep-2025). All expiry-day rules from F2/F3 fire on Tuesday.
- Market session: 09:15–15:30 IST. Ops gate: 09:05–15:35, Mon–Fri minus NSE holidays.
- The Upstox token dies every night at **03:30 IST**, regardless of issue time (F4).
- The LLM advisory layer runs at **≥1-min aggregated cadence. It never runs in the tick loop** (F4, corroborated by F3 nil).
- No available feed has aggressor flags. All trade signing is inferred (tick rule / Lee–Ready-lite). Signing is therefore **verification-gated** before it may influence advice (conflict resolution CR-4).

---

## 1. Ingestion architecture

```
                        ┌──────────────────────────────────────────────────────────┐
                        │  Deterministic engine (single process, async queue core)  │
                        │   bars 1s/10s/60s · feature frames · hard-rule gates ·    │
                        │   LLM snapshot builder (60s + event) · storage writer     │
                        └───▲─────────▲─────────▲─────────▲─────────▲───────▲──────┘
                            │         │         │         │         │       │
  ┌─────────────────────────┴───┐ ┌───┴─────┐ ┌─┴───────┐ ┌┴────────┐ ┌┴────┴────────┐
  │ WSS #1 · v3 · mode `ltpc`   │ │ WSS #2  │ │ REST    │ │ REST    │ │ HTTPS CDN     │
  │ NIFTY index LTP + India VIX │ │ v3 mode │ │ option/ │ │ history │ │ instruments   │
  │ (2 keys of 5,000 ltpc cap)  │ │ `full`(≠`option_greeks`│ chain?  │ │ candles │ │ + OAuth job   │
  │ push, ~tick rate            │ │ 5-depth)│ │ 30–60s  │ │ on dem. │ │ daily         │
  └─────────────────────────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────────┘
   Voltick feed: RV buckets,     Quotes+OI+IV+greeks for   Full-chain  Boot backfill   complete.json.gz
   relvol, time-of-day model,    ATM±15 CE/PE + NIFTY fut   OI/walls/   + gap repair    + key index + auth
   VIX regime.                   (~31 keys ≤ full-cap 1500) PCR,fallback                 (§6.1)
```

Transport inventory, with the reason for each cadence (rows numbered T1–T8):

| # | transport | payload | cadence | why this cadence |
|---|---|---|---|---|
| T1 | wss v3 `ltpc` | NIFTY index, India VIX | streaming push | VIX and spot feed the denominators of RV and regime at sub-second rate. Do not poll REST for this; polling wastes budget. Key use is trivial (2/5,000). [F4] |
| T2 | wss v3 `full` (fallback `option_greeks` if depth is unstable) | NIFTY futures + ATM±15 CE/PE: LTP, 5-depth quotes, OI, IV, greeks | streaming push; downsample in-process to 1 s / 10 s / 60 s bars through an async queue | `full` mode makes 5-depth **free**. The F3 trigger set (OFI / imbalance / microprice) *requires* book quotes. Key budget: ~31 keys ≪ 2,000 nominal / 1,500 combined cap. **This stream replaces F2's "REST-poll basis at 5–15 s".** Mids at ATM±1 arrive as live quotes at zero REST cost (decision CR-1). The queue decouples feed from strategy. Burst drops never block bars (F4 dhan-bot pattern). |
| T3 | REST `GET /v2/option/chain?expiry_date=current_week` | full-chain OI, IV, greeks snapshot | **every 30–60 s**, market hours only | OI follows an exchange schedule and moves slowly. (Dhan hard-limits to 1 req/3 s "because OI changes slowly"; F3: OI is usable only at ≥10 s horizons.) 1–2 req/min ≈ ≤540/day ≪ caps (50/s nominal; third-party constants 25/s / 250/min / 1,000-per-30-min — verify burst on day 1). This replaces F3's 1–3 s chain-polling idea (decision CR-2). The relative expiry keyword auto-rolls on Tuesday. |
| T4 | REST historical-candle | 1-min OHLCV backfill | once at boot + on-demand gap repair | Bootstraps 1-min bar context (ATR, σ buckets). Retry 3× with exp-backoff. If all retries fail, degrade to wss-only accumulation with a reduced-context flag. [F4] |
| T5 | HTTPS CDN `complete.json.gz` (~60 MB) + local SQLite index | instruments master | once daily, pre-08:00 | Not API-rate-limited. CSV is deprecated. Keys (`NSE_FO|num`) are per-expiry ephemeral. Expiry rollover is the #1 bug class. Resolve ATM±15 fresh every session. Fallback: `/option/contract`. [F4] |
| T6 | OAuth job (Playwright+TOTP, webhook fallback) | access token | daily 07:30–08:45 IST | The token always dies at 03:30. Re-auth long before warm-up. Verify with one cheap authed call. Silent overnight auth death is the canonical outage (§6.1). [F4] |
| T7 | NSE scrape | cross-check only (optional) | 5-min, market hours | Fragile (cookie/401/IP-ban). On any failure, disable it silently for the day. Never put it on the critical path. [F4] |
| T8 | Order API | **none** — human executes | — | Leave the order bucket (10/s) untouched on purpose. This keeps SEBI algo-registration exposure minimal. [F4] |

Output cadence contract:

1. The engine refreshes feature frames per quote event for trigger features (utility ≤30 s).
2. Frames roll up to 10 s / 60 s engine bars.
3. **The engine emits LLM snapshots every 60 s, plus event snapshots** (ORB break, EM-consumption crossing, hard-rule state flip). The 1-min LLM cadence floor is a hard banned-pattern guard (F4 demoted #8).

---

## 2. Master feature register

This register combines F2's 11 features, F3's 12 survivors, and F4's indicator plan. Result:
**28 active rows + shadow + banned**.

Roles: trigger / confirmation / regime / filter / context / execution / exit / shadow / banned.
Cadence is the engine compute cadence. "snap" means the 60 s LLM snapshot. The engine still computes
faster values for the deterministic layer. Conflict decisions are referenced as CR-x (§2.4).

### 2.1 Derivatives / vol / chain features

| # | feature | formula / params | inputs | cadence | computed-by | role | tier + source |
|---|---|---|---|---|---|---|---|
| FR-01 | `synthetic_fwd_basis` (PCP lead) | F\*=K+(mid(C)−mid(P)) at ATM±1 (rT≈0); basis=F\*−fut LTP (spot fallback); median across strikes; outlier-filter spread crossings | wss `full` mids of ATM±1 + fut LTP | per quote; 5–15 s engine roll; in snap | WSS-FULL | **trigger/confirmation** (options lead cash; log-then-arm per OR-03) | A India [F2; R03 S17/S18] + A US [S6] |
| FR-02 | `atm_iv_expected_move` | EM₁d=S·IV_ATM·√(1/252); opening straddle = intraday cap; track EM-% consumed | chain/wss IV + ATM straddle mids | open + per snap | WSS-FULL + REST-CHAIN | **context/filter** — veto late entries when EM is largely consumed | A India [F2; R03 S23; R04 S23/24] |
| FR-03 | `ivp_252` (+`ivr` display-only) | % of trailing 252 daily ATM-IV obs below current; IVR secondary | persisted daily ATM-IV series (log from day 1) | per snap | ENGINE (hist store) | **filter** — block or penalize buys when IVP>60–70; favor <30 (provisional, OR-05) | A/B for gate [F2; R04 S13/24/25/27/28]; C for IVP-over-IVR [S3] |
| FR-04 | `vrp_spread` (IV/RV) | ATM_IV ÷ trailing 5–10d RV and ÷ same-time-of-day RV bucket | IV series + RV from T1 ticks | 1–5 min | ENGINE | **filter** — require ≤~1 or falling before buys | A/B India [F2; R04 S24/25] |
| FR-05 | `div_momentum` | ΔATM-IV over 1h & 5d; VIX-spike flag | IV series, VIX | 1–5 min | ENGINE | **confirmation only**; act only on extremes (>~50%/5d); never a trigger | B [F2; R04 S29, S24/26] |
| FR-06 | `skew_rr25` + `postdrop_put_iv_flag` | IV(25ΔP)−IV(25ΔC); intraday Δskew; put-IV inflation flag after sharp drops | per-strike IV (chain greeks) | 5–15 min | REST-CHAIN / WSS-FULL | **context** low-weight; primary use = HR-07 late-put veto | A-weak [F2; R03 S6/7 weekly+; R04 S19–21] |
| FR-07 | `theta_clock_gate` | required ΔS over holding window = |Θ_window|÷Γ (+vega if event near); block if > median range of current time-of-day RV bucket | greeks per candidate strike + TOD buckets | per candidate trade | WSS-FULL + ENGINE | **filter** (per-trade arithmetic) | theory-A (θ∝1/√T) [F2; R04 S10/14] + C NIFTY timing [R04 S5/6] |
| FR-08 | `tod_vol_buckets` | per-15-min RV multipliers (NIFTY U-shape) × expiry-day decay multipliers; start from desk priors; self-calibrate after | spot tick history (self-built) | continuous | WSS-LTPC | **context/filter** — scales confidence; denominator for FR-07 | A India [F2; R04 S31/32] + B [R04 S18] + C desks |
| FR-09 | `delta_band` | long scalps Δ∈0.5–0.8 (ATM to modest ITM); reject Δ<~0.25 far-OTM | chain/wss greeks Δ | per trade | WSS-FULL | **execution** guidance at strike selection, medium confidence | A preprint [F2; R04 S12 SPX] + A retail-loss [R04 S13]; India unvalidated |
| FR-10 | `oi_walls` (merged, CR-3) | top-2 call-OI + top-2 put-OI strikes; argmax of (OI_c−OI_p)·|Γ_k| combined within ±1% of spot; distance to nearest wall in ticks; expiry-day up-weight | chain OI + BSM Γ + spot | wss-key OI live; full-chain 30–60 s; staleness-gated | REST-CHAIN + WSS-FULL | **context** (magnets, not S/R walls; pin-risk zones into expiry close) | T1 ×2 [F3: Ni et al. JFE'05; Avellaneda–Lipkin'03]; mechanism A [F2; R03 S8–10] |
| FR-11 | `gex_local_sign` + `mom_rev_selector` (merged, CR-3) | strikes |k−ATM|≤5 (±~2%): Σ OI_p·Γ_p·S²·0.01 − Σ OI_c·Γ_c·S²·0.01; sign ∈{+,0,−} with deadband=median|OI|·Γ; × illiquidity flag (spread_bps>80th pct ∨ depth<20th pct) ⇒ (−γ∧illiquid)=momentum-bias, (+γ)=reversion-bias | chain OI + IV proxy + microstructure flags | per chain poll; flag changes ≤1/5 min (deadbanded) | REST-CHAIN | **regime** — multiplicative selector on FR-15/16/18; LOW weight; valid only when India-VIX + ATM-IV are in the snapshot; **never compute aggregate signed GEX** | mechanism T1 [F3: Ni RFS'21; Barbon–Buraschi]; standalone-predictive FAILURE tag (FlashAlpha; Princeton diss.) |
| FR-12 | `flip_price_context` | strike where cumulative local GEX crosses 0 nearest spot | chain + greeks | per poll, Tuesdays only | REST-CHAIN | **context** display-only; the engine never auto-triggers on it | desk folklore C; structural test negative [F3 Princeton diss.; F2 R04 S11] |
| FR-13 | `opt_hedge_flow` (+`pcr_oi`,`pcr_vol` shadow-alongside) | Σ_k ΔOI_k·Δ_k·S, call−put signed; roll 1/5/15 min; OI-staleness-gated (>60 s no ΔOI ⇒ stale) | chain OI + BSM Δ | 1/5/15 min, effective ≥10 s | REST-CHAIN | **regime** — 5–15 min directional conditioning (fills the pocket OFI cannot reach) | T1 ×2 [F3: Hu JFE'14; Pan–Poteshman RFS'06] |
| FR-14 | `open10_opt_flow` | FR-13 + signed imbalance accumulated 09:15–09:25, then frozen and emitted all day | as FR-13 (+FR-18 pre-verification: use L1 imbalance) | once daily at 09:25 | ENGINE | **context/regime** day-bias, medium-low weight | T2 single-market [F3: KOSPI Kang/Lee JFM] |

### 2.2 Microstructure trigger set (deterministic engine only; the LLM sees rollups)

| # | feature | formula / params | inputs | cadence | computed-by | role | tier + source |
|---|---|---|---|---|---|---|---|
| FR-15 | `ofi_l1` → `ofi_10s`,`ofi_30s` | Cont–Kukanov–Stoikov signed book events; cumulative per window; normalize by L1 depth (qᵇ+qᵃ) | wss `full` L1 on fut + ATM±1 | event → 10/30 s bins | WSS-FULL | **trigger** (momentum-ignition confirm), ≤30 s horizon only; ≥1-min forecast banned (B-06) | T1 [F3 S1]; decay caveat T1 [S2] |
| FR-16 | `vol_imb_l1`,`vol_imb_l5` | I₁=(Qᵇ−Qᵃ)/(Qᵇ+Qᵃ); I₅ summed over 5 levels; z-scored on a 20-min trailing window | wss `full` 5-depth | per quote, 1 s floor | WSS-FULL | **trigger** (I₁ sub-30 s) / **regime** (I₅, 1–5 min; NSE: L2–5 ≈50% of discovery) | T1 [F3 S1] + NSE T2 [Gupta–Tripathi] |
| FR-17 | `microprice_dev` | MP=(PᵃQᵇ+PᵇQᵃ)/(Qᵇ+Qᵃ); dev=(MP−mid)/spread_ticks | L1 quotes | per quote | WSS-FULL | **trigger** co-input with FR-15 (redundant-safe) | T1 [F3 S4 Stoikov] |
| FR-18 | `signed_vol_imb_{10,60,300s}`, `cum_delta` (CR-4) | tick-rule sign; Lee–Ready-lite vs prevailing mid when interleaving permits; (V_b−V_s)/(V_b+V_s) per window normalized by trailing median volume; cum since 09:15 | LTPC ticks + L1 quotes | 10/60/300 s rolls | WSS-FULL | **shadow-armed**: trigger 10–60 s / regime 300 s **only after recorded-session signing-bias verification passes**; until then log it, and let L1 imbalance carry the trigger seat; naive standalone use is banned (alpha dies after costs [F3 S17]) | T1/T2 signing acc. [F3 S5/6]; NSE decay T2 [S15]; F4 ban-absent-verification [R06/R12] |
| FR-19 | `tick_imb_{10,60s}`, `trade_intensity`, `t_per_bucket` | (up−down)/(up+down); ticks/s ÷ same-time-of-day 20d baseline; wall-time to fill V* (25k-lot fut / strike-adaptive) | LTPC ticks | per tick; 10/60 s bins | WSS-FULL | **regime** — liquidity/event-state standardizer for all other features (the salvaged VPIN channel) | T1 Ané–Geman [F3]; T2 intensity-is-the-channel [S10] |
| FR-20 | `spread_bps`,`depth_l1_l5`,`book_slope` | 10⁴(Pᵃ−Pᵇ)/mid; ΣQ per side/level; log-depth decay OLS L1→L5 | wss `full` | per quote, 1 s floor | WSS-FULL | **regime** — impact multiplier, illiquidity flag (feeds the FR-11 selector), size-cap input | T1 [F3 S1]; T2 [S24] |

### 2.3 Tape / indicator plan (F4 survivors, merged)

| # | feature | formula / params | inputs | cadence | computed-by | role | tier + source |
|---|---|---|---|---|---|---|---|
| FR-21 | `orb_filtered` | 5/15/30-min opening range; entries 09:15–11:15; **skip** if OR width < 20th pct of 20d ATR; skip non-"in-play" days (low rel-volume, no news/expiry); stops ≥ OR width or trail OR extreme | 1-min bars, ATR(20d), FR-25, calendar | per 1-min bar in window | ENGINE (bars) | **signal — the sole surviving family**; cost floor HR-08; rolling-decay monitor (expect ~26% OOS decay) | B+ [F4; R06 S6/7/10/12/14]; replication-failure caveat [S23] |
| FR-22 | `first30_60_momentum` | first-30/60-min spot return sign and magnitude → session prior | bars | 09:45 / 10:15, then static | ENGINE | **context** state field; needs internal NIFTY replication before any weight | A− US-only [F4] |
| FR-23 | `session_clock_tags` | trend-bias 09:15–11:15 + final hour; reversion-bias 11:30–14:30; expiry buckets {open45, midday, last90}; expiry range ×1.25–1.30 | clock + calendar | per bucket | CLOCK | **regime** — gates admissible bias (anti-regime rule F4-dropped-14); F2 and F3 calendar flags merge here | A−/B [F4; R06 S1/12/19/24]; practitioner+T1/T2 [F3 expiry stats] |
| FR-24 | `vwap_bands` | session VWAP anchored at 09:15; distance in rolling-20d intraday σ; tags >+1σ, ±2σ, above/below | LTPC ticks | 1 s; snap state | WSS-LTPC | **context** — reversion bias at extremes on range days only; VWAP-cross trigger banned (B-12) | B− [F4; R06 S18 + band study] |
| FR-25 | `relvol_spike` | current 5-min volume ÷ same-time 20d median; flag ≥1.5× | fut volume ticks + hist | per 5-min bar | ENGINE | **context / confirmation filter** — the cheapest robust filter; feeds FR-21 eligibility + FR-22 replication | B− [F4; corroborated ORB + ML-filter practice] |
| FR-26 | `india_vix_regime` | VIX level + Δ vs prev close; session tag low/normal/high | T1 tick | per snap | WSS-LTPC | **context** — vol-regime gate (the Crabel/OR-filter mechanism); keep weight low (no direct NIFTY efficacy test) | B− inferred [F4]; precondition for FR-11 [F3] |
| FR-27 | `atr_trailing_exit` | ATR(14) trailing stop on candidates | bars | per bar | ENGINE | **exit mechanic** — risk management, never an entry signal (supertrend banned B-10) | D+ evidence kills supertrend [F4; R06 S15–17] |
| FR-28 | `pcr_context` (CR-5) | PCR recomputed from CE/PE OI (ignore the payload field; report unavailable-not-0 when CE/PE OI ≤ 0) | chain | 30–60 s | REST-CHAIN | **context only** — a labeled crowd-state read; **no contrarian thresholds ever** (B-01) | C community [F4; R12]; signal version rejected A-null India [F2; R03 S15/16] |

### 2.4 Shadow and banned

| # | item | disposition | why |
|---|---|---|---|
| SH-01 | `shadow_flow_log`: volume-PCR, per-strike ΔOI buildup states, signed-imbalance proxies, max-pain distance series | compute and persist from day 1; gates nothing; excluded from the LLM payload (F2: do not even render max pain; F3: "labelled weak context or skip" ⇒ skip) | US single-stock edge only [F2; R03 S1/2/4]; India OI cousins null [R03 S15]; needs an in-house backtest |
| CR-1 | Basis cadence conflict (F2 5–15 s REST poll vs F4 30–60 s chain + wss `full`) | **resolved**: basis inputs moved to wss `full` subscribed ATM±1 mids; the REST chain never carries the basis | REST budget + OI staleness; wss quotes are fresher than any feasible poll |
| CR-2 | Chain poll cadence (F3 1–3 s vs F4 30–60 s) | **resolved at 30–60 s**: the Dhan 1-req/3s limit + the exchange OI schedule make sub-10 s OI futile; wss keys cover subscribed OI | F4 engineering evidence outranks F3 aspiration |
| CR-3 | Gamma feature conflict (F2 market-Σ dealer-gamma *filter* vs F3 local-only low-weight *regime*) | **resolved to the F3 form**: NIFTY naive sign is +γ on ~95% of days (constant ⇒ no information); F2's own open risk (Indian dealer-sign assumption) weakens the filter; flip level demoted to display context; market-wide signed GEX never exposed | F3 adjudication + F2 risk note agree; mechanism T1, standalone-prediction fails controls |
| CR-4 | CVD/signed-flow conflict (F4 outright ban vs F3 keep-with-verification) | **resolved as shadow-armed**: F4's ban holds in production until recorded-session signing bias is verified (LR-lite vs tick rule, symmetric-error check); pass ⇒ FR-18 arms; fail ⇒ L1-imbalance-only permanently | F4's evidence (CVD error ~169% of magnitude) covers *unmanaged* signing; F3 supplies the management procedure |
| CR-5 | PCR role (F2 reject vs F4 context) | **resolved**: recomputed PCR may ride as labeled context; contrarian thresholds banned | layers separated, per F4 adjudication + F2's signal rejection |
| B-01 | OI-PCR contrarian thresholds (0.7/1.3) | banned (signal) | India null [F2; R03 S15/16] |
| B-02 | max pain as target/magnet | banned as target; persisted only (SH-01) | n=242 + India coin-flip [F2/F3] |
| B-03 | "highest OI = S/R wall" intraday | banned as stated; FR-10 magnet framing only | sourceless folklore [F2] |
| B-04 | VPIN / BVC toxicity | banned; inputs salvaged via FR-19 | Andersen–Bondarenko ×2 [F3] |
| B-05 | market-wide signed GEX level | banned (never computed) | ~95% constant sign; provider spread 2,250× [F3] |
| B-06 | OFI point forecasts ≥1 min | banned (≤30 s nowcast only) | lagged OOS R² ≈ 0 [F3; Cont–Cucuringu–Zhang] |
| B-07 | gamma-flip acceleration auto-trigger | banned (FR-12 context only) | Princeton structural test negative [F3] |
| B-08 | charm/vanna flow maps | banned (single-source tail) | one proprietary white paper + blogs [F3] |
| B-09 | 0DTE crash-avoidance special logic | banned (normal risk limits suffice) | attenuation evidence outvotes dissent [F3] |
| B-10 | supertrend as signal | banned (FR-27 exit mechanic allowed) | flat 40–43% WR, whipsaw+costs fatal [F4] |
| B-11 | intraday EMA/MA crossovers ≤15 min | banned | negative expectancy on all sub-daily TFs [F4] |
| B-12 | RSI entry rules; VWAP-cross trigger; naive first-candle breakout | banned (RSI/Web extreme-read tag survives in FR-24/F4 context) | D−/F grades; 52% sustain [F4] |
| B-13 | CVD / 30-depth imbalance as displayed signal | banned pending CR-4 verification | no aggressor flags; sign error [F4] |
| B-14 | ML direction-prediction >90% claims; LLM in tick loop | banned | leakage graveyard; no documented profitable per-tick LLM [F4] |
| B-15 | AVWAP signals; O/S ratio; OI-band "99% corr" papers; tick-store infra | banned/descoped | evidence gap / cross-sectional only / junk methodology / over-engineering [F2/F4] |

**Hard conflict verdict (F2 vol rules vs F3 time rules vs F4 ORB rules):** no direct contradiction
survives resolution. F2's open-suppression (HR-01) is a *buy gate*. F4's ORB is a *signal inside a
window*. The two compose into HR-01's exception clause (§3). F2's midday suppression sits inside
F4's reversion-bias window; the two use different layers, and both stay.

---

## 3. Hard rules register (single source of truth for gates)

| # | rule | action | source + tier | consistency check |
|---|---|---|---|---|
| HR-01 | Open suppression | no buy advisories 09:15–09:30; **Monday: full block 09:15–09:45**; ORB exception: buy entries eligible ≥09:30 (5/15-min OR) with FR-25 relvol pass and cost multiplier +0.5; the 30-min OR completes at 09:45 naturally | F2 [A India R04 S4/31/32; B R04 S18] + F4 ORB window [B+] | F2 said "no buys 9:15–9:45"; F4's Zerodha-tier evidence shows 9:15–11:15 long-side edge. The resolution trades F2's 30–45 min down to 30 min Tue–Fri and keeps 45 min on Monday. |
| HR-02 | Weekend premium | flat by Friday close; never hold fresh Friday-late longs into the weekend; Monday marks ≈ Friday close | F2 [A JoF R04 S15; B R04 S16] | expiry-day independent (still true with Tuesday weekly) |
| HR-03 | Expiry (Tuesday) buy cutoff | no new longs after 13:15–13:30 unless opening-straddle EM is broken **and** the tape shows strong momentum | F2 [C desks ×2 R04 S5/6 + theory A R04 S10/14] | the cutoff sits inside F4's 11:30–14:30 reversion window — coherent (both suppress trend-buys); Thursday-era stats ⇒ re-derive (OR-07) |
| HR-04 | Midday suppression | no new directional buys 11:30–13:30 (non-event), extended 12:30–14:00 on expiry; the reversion-*bias* tag spans 11:30–14:30 | F2 [C desks + A U-shape] + F4 [A−/B clock] | the windows differ by design: suppression sits inside the bias tag; both stay, on distinct layers |
| HR-05 | Expiry final-90-min pin regime | expect mean reversion toward top-OI strikes; veto breakout-chase entries into OI walls | F2 [A R03 S8–10; R04 S10] + F3 expiry_regime.last90 | consistent across F2/F3 |
| HR-06 | Non-expiry trend-day close | final ~30 min favors continuation; prefer with-trend entries | F2 [A JFE R03 S19] + F4 final-hour trend tag | no conflict |
| HR-07 | Post-drop late-put veto | after a sharp NIFTY drop + instant VIX jump: block new put buys (put IV inflated 1.3–1.5×) | F2 [A R04 S19 + C R04 S26]; powers the FR-06 flag | the Granger evidence is at 15-min scale ⇒ apply at snapshot cadence only |
| HR-08 | Cost gate | advise a scalp only if model-expected move ≥ **k=3** × all-in round trip (spread+STT+brokerage); ORB floor 2–3× ⇒ canonical 3 | F2 [A regulator R04 S30] + F4 ORB cost floor | F2 k≈3 vs F4 2–3× → resolved at 3 pending calibration |
| HR-09 | Extreme-VIX softening | at very-high VIX percentile, soften (never lift) the HR-01/FR-03 call blocks; subordinate to HR-01/07/08 | F2 [A R04 S22] | the ordering is stated to kill rule cycling |
| HR-10 | IVP gate | block or penalize premium buys when IVP>~60–70; favor IVP<~30 with rising RV | F2 [A/B corroborated; thresholds provisional → OR-05] | thresholds imported from US equity quintiles — flag this in the payload |
| HR-11 | ORB eligibility | skip if OR < 20th pct of 20d ATR; skip non-in-play days; no stops tighter than OR width | F4 [B+] | composes with the HR-01 exception |
| HR-12 | Ops market-hours gate | collect and strategize only Mon–Fri (holiday-checked) 09:05–15:35; off-hours = replay only | F4 ops spec | chain/OI flatline off-hours; wss heartbeats only |
| HR-13 | Kill-switch | check the flag file in every job on every loop; send a pre-open health summary to the alert channel by 09:05 | F4 (deltaforge pattern) | — |

---

## 4. LLM snapshot payload (data contract only — the interface design lives in doc 02)

Emission: every 60 s, plus event snapshots (ORB break, EM-threshold crossing, hard-rule flip, staleness).
Budget: **≤3k tokens** ⇒ ~35 fields, abbreviated keys, truncated precision (spot 1dp, ratios 2dp,
arrays ≤4 elements), no prose. Field list:

| # | group | fields |
|---|---|---|
| P1 | header | ts, session_state (warmup/open/midday/last90/close), is_expiry, T−min-to-close, day_of_week |
| P2 | tape | spot, fut, basis (FR-01 value + 60s delta + armed-flag), vix, vix_d (FR-26 tag) |
| P3 | vol state | atm_iv, ivp, ivr, vrp (FR-04), div_1h/5d+spike_flag (FR-05), em_consumed_pct (FR-02), tod_mult (FR-08) |
| P4 | regime flags | clock tags (FR-23), gex_local_sign×illiq → mom_rev_selector (FR-11), or_status (width-pct, in_play, break state — FR-21), first30_ret (FR-22), relvol (FR-25), vwap_sigma (FR-24) |
| P5 | flow rollups | ofi_30s_norm (FR-15), imb_l1/l5 z (FR-16), micro_dev (FR-17), sv_imb_60/300 + verification_flag (FR-18), tick_intensity (FR-19), spread_bps + illiq flag (FR-20) |
| P6 | chain | oi_walls: top2 CE OI strikes, top2 PE, max-combined, dist_ticks each (FR-10); hedge_flow_1/5/15 (FR-13); open10 (FR-14); pcr_context (FR-28); skew_rr25 + put_inflate flag (FR-06); flip_price Tue-only labeled "context" (FR-12) |
| P7 | gates | hard-rule states HR-01…11 as bitmask + human strings; theta_clock verdict per live candidate (FR-07) |
| P8 | health | per-source staleness flags (wss1/wss2/chain/auth/master), degraded_context flag |
| P9 | exclusions | max pain, shadow flow, raw CVD, market-GEX — never serialized (SH-01, B-02/05/13) |

---

## 5. Storage spec

Use no tick-store infra (QuestDB/TimescaleDB). F4 descoped it. SQLite + Parquet suffice at advisory scale.

| # | artifact | source | format / layout | retention | notes |
|---|---|---|---|---|---|
| S-1 | LTPC ticks (index, VIX) | T1 (1 s sampled) | Parquet, date-partitioned | 30 d hot / 365 d cold | powers RV bucket backfill |
| S-2 | 5-depth quote events + LTPC: fut + ATM±1 | T2 | Parquet daily; event-level during trigger windows, else 1 s sampled | 30 d hot / 90 d cold | needed for CR-4 verification + trigger ablation |
| S-3 | 1-min OHLCV bars, all ~31 wss keys | engine | Parquet | indefinite | the strategy/audit unit; gaps backfilled via T4 |
| S-4 | full-chain snapshots (OI/IV/greeks + recomputed PCR) | T3 | Parquet daily | indefinite | lightweight (~1 row-set/45 s); dedupe unchanged payloads before write |
| S-5 | engine feature frames (all FR values, 60 s) | engine | Parquet daily | 1 yr+ | source for ablation and calibration |
| S-6 | LLM snapshot payloads (P1–P8 verbatim) | engine | JSONL daily | 1 yr | replay + prompt regression |
| S-7 | **shadow feature log** (SH-01) | engine | Parquet, `shadow/` prefix | indefinite | strictly separate namespace from S-5/S-8 |
| S-8 | **advice log** | advisory layer | JSONL, fields: {ts, source: live|shadow, model, prompt_hash, advice, gates_state, realized_outcome} | indefinite | never act on `source=shadow` rows; enforce separation at the write path, not by query convention (F4 paper/live abstraction) |
| S-9 | basis lead-time log (FR-01 raw vs spot/fut, 5 s) | engine | Parquet | indefinite | feeds the OR-03 study before FR-01 arms as trigger |
| S-10 | ops: auth events, watchdog events, health summaries, kill-switch state | ops | JSONL append | 90 d | the alert channel is the primary copy |

---

## 6. Failure-mode handling

### 6.1 Watchdogs and auth (numbers from F4; F2/F3 staleness gates folded in)

| # | failure | detection | response |
|---|---|---|---|
| FM-01 | wss silent (app-level) | no application message for 30 s inside the market gate (the SDK raises only on close ⇒ build your own liveness) | reconnect with exp-backoff; **kill the old socket before you open the new one** (2-conn/user cap — reconnect storms lock you out); re-subscribe keys on reconnect |
| FM-02 | wss 401 | auth header reject | treat as an **auth failure**, not a network failure: run the T6 flow |
| FM-03 | token death (03:30 IST nightly) | scheduled | re-auth daily 07:30–08:45; verify post-auth via one cheap authed REST call; on 401 retry once, then **fail loudly to the alert channel before 09:05** |
| FM-04 | chain REST stale/failed | 3 consecutive unchanged-timestamp or failed pulls | mark chain features stale in P8; alert; gate off FR-10/11/13 |
| FM-05 | OI staleness (intraday) | no ΔOI on band strikes for >60 s | gate FR-11/13 on staleness; walls must re-confirm before use [F3 mitigation] |
| FM-06 | bar gap after wss outage | sequence/timestamp hole at resume | backfill via T4 historical REST; flag the affected bars |
| FM-07 | rate-limit pressure | HTTP 429 or bucket telemetry | step the chain poll down 30 s → 60 s → 5 min; never exceed verified caps (verify burst on day 1 against the 25/s, 250/min, 1000/30 min constants) |
| FM-08 | instruments master parse fail | at boot | keep yesterday's master **but** verify today's expiry via `/option/contract`; alert on mismatch |
| FM-09 | subscribe error / key invalid | wss subscribe ack | re-resolve keys via `/option/contract`, then retry; never cache keys across expiries |
| FM-10 | off-hours garbage | clock gate HR-12 | gate chain polling, snapshots, and bar consumers; ignore wss heartbeats; off-hours = replay mode only |
| FM-11 | burst overload | async-queue depth high-water | drop to snapshot-of-latest per key (queue decoupling — the strategy never blocks on the feed) |
| FM-12 | storage-write failure | write monitor | alert; the feature engine continues in memory |
| FM-13 | anything unrecognized | default | honor the kill-switch flag file (HR-13); prefer silence over wrong advice |

### 6.2 Rate-limit budget summary

| resource | budget | planned draw | headroom |
|---|---|---|---|
| wss connections | 2/user | 2 (T1+T2) | none — manage reconnect carefully (FM-01) |
| wss ltpc keys | 5,000 | 2 | 2,500× |
| wss full keys | 2,000 nominal / 1,500 combined | ~31 | ~48× |
| REST standard bucket | 50/s nominal (25/s, 250/min, 1000/30min unverified) | chain 1–2/min + history ≤10/day + auth 1/day | ≥100× |
| REST order bucket | 10/s | 0 (advisory only) | untouched (T8) |

---

## 7. Open risks and gaps (merged, ranked by severity)

| # | risk | severity | source | mitigation in spec |
|---|---|---|---|---|
| OR-01 | Auth automation fragility; 03:30 token death; silent overnight auth death = canonical outage | **blocking, operational** | F4 | T6 + FM-03; alert-by-09:05 contract |
| OR-02 | Indian dealer-gamma sign convention unverifiable (retail net *short* premium ⇒ the US convention may not transfer); no public positioning data | high | F2 + F3 | FR-11 capped low-weight, deadbanded, gated behind VIX/ATM-IV; A/B the multiplier off to measure contribution |
| OR-03 | The synthetic-forward lead may have compressed from hours (2009–17 studies) to minutes/seconds today | high (delays the primary trigger) | F2 | build the S-9 basis log first; arm FR-01 as trigger only after the current lead time is measured |
| OR-04 | Tick/LR-lite signing accuracy at ~1 event/s batching unverified; CVD error risk documented | high | F3 + F4 (CR-4) | shadow-armed FR-18; recorded-session verification gate; permanent L1-imbalance fallback option |
| OR-05 | IVP thresholds (60–70 block / 30 favor) imported from US equity quintile studies | medium | F2 | provisional flags in P3; NIFTY calibration from S-5 before HR-10 hardens |
| OR-06 | OI latency/staleness intraday vs feature freshness (walls, gamma, hedge flow) | medium | F2 + F3 | FM-05 staleness gating; wss-key OI preferred |
| OR-07 | All NIFTY decay/pinning/expiry-range stats are Thursday-era; the regime is now Tuesday expiry | medium | F2 + F3 | HR-03/05 flags provisional; re-derive from S-4/S-9 accumulation |
| OR-08 | The BSM-greeks vol fallback chain (chain ATM IV → India-VIX/√252 → EWMA RV) adds fragility | medium | F3 | document the fallback order in code; flag the active source in S-5 |
| OR-09 | Upstox rate-limit constants unverified | medium | F4 | day-1 burst verification; FM-07 step-down |
| OR-10 | ΔVIX→NIFTY Granger evidence at 15-min bars > scalp horizon | low-medium | F2 | FR-05 confirmation-only, never a trigger |
| OR-11 | Skew evidence entirely US/EU; deep-ITM spread drag on NSE untested (the FR-09 band may need narrowing toward ATM) | low-medium | F2 | conservative band at start; instrument-level cost logging |
| OR-12 | ORB edge thin post-replication (Sharpe −0.06 full sample) | low-medium | F4 | HR-08 cost floor + mandatory rolling-decay monitor; allocate confidence, not certainty |
| OR-13 | NSE scrape fragility if enabled | low | F4 | T7 optional, silent-disable, never on the critical path |
| OR-14 | SEBI algo-registration exposure if order routing is ever added | low (future) | F4 open Q6 | T8 documents the untouched order bucket; the compliance track owns it |
| OR-15 | The India-VIX Monday-open study is from 2019, before the weekly restructure | low | F2 | the sign is mechanically plausible; re-measure the magnitude via S-1 |

---

*Row references: T1–T8 transports; FR-01–28 features; SH-01 shadow; CR-1–5 adjudications;
B-01–15 banned; HR-01–13 hard rules; P1–P9 payload; S-1–10 storage; FM-01–13 failure modes;
OR-01–15 risks.*
