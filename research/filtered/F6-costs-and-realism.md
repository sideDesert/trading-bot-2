# F6: Costs & realism — filtered

Merged and quality-gated from R10 (backtest rigor + exact Indian costs) and R11 (India retail reality + regulation). Tier-A / primary / decision-changing items kept; practitioner explainers and anecdotes demoted (see last section). **All 2026 regulatory facts marked "reverify on build day" — charges must be config-driven, never hard-coded** (STT hiked twice in 18 months: Oct 2024, Apr 2026).

## Constants table 2026 — charge/regulation | value | source | reverify-by date

| Item | Value (authoritative) | Source | Reverify-by |
|---|---|---|---|
| STT, option **sale**, on premium | **0.15%** (history: 0.0625% → 0.1% on 1-Oct-2024 [Finance (No.2) Act 2024] → **0.15% on 1-Apr-2026** [Finance Act 2026]; all three steps true, no contradiction) | BSE notice 20260331-7; Zerodha bulletin 445377; NSE circular (Bigul PDF); CNBC-TV18 | **Build day** (rate has drifted twice in 18 mo) |
| STT, option exercise | 0.15% of intrinsic (buyer pays; was 0.125%) | Same as above | Build day |
| STT, futures sale | 0.05% (context only; bot trades options) | Same as above | Build day |
| Brokerage | Flat **₹20 per executed order**, each side (discount broker; one order per leg assumed) | Zerodha charges page (live) | Build day |
| NSE transaction charge, equity options | **₹35.53/lakh of premium per side = 0.03553%** | Zerodha live tariff. **Contradiction resolved:** NSE circular FA64232 (Oct-2024) set ₹35.03/lakh under SEBI uniform/true-to-label regime; the live broker pass-through of ₹35.53 wins as the operative rate. Difference <₹0.04/side/lot — immaterial, but use 0.03553%. | Build day |
| GST | **18% on (brokerage + exchange txn + SEBI fee)** | Zerodha | Build day |
| SEBI fee | ₹10/crore of turnover (0.0001%), each side | Zerodha | Build day |
| Stamp duty | 0.003% of buy-side premium | Zerodha | Build day |
| NIFTY lot size | **75 units** (25→75 for contracts from 20-Nov-2024; ₹15–20L min contract value) | SEBI/HO/MRD/TPD-1/P/CIR/2024/132; NSE FAOP64625 | Build day |
| 1 lot notional / point risk | ₹15–18L notional; **₹75 per 1 index point** (100-pt adverse move = ₹7,500) | Derived from lot=75 | Static |
| Tick | ₹0.05 ⇒ **₹3.75 per tick per lot** | NSE contract spec | Static |
| Expiry day | **Tuesday** for ALL NSE expiries (Thu→Tue for contracts expiring on/after 1-Sep-2025; first Tue weekly = 2-Sep-2025). **Contradiction resolved:** R10 open-question flagged the move; R11's NSE circular FAOP68747 is primary → Tuesday confirmed. BSE/SENSEX = Thursday. | NSE FAOP68747 | Build day (regime has moved twice since 2024) |
| Weekly contracts | NIFTY only on NSE; SENSEX only on BSE. BANKNIFTY/FINNIFTY/MIDCPNIFTY weeklies dead since Nov-2024 | SEBI 2024/132; ET reporting | Build day |
| Upfront option premium collection | Since 1-Feb-2025 (full premium debited at order) | SEBI 2024/132 | Build day |
| +2% ELM on short options on expiry day; no calendar-spread margin benefit on expiry leg | Since 20-Nov-2024 / 1-Feb-2025; short-side expiry margin ≈ ₹1.65–1.7L/lot vs ~₹1.5L normal | SEBI 2024/132 (NiftyDesk figure = B-tier, keep as ballpark) | Build day |
| Intraday index FutEq limits | From 1-Oct-2025: NET ₹5,000 cr, GROSS ₹10,000 cr/side per entity per index; ≥4 random snapshots (one mandatory 14:45–15:30); expiry-day ASD penalties from 6-Dec-2025 | SEBI/HO/MRD/TPD-1/P/CIR/2025/122 | Build day |
| Retail <10 orders/sec | Above → exchange algo-registration territory; keep bot well under | Upstox/SEBI-NEST practice (B-tier) | Build day |
| Median option round-trip cost (empirical) | **59.1 bps of premium**: 28.4 bps statutory+brokerage + 30.7 bps spread (842k contract-minutes, NIFTY/BANKNIFTY) | alphabench study (empirical, tier-A quality) | Re-baseline with our own fill data in pilot |

## Cost model — parameterized round-trip equation with worked lot=1 and lot=5 examples

**Definitions:** Pe = entry premium (₹/unit), Px = exit premium, L = lots, U = 75L units, one order per leg (L lots filled in one order per side).

**All-in round-trip cost:**

```
C(L, Pe, Px) = 40                                                     # brokerage 2×₹20
  + 75·L · [ 0.0015·Px            +   # STT (sell side)
             0.0003553·(Pe+Px)    +   # NSE txn, both sides
             0.000001·(Pe+Px)     +   # SEBI ₹10/cr
             0.00003·Pe         ] +   # stamp (buy side)
  + 0.18 · ( 40 + 75·L · 0.0003563·(Pe+Px) )   # GST on (brk + txn + SEBI)
  + SLIP                                                              # spread/slippage
SLIP ≈ 75·L · max(half quoted spread, 1 tick) · 2 legs
     ≈ 75·L · 0.00307·((Pe+Px)/2)     # alphabench median panel: 30.7 bps, ~52% of the bill
```

Per-unit cost = C / (75L); **breakeven ticks = per-unit cost / 0.05**.

**Worked example, L=1, Pe=Px=₹100** (zero gross P&L, ATM weekly):

| Component | ₹ (round trip) |
|---|---|
| Brokerage | 40.00 |
| STT (0.15% × 7,500 sell premium) | 11.25 |
| NSE txn (0.03553% × 15,000) | 5.33 |
| SEBI (₹10/cr) | 0.02 |
| Stamp (0.003% buy) | 0.23 |
| GST 18% | 8.16 |
| **Explicit total** | **₹64.98/lot = ₹0.87/unit ≈ 17 ticks ≈ 0.87% of premium** |
| + Slippage (30.7 bps median) | ≈ +₹23/lot |
| **All-in** | **≈ ₹88–95/lot = ₹1.18–1.25/unit ≈ 24–25 ticks ≈ 1.2–1.3% of premium** |

**Worked example, L=5, Pe=Px=₹100** (premium/side ₹37,500; turnover ₹75,000):
Brokerage ₹40 · STT ₹56.25 · txn ₹26.65 · SEBI ₹0.08 · stamp ₹1.13 · GST ₹12.01 ⇒ **explicit ₹136.11 total = ₹27.2/lot = ₹0.363/unit ≈ 7.3 ticks ≈ 0.36% of premium**. +Slippage ≈ ₹23/lot (per-unit spread unchanged) ⇒ **all-in ≈ ₹251 = ₹50/lot = ₹0.67/unit ≈ 13–14 ticks ≈ 0.67% of premium**.

**Breakeven math & scaling law:**
- Index breakeven: with ATM delta ≈ 0.5, underlying must move ≈ **2.5 pts (1-lot) ≈ 1.4 pts (5-lot)** just to offset friction before any alpha.
- Flat ₹40 brokerage dominates single-lot scalping: ~43 bps at ₹25k position vs ~25 bps at ₹3L (alphabench). Explicit cost/lot falls 87→30 bps from 1 to 10 lots. **Single-lot scalping is structurally the most expensive way to trade** — encode a sizing floor (≥5 lots, see Q below) or accept 2× cost drag.
- **Minimum viable holding time (cost-implied):** costs are a fixed toll; edge must scale with hold. Breakeven = 23.4% of a typical 15-min move but 4.7% of a full-session move → **sub-15-min scalps are structurally marginal; default horizon 30 min–2 h (breakeven capture 8–17%)**.
- Sensitivity: exiting at Px=₹80 cuts STT to ₹9 (−₹2.3); at ₹130 STT ₹14.6. Brokerage/GST dominate and are fixed.
- **Minimum-edge alert gate:** expected MFE (signal forecast) ≥ **3× all-in cost** before firing — single-lot: ≥ ~₹3.6–4/unit ≈ ≥ 75–80 ticks of expected move.

## MAE/MFE & evaluation protocol — exact steps + stop/target derivation rules + forward-only shadow-log design

**Excursion instrumentation (mandatory in sim AND live shadow log):**
1. Per trade log entry price/time + running min/max of option **mid price every tick** while open, plus recorded bid/ask at entry/exit. MAE = entry − min(adverse-side); MFE = max(favourable-side) − entry.
2. Normalize to R: MAE_R = MAE / planned initial risk per unit; MFE_R likewise (ATR units if risk varies) so trades are comparable across regimes.
3. Accumulate **≥100 trades per setup type** (bucketed by regime: trend vs chop; expiry-Tuesday vs non-expiry). 50+ absolute minimum; below that percentiles are noise.
4. **Stop calibration — winners only:** filter to winning trades, bucket winners' MAE_R in 0.2R bins, proposed stop = **p85–p90 of winners' MAE** (sanity shortcut: 1.1–1.2× mean winners' MAE). A shallower stop clips real winners; deeper pays for losers without saving winners.
5. **Target calibration:** candidate target = **winners' median MFE**. Compute capture ratio = realized avg win / avg winners' MFE; if < **0.70**, exit donates profit → widen target or trail. Bot alert carries: stop = winners' p90 MAE, target = winners' median MFE.
6. Losers' check: losers with small MAE that then explode past the stop ⇒ the problem is **entries**, not stops — fire the entry-quality filter, don't widen stops.
7. Anti-overfit: re-derive percentiles on rolling window (last ~3 months / 200 trades); **refuse stop changes < 0.1R**; never calibrate stops on the same sample used to select the signal; recompute weekly from live logs.

**Sizing (advisory output per alert):** size = min(¼–½ Kelly from trailing ≥100-trade stats, **1–2% NAV risk cap**, margin cap). Full Kelly never suggested: full Kelly ⇒ 30–50% drawdowns and is catastrophically wrong under p mis-estimation (55% WR over 100 trades has ±10% CI). ½-Kelly ≈ 75% of growth at ~half variance; ¼-Kelly ≈ 56% at ~quarter variance.

**Forward-only shadow-log design (mandatory evaluation architecture):**
- The system **never backtests an alert it didn't log forward in real time**. Every candidate alert is shadow-logged at emission time with: entry quote (bid/ask, never mid/LTP fills), tick-level MAE/MFE mid-price path, hypothetical fill at quote + realized-spread model, full cost equation applied, and the signal snapshot.
- Trials diary: **log every configuration ever tested** — undisclosed search intensity is the most corrosive overfit. For N skill-less trials, E[max SR] ≈ (1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne)) ≤ √(2 ln N): N=10 junk trials already imply expected IS Sharpe 1.57; N=1,000 ⇒ ~3.26.
- Go-live gates (all must hold): (a) **DSR > 0.95 given N trials attempted** on the stitched out-of-sample curve; (b) walk-forward stitched-OOS with **OOS/IS decay ratio ≥ 0.5** and stable parameters across windows (anchored ≈ rolling); (c) purged + embargoed K-fold (or CPCV) for any ML component — financial labels span forward windows; standard CV leaks; (d) **≥100 forward shadow trades** (needed anyway for MAE/MFE percentiles) before any user-facing alerting.
- Backtests use the hard cost model above with per-leg slippage = max(half quoted spread, 1 tick); exits never simulated at mid/LTP.

## Reality guardrails — capital floor, expectancy honesty, day/time cautions merged from both files

**Loss base rates (SEBI primary studies — contradictions resolved, all true, successive vintages):**

| Vintage | Losers | Aggregate net loss | Avg loss/trader |
|---|---|---|---|
| FY22–24 | 92.8% ("93%") of 1.13 cr individuals | ₹1.81 lakh cr | ≈ ₹2 lakh |
| FY25 | ~91% | ₹1.06 lakh cr (+41% YoY) | — |
| FY26 | 87.7% | ₹91,685 cr | ₹1.17 lakh (**rising despite fewer traders**) |

Participation fell (active traders −20% in FY26); loser share is basically invariant. ~92% of individual losses come from options; **97% of individuals are primarily/exclusively option buyers**; option **sellers were the only positive-median cohort** (FY26). 96–97% of FPI/prop profits came from algo entities; FY26 counterparty books: prop +₹44k cr, FPI +₹14k cr vs individuals −₹72k cr gross − ~₹25k cr **transaction costs**. Loss rates scale down with wealth: 93% (no equity holdings) → 58% (>₹10 cr).

**Implications for advice phrasing & risk defaults (mandatory):**
- Every alert and dashboard shows **cost-inclusive P&L and "ticks to breakeven"** alongside the setup. Never quote gross moves.
- Bot promises a **risk-controlled process, never returns**; default phrasing must reflect that an average signal-follower's expectancy is plausibly negative after ~₹25k cr/yr of market-wide friction, and that buying-side scalping fights the highest-mortality strategy in the market.
- Bandwagon: 96–97% of counterparty profit is algo-run — user is competing against institutional algos with a two-step (alert → human) latency disadvantage. Say so in onboarding.
- Defaults: hard **daily kill-switch** (e.g. close at ± daily-loss budget), max 1–2% NAV per alert, mandatory funded buffer (upfront premium collection).

**Capital floor (honesty):**
- Realistic floor ≈ **₹10–15 lakh** trading capital for selling/hedged flows: 1-lot short needs ~₹1.5–1.7L margin (₹1.7L on expiry Tue) → 2–4 concurrent positions + 30–40% free buffer ⇒ ₹8–12L; premium-buying scalping needs ≥₹3–5L to survive the variance of 75-unit lots.
- **Do not market to sub-₹3 lakh users** — SEBI data: sub-₹1L-portfolio traders are the ~93%-loser cohort; low-income traders (<₹5L) are >half of aggregate losses (~₹50,000 cr).
- Short-side capital bar: option selling at ₹1.65–1.7L/lot expiry margin is out of reach for tiny accounts — but buying-side is the losing-side cohort; a ₹10–15L floor is the honest minimum for the seller/theta-side flows SEBI data favors.

**Day/time cautions (merged):**
- **Tuesday = NIFTY expiry**: wider opening 15-min range; mid-session dead zone ~12:30–14:00; gamma resolution into 15:30; India VIX typically **falls 3–5%** intraday; a **rising VIX after 13:00 = warning**; ~75% of ATM premium gone by ~14:00 (OTM ~89% on range days) → late entries decay even when directionally right.
- Tuesday-ready defaults: prefer **early-window momentum** entries, **flat by 14:45** (also the start of SEBI's mandatory snapshot window 14:45–15:30 — expect positioning unwinds and expiry-afternoon margin-shock flow from calendar-spread deleveraging), **halve size when VIX > 16**.
- Recalibrate all day-of-week logic: fresh weekly risk starts **Wednesday**; **Monday carries overnight-to-expiry gap risk** (Sat/Sun + Mon only 1 day before expiry).
- Ops reality (from R11, kept brief — full detail belongs to the infra broker filter): daily OAuth re-auth pre-open (tokens die 3:30 AM IST), WS stall watchdog + re-resubscribe ("works after restart, dead next morning"), never poll full option-chain REST (1 call/3 s; use quotes/WS per strike), stay <10 orders/s.

## Demoted/dropped + reasons

- **Trader anecdotes (Thakre ₹2.16 cr, Karthik Raj kill-switch, Jegan, Jain)** — B-tier press, survivorship-biased, not replicable evidence. Kept only as qualitative corroboration of three design defaults: tiny deployed capital vs net worth, hard daily kill-switch, execution discipline > indicators. Not used in any quantitative claim.
- **Expiry-day blog quantification (NiftyDesk, MarketNetra, Intraday Lab decay stats)** — B-tier self-published backtests without methodology disclosure; directionally consistent with SEBI microstructure changes → kept as *hypotheses* (the 75%-by-2PM decay, VIX >16 halving rule) to be re-estimated in our own shadow data, never hard-coded as truth.
- **Upstox API reliability/rate-limit detail (R11 S14–S20)** — real and decision-relevant but **out of scope for costs/realism**; handed to the broker-infra filter; only one-line cautions retained above.
- **Practitioner Kelly explainers (R10 S21)** — B-tier blogs, but the ¼–½ Kelly + 1–2% NAV cap is standard institutional practice (MacLean-Thorp-Ziemba lineage); kept with practitioner provenance noted.
- **DSR/walk-forward/purged-K-fold explainers (R10 S3, S4, S9–S12)** — explainers demoted; retention rests on the peer-reviewed/primary items (Bailey–López de Prado DSR/False-Strategy math; López de Prado AFML ch.7/12 purging/embargo/CPCV). Kept the formulas and gates, dropped blog URLs.
- **dropped:** nothing contradicted required outright deletion — the STT history "contradiction" was vignettes of a true 3-step rate path; the ₹35.03/₹35.53 txn discrepancy is resolved in the constants table; the SEBI 93%/91%/87.7% figures are three successive study vintages, not conflicting claims.

**Open verification items:** (1) locate the intermediate NSE circular moving txn ₹35.03→₹35.53/lakh (immaterial, cosmetic); (2) replace quoted-spread slippage medians with our own realized-fill data from the pilot; (3) decide the sizing floor (1-lot at ~87 bps explicit vs ≥5 lots at ~30 bps) — all reverify on build day.
