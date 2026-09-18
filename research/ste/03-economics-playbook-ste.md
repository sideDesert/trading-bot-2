# 03 — Economics, Realism and Operating Playbook (STE)

## Terms and abbreviations

- **engine** — the deterministic Python process. It computes all numbers, including position size.
- **Evidence tiers:** A = peer-reviewed or regulator-grade. B = corroborated preprint / industry.
  C = blog or anecdote.
- **STT** — Securities Transaction Tax. **GST** — Goods and Services Tax (18%). **SEBI** — the Indian
  securities regulator. **NSE / BSE** — the exchanges. **ELM** — extreme loss margin.
- **NIFTY / SENSEX / BANKNIFTY / FINNIFTY / MIDCPNIFTY** — index names. **IST** — India Standard Time.
- **ATM / ITM / OTM** — at / in / out of the money. **FutEq** — futures-equivalent exposure.
- **bps** — basis points (1 bp = 0.01%). **L / lakh, cr / crore** — Indian number units (₹1L = ₹100,000; ₹1 cr = ₹10,000,000). ₹ = INR.
- **LLM** — large language model. **VIX / India VIX** — volatility index. **EM** — expected move.
- **ORB** — opening-range breakout. **VWAP** — volume-weighted average price. **ATR** — average true range.
- **MAE / MFE** — maximum adverse / favorable excursion of a trade. **p85–p90** — percentiles.
- **DSR** — deflated Sharpe ratio. **CPCV** — combinatorial purged cross-validation. **CV** — cross-validation.
- **IS / OOS** — in-sample / out-of-sample. **Sharpe** — return per unit of volatility.
- **Kelly** — the Kelly criterion for position size. **NAV** — net asset value (account value).
- **SLIP** — spread/slippage cost. **OAuth** — the broker login flow. **WS / wss** — WebSocket feed.
- **NO_TRADE day** — a session where the bot advises no trades at all.

This document combines F6 (filtered R10 + R11). It answers three questions: what does this cost, what
is realistically achievable, and how do we run the play honestly. All numbers carry through exactly
from the sources. Every 2026 regulatory fact is **config-driven, never hard-coded**. Re-verify every
such fact **on build day**. (STT alone has hiked twice in 18 months.)

---

## 1. Regulatory constants 2026 — authoritative table

| Item | Value (authoritative) | Source | Reverify-by |
|---|---|---|---|
| STT, option **sale**, on premium | **0.15%** (path: 0.0625% → 0.1% on 1-Oct-2024 [Finance (No.2) Act 2024] → **0.15% on 1-Apr-2026** [Finance Act 2026]; all three steps true) | BSE notice 20260331-7; Zerodha bulletin 445377; NSE circular FATAX73524; CNBC-TV18 | **Build day** (rate drifted twice in 18 mo) |
| STT, option exercise | 0.15% of intrinsic (buyer pays; was 0.125%) | Same as above | Build day |
| STT, futures sale | 0.05% (context only; the bot trades options) | Same as above | Build day |
| Brokerage | Flat **₹20 per executed order**, each side; assume one order per leg | Zerodha charges page (live) | Build day |
| NSE transaction charge, equity options | **₹35.53/lakh of premium per side = 0.03553%** (NSE circular FA64232 set ₹35.03/lakh Oct-2024; the live broker pass-through of ₹35.53 wins as the operative rate; the difference is <₹0.04/side/lot — immaterial) | Zerodha live tariff | Build day |
| GST | **18% on (brokerage + exchange txn + SEBI fee)** | Zerodha | Build day |
| SEBI fee | ₹10/crore of turnover (0.0001%), each side | Zerodha | Build day |
| Stamp duty | 0.003% of buy-side premium | Zerodha | Build day |
| NIFTY lot size | **75 units** (25→75 for contracts from 20-Nov-2024; min contract ₹15–20L) | SEBI/HO/MRD/TPD-1/P/CIR/2024/132; NSE FAOP64625 | Build day |
| 1 lot notional / point risk | ₹15–18L notional; **₹75 per 1 index point** (100-pt adverse = ₹7,500) | Derived from lot=75 | Static |
| Tick | ₹0.05 ⇒ **₹3.75 per tick per lot** | NSE contract spec | Static |
| Expiry day | **Tuesday** for ALL NSE expiries (Thu→Tue for contracts expiring on/after 1-Sep-2025; first Tuesday weekly = 2-Sep-2025). BSE/SENSEX = Thursday | NSE FAOP68747 (primary; resolves the R10 open question) | Build day (the regime moved twice since 2024) |
| Weekly contracts | NIFTY only on NSE; SENSEX only on BSE. BANKNIFTY/FINNIFTY/MIDCPNIFTY weeklies died in Nov-2024 | SEBI 2024/132 | Build day |
| Upfront option premium collection | Since 1-Feb-2025 — the full premium is debited at order; no collateral-timing tricks; a funded buffer is mandatory | SEBI 2024/132 | Build day |
| Expiry-day margins | +2% ELM on short options on expiry day (from 20-Nov-2024); no calendar-spread margin benefit on the expiring leg (from 1-Feb-2025); short-side expiry margin ≈ **₹1.65–1.7L/lot** vs ~₹1.5L normal | SEBI 2024/132 (₹1.65–1.7L figure is a B-tier ballpark) | Build day |
| Intraday index FutEq limits | From 1-Oct-2025: NET ₹5,000 cr, GROSS ₹10,000 cr/side per entity per index; ≥4 random snapshots (one mandatory **14:45–15:30**); expiry-day ASD penalties from 6-Dec-2025 | SEBI/HO/MRD/TPD-1/P/CIR/2025/122 | Build day |
| Retail order-rate ceiling | **<10 orders/sec** — above this, you enter exchange algo-registration territory | SEBI-NEST practice (B-tier) | Build day |
| Empirical round-trip baseline | **59.1 bps of premium median**: 28.4 bps statutory+brokerage + 30.7 bps spread (842,350 contract-minutes, NIFTY/BANKNIFTY, 27 sessions, 461 contracts) | alphabench (empirical, tier-A) | Re-baseline with own fill data in the pilot |

---

## 2. The cost machine

### 2.1 Parameterized round-trip equation

Definitions: Pe = entry premium, Px = exit premium (₹/unit), L = lots, units = 75L, one order per leg.

```
C(L, Pe, Px) = 40                                          # brokerage 2×₹20
  + 75·L · [ 0.0015·Px          +  # STT sell side
             0.0003553·(Pe+Px)  +  # NSE txn, both sides
             0.000001·(Pe+Px)   +  # SEBI ₹10/cr
             0.00003·Pe        ] + # stamp, buy side
  + 0.18 · ( 40 + 75·L · 0.0003563·(Pe+Px) )   # GST on (brk + txn + SEBI)
  + SLIP                                                   # spread/slippage
SLIP ≈ 75·L · max(half quoted spread, 1 tick) · 2 legs
     ≈ 75·L · 0.00307·((Pe+Px)/2)   # alphabench median: 30.7 bps ≈ 52% of the bill
```
Per-unit cost = C / (75L); **breakeven ticks = per-unit cost / 0.05**.

### 2.2 Worked examples — zero-gross round trip (Pe = Px = P), 1 and 5 lots

| Premium | Measure | **1 lot** | **5 lots** |
|---|---|---|---|
| ₹40 | Explicit ₹ | ₹54.31 | ₹82.76 (₹16.55/lot) |
| | All-in ₹ (incl. slippage) | ₹63.52 | ₹128.81 (₹25.76/lot) |
| | Per unit / ticks / % of premium | ₹0.724 · **14.5 ticks** · 181 bps explicit | ₹0.221 · **4.4 ticks** · 55 bps |
| | All-in per unit / ticks / % | ₹0.847 · **16.9 ticks** · 212 bps | ₹0.344 · **6.9 ticks** · 86 bps |
| **₹100 (ATM weekly anchor)** | Explicit ₹ | **₹64.98** | **₹136.11 (₹27.22/lot)** |
| | All-in ₹ | ≈₹88–95 | ≈₹251 (₹50/lot) |
| | Explicit per unit / ticks / % | **₹0.87 · 17.3 ticks · 87 bps (0.87%)** | ₹0.363 · 7.3 ticks · 36 bps (0.36%) |
| | All-in per unit / ticks / % | **₹1.18–1.25 · 24–25 ticks · 1.2–1.3%** | ₹0.67 · 13–14 ticks · 0.67% |
| ₹200 | Explicit ₹ | ₹82.76 | ₹225.02 (₹45.00/lot) |
| | All-in ₹ | ₹128.81 | ₹455.27 (₹91.05/lot) |
| | Explicit per unit / ticks / % | ₹1.104 · **22.1 ticks** · 55 bps | ₹0.600 · **12.0 ticks** · 30 bps |
| | All-in per unit / ticks / % | ₹1.718 · **34.4 ticks** · 86 bps | ₹1.214 · **24.3 ticks** · 61 bps |

Component detail at the anchor case (L=1, P=₹100, round trip): brokerage ₹40.00 · STT ₹11.25 ·
NSE txn ₹5.33 · SEBI ₹0.02 · stamp ₹0.23 · GST ₹8.16 ⇒ explicit **₹64.98/lot**; + slippage ≈ ₹23/lot
⇒ **all-in ≈ ₹88–95/lot**.

**Sensitivities:** exiting at Px=₹80 cuts STT to ₹9.0 (−₹2.3); at ₹130, STT is ₹14.6. Brokerage and
GST dominate, and they are fixed. The toll barely cares how the trade went.

### 2.3 Breakeven math and the scaling law

- **Index breakeven:** with ATM delta ≈ 0.5, NIFTY must move ≈ **2.5 points (1 lot) / 1.4 points
  (5 lots)** in your favour just to offset friction — before any alpha.
- **Flat brokerage dominates small size:** ~43 bps on a ₹25k position vs ~25 bps at ₹3L (alphabench).
  Explicit cost per lot falls from **87 bps (1 lot) to ~30 bps (10 lots)**. The ₹40 toll amortizes.
- **Corollary 1 — minimum viable thesis size:** set a **sizing floor of ≥5 lots per alert** (explicit
  36 bps at ₹100 premium). Otherwise you accept a 2× cost drag. Single-lot scalping is *structurally
  the most expensive way to trade*.
- **Corollary 2 — hold horizon:** costs are a fixed toll. Edge must scale with hold time. Breakeven =
  **23.4% of a typical 15-min move, but only 4.7% of a full-session move**. Sub-15-min scalps are
  structurally marginal. **Default horizon: 30 min–2 h** (breakeven capture 8–17%).
- **Corollary 3 — minimum-edge alert gate:** fire an alert only when expected MFE (signal forecast) ≥
  **3× all-in cost**. At 1 lot at ₹100 premium, that is ≥ ~₹3.6–4/unit ≈ ≥75–80 ticks of expected move.
- **The 23% verdict in one line:** a 1-lot 15-minute scalper must capture ~a quarter of a typical
  15-minute move on every single trade, just to stand still. This is why single-lot scalping is
  nearly unwinnable.

---

## 3. Expectancy honesty

### 3.1 SEBI loss base rates (primary studies, successive vintages — all are true at once)

| Vintage | Losers | Aggregate net loss | Avg loss/trader |
|---|---|---|---|
| FY22–24 | 92.8% ("93%") of 1.13 cr individuals | ₹1.81 lakh cr | ≈ ₹2 lakh |
| FY25 | ~91% | ₹1.06 lakh cr (+41% YoY) | — |
| FY26 | 87.7% | ₹91,685 cr | **₹1.17 lakh (rising despite fewer traders)** |

Participation fell (active traders −20% in FY26). **The loser share is basically invariant.** Loss
rates scale down with wealth: from 93% (no equity holdings) to 58% (>₹10 cr portfolios).

### 3.2 Who makes the money

- ~92% of individual losses come from **options**. **97% of individuals are primarily or exclusively
  option buyers.**
- Option **sellers were the only positive-median cohort** (FY26).
- FY26 counterparty books: prop **+₹44,000 cr**, FPI **+₹14,000 cr**, vs individuals **−₹72,000 cr**
  gross, plus **~₹25,000 cr in transaction costs**.
- **96–97% of FPI/prop profits came from algo entities.**

### 3.3 What this means for a BUYER-side advisory bot

We are building an advisory bot for **buying-side intraday options**. This is the single
highest-mortality strategy in the market. The user executes retail-late against institutional algos
that hold 96–97% of the winning counterparty books. The market extracts ~₹25,000 cr/yr of friction
from the retail side. Realistic framing:

- The **average signal-follower's expectancy is plausibly negative after costs**, even if the signals
  are directionally decent. The bot sells a **risk-controlled process, never returns**.
- Edge, if any, is thin and capacity-free. Replication evidence on the one surviving retail signal
  family (ORB with filters) shows headline alphas that fail independent replication and decay ~26%
  OOS. Frame the probability-of-edge as *a hypothesis to re-test continuously*, not a property of the
  product.
- **Bandwagon disclosure (mandatory at onboarding):** the user competes against institutional algos
  with a two-step (alert → human) latency disadvantage. Say so.
- **Every alert and dashboard shows cost-inclusive P&L and "ticks to breakeven."** Never quote gross
  moves.

---

## 4. Capital and risk defaults

- **Capital floor (honesty):** ≈ **₹10–15 lakh** for selling/hedged flows (1-lot short needs
  ~₹1.5–1.7L margin ⇒ 2–4 concurrent positions + 30–40% free buffer ⇒ ₹8–12L). **≥₹3–5L** minimum for
  buying-side scalping, to survive 75-unit-lot variance. **Do not market to sub-₹3 lakh users.**
  Sub-₹1L-portfolio traders are the ~93%-loser cohort. Sub-₹5L-income traders carry more than half of
  aggregate losses (~₹50,000 cr).
- **Per-trade size (engine-computed, never LLM-computed):**
  `size = min(¼–½ Kelly from trailing ≥100-trade stats, 1–2% NAV risk cap, margin cap)`. Never suggest
  full Kelly. Full Kelly implies 30–50% drawdowns, and it is catastrophically wrong when p is
  mis-estimated (a 55% win rate over 100 trades has a ±10% CI). ½-Kelly ≈ 75% of growth at ~half the
  variance; ¼-Kelly ≈ 56% at ~a quarter of the variance.
- **Daily kill-switch (hard):** close at ± the daily-loss budget. Enforce in code. No override path
  exists in the alert flow.
- **Funded buffer mandatory:** upfront premium collection (since 1-Feb-2025) debits the full premium
  at order. No timing tricks. Multi-order bursts need headroom.

### 4.1 MAE/MFE protocol — exact procedure (mandatory in sim AND in the live shadow log)

1. **Instrument excursions.** Per trade, log entry price and time, plus the running min/max of the
   option **mid price every tick** while open, plus the recorded bid/ask at entry/exit.
   MAE = entry − min(adverse-side); MFE = max(favourable-side) − entry.
2. **Normalize to R.** MAE_R = MAE / planned initial risk per unit. Do the same for MFE_R (use ATR
   units if risk varies). This makes trades comparable across regimes.
3. **Accumulate ≥100 trades per setup type**, bucketed by regime (trend vs chop; expiry-Tuesday vs
   non-expiry). 50+ is the absolute minimum. Below that, percentiles are noise.
4. **Stop calibration — winners only.** Filter to winning trades. Bucket MAE_R in 0.2R bins. Proposed
   stop = **p85–p90 of the winners' MAE** (sanity shortcut: 1.1–1.2× the mean winners' MAE). A
   shallower stop clips real winners. A deeper stop pays for losers without saving winners.
5. **Target calibration.** Candidate target = **the winners' median MFE**. Capture ratio = realized
   avg win / avg winners' MFE. If the ratio is < **0.70**, the exit donates profit: widen the target
   or trail it. Every alert carries: stop = winners' p90 MAE, target = winners' median MFE, recomputed
   weekly from live logs.
6. **Losers' check.** If losers show small MAE and then explode past the stop, the problem is
   **entries**, not stops. Tighten the entry filter. Do not widen stops.
7. **Anti-overfit.** Re-derive percentiles on a rolling window (last ~3 months / 200 trades).
   **Refuse stop changes < 0.1R.** Never calibrate stops on the sample you used to select the signal.

### 4.2 Anti-overfit evaluation gates (apply to any signal/backtest)

- **DSR > 0.95 given N trials attempted**, on the stitched out-of-sample curve. For N skill-less
  trials, E[max Sharpe] ≈ (1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne)) ≤ √(2 ln N): N=10 junk trials already imply
  an expected IS Sharpe of 1.57; N=1,000 ⇒ ~3.26.
- **Trials diary:** log every configuration ever tested. Undisclosed search intensity is the most
  corrosive overfit.
- **Walk-forward:** stitched-OOS with an **OOS/IS decay ratio ≥ 0.5** and stable parameters across
  windows (anchored ≈ rolling). Parameterized drift (a lookback that jumps 20→60→30) = noise.
- **Purged + embargoed K-fold (or CPCV)** for any ML component. Financial labels span forward windows.
  Standard CV leaks.
- Backtests must use the §2.1 hard cost model with per-leg slippage = max(half quoted spread, 1 tick).
  **Never simulate exits at mid/LTP.**

---

## 5. The operating playbook

### 5.1 Session clock and blocked windows

| Window | Rule | Basis |
|---|---|---|
| Pre-open (~8:30–9:05) | Do the daily OAuth re-auth (tokens die at 3:30 AM IST); connect WS and arm the stall watchdog; run the charge-table config check; check India VIX vs prev close; set the event-calendar flag; verify the funded buffer | R11 ops reality; charges are config-driven |
| **9:05 start gate** | Go/no-go: feed healthy, VIX regime tagged, capital/margin check passed. On any fail, the bot announces a NO_TRADE day | Process default |
| **9:15–9:45 rule** | **No buy advisories in the first 15–30 min** (suppress fresh longs 9:15–9:45 hardest); Monday open = **full block** in this window | A-tier: Monday India VIX +2.35–2.44% at open; U-shaped vol is highest in the first 30 min |
| **Monday-open rule** | Monday carries overnight-to-expiry gap risk (Sat/Sun + Monday sits 1 day before the Tuesday expiry). Treat Monday open as a blocked window. Fresh weekly risk starts **Wednesday** | Expiry moved to Tuesday |
| 9:45–11:15 | Prime momentum/ORB window (ORB is eligible 9:15–11:15 once the suppress window expires); the LLM gets the first-30-min momentum state | Session-clock tags |
| **Midday dead zone** | Inhibit new directional buys **~12:30–14:00 on expiry days (11:30–13:30 on non-event days)** | Desk practice + A-tier U-shape lows |
| **Expiry 13:15 cutoff** | Tuesday: **no new longs after ~13:15–13:30**, unless the opening-straddle EM is already broken AND the tape shows strong momentum | Corroborating desks + 1/√T decay |
| 14:00–14:45 | Rising VIX after 13:00 = warning; ~75% of ATM premium is gone by ~14:00 (89% for 1-strike OTM on range days) — late entries decay even when directionally right | Expiry studies (B-tier hypotheses; re-estimate in shadow data) |
| **Flat by 14:45 (Tuesday)** | 14:45 starts SEBI's mandatory snapshot window (14:45–15:30). Expect positioning unwinds and margin-shock flow from calendar-spread deleveraging | SEBI 2025/122 + expiry ops |
| Any window, VIX > 16 | **Halve size** | Expiry-day hypothesis (B-tier) |

### 5.2 Tuesday-expiry session plan (NIFTY weekly)

- Regime facts: expiry-day range **+25–30% vs non-expiry (~180–220 pts vs ~140–170)**; direction is a
  coin-flip (~52/48); **~68% of expiries finish inside the opening straddle**; the **first 45 min +
  last 90 min ≈ 60% of the day's range**; India VIX typically **falls 3–5%** intraday.
- **Plan:**
  1. No fresh longs 9:15–9:45. The wider opening 15-min range whipsaws entries.
  2. Primary entries = **early-window momentum 9:45–11:15**, sized to the larger expected range
     (wider stops in R terms, same % NAV).
  3. Observe the midday dead-zone block.
  4. Hard new-long cutoff at 13:15–13:30.
  5. Flat by 14:45.
  6. Treat final-hour mean reversion toward high-OI strikes as a veto on breakout-chase entries, not
     as a fade signal.
- **ORB filter integration (per the features doc):** ORB is the **sole surviving signal family**, and
  only with mandatory filters. Skip if the opening-range width < 20th percentile of the 20d ATR
  (a contraction proxy). Skip non-"in-play" days (low rel-volume, no news/expiry — note that a Tuesday
  expiry itself counts as an in-play event). **No tight stops** (≥ OR width, or trail the OR extreme).
  Require relative-volume ≥1.5× the same-time 20d median. Impose the §2.3 cost floor (gross edge ≥
  2–3× all-in round trip incl. STT). Run a rolling-decay monitor (expect ~26% OOS decay). Naive ORB
  is a coin flip; the filter IS the edge.
- **Liquidity gate, all days:** alert only when the quoted spread ≤ 2% of mid premium and the strike
  is within ±3% of spot.

### 5.3 When the bot must tell the user NOT to trade

The NO_TRADE advisory is a first-class output. Fire it when any of these holds:

1. Any start-gate check fails.
2. The time is inside any blocked-window rule above.
3. Expected MFE < 3× all-in cost.
4. Quoted spread > 2% of mid, or the strike is beyond ±3% of spot.
5. VIX > 16 (halve size, or veto on expiry afternoons).
6. VIX is rising after 13:00 on Tuesday.
7. The daily loss budget is hit (the kill-switch is already flat).
8. The MAE/MFE capture ratio degrades below 0.70 on the rolling window (the exit logic is donating
   profit — pause and recalibrate).
9. DSR or forward shadow stats fall below the §6 thresholds.
10. The signal's rolling OOS decay breaches the monitor limits.

Silence is also a position.

---

## 6. Go/No-Go criteria — graduation ladder and kill switches

**Stage 0 → Stage 1 (shadow-log mode entry):** the build passes the §1 config verification; the
forward-only shadow architecture is live. Log every candidate alert at emission with: the entry quote
(bid/ask, never mid/LTP fills), the tick-level MAE/MFE mid path, a hypothetical fill at quote plus a
realized-spread model, the full §2.1 cost equation, and the signal snapshot. Backtest prerequisites
met: hard cost model, no mid/LTP exits, trials diary started.

**Stage 1 → Stage 2 (user-facing alerting). ALL must hold:**

1. **≥100 forward shadow trades** per setup type (needed anyway for MAE/MFE percentiles).
2. **DSR > 0.95 given N trials attempted** on the stitched OOS curve.
3. Walk-forward stitched-OOS decay ratio ≥ 0.5 with stable parameters.
4. Purged-embargoed K-fold / CPCV clean for any ML component.
5. Shadow cost-inclusive expectancy > 0 **at the commanded sizing floor (≥5 lots)**, with a
   realized-spread model — not quoted-spread medians.
6. Capture ratio ≥ 0.70 against winners' median MFE.

**Stage 2 → Stage 3 (semi-auto, only if ever):** additionally, ≥200 live alerted trades with user
execution slippage within 1 tick of the shadow-modeled fills; realized cost per lot within +20% of
model; no kill-switch breach in 40 consecutive sessions; a manual approval gate on every order (at
this stage the bot never self-executes without a human ack).

**Kill criteria (immediate rollback to shadow mode, or off):**

1. Cost-inclusive expectancy ≤ 0 over the trailing 100 alerted trades.
2. Capture ratio < 0.50, persisting after one recalibration.
3. Any month where realized costs exceed 150% of model (the spread regime broke).
4. Parameter instability across two consecutive walk-forward windows.
5. A regulatory change that invalidates a §1 constant (e.g., another STT/lot/expiry move) without a
   same-day config patch.
6. Any order-rate or position-limit incident.

---

## 7. Open risks — merged and ranked

1. **No demonstrated buyer-side edge net of costs (highest).** The base rate says 88–93% lose. The
   only positive-median cohort sells. ORB-with-filters is the sole surviving retail signal family, and
   its headline alphas fail independent replication. The entire product rests on shadow-log proof, not
   on published evidence.
2. **Cost regime drift.** STT hiked twice in 18 months (1-Oct-2024, 1-Apr-2026). Rates must be
   config-driven and re-verified on build day. A third hike at scalping horizons directly kills
   marginal setups.
3. **Slippage uncertainty.** The 30.7 bps median spread figure is a quoted-spread median across a
   broad panel, not our achieved fills. ATM NIFTY weekly spreads range ₹0.5–2, and under-₹20 premiums
   run 57 bps. The pilot must re-baseline with realized order-level fills. A structurally wider regime
   breaks the 5-lot economics above.
4. **Sizing-floor tension (decision pending).** 1-lot economics (~87 bps explicit) vs ≥5 lots
   (~30–36 bps). If the alert audience cannot fund 5 lots (₹37.5k premium at ₹100), the product's
   honest addressable user base is ₹5L+ accounts only. This is a market-sizing constraint, and an open
   policy decision.
5. **Expiry-day microstructure constants are B-tier hypotheses.** The 75%-by-14:00 decay, the VIX>16
   half-size rule, and the dead-zone bounds come from self-published backtests. They are directionally
   consistent with SEBI microstructure changes, but re-estimate them in our own shadow data before
   hard-coding.
6. **Two-step latency vs algos.** Alert → human read → human execution adds seconds against
   96–97%-algo counterparties in the same door. There is no fix — only honesty (onboarding disclosure)
   and design (a 30-min–2-h horizon, where latency matters least).
7. **Ops fragility (feed/token).** Daily OAuth re-auth; WS silent stalls ("works after restart, dead
   next morning"); option-chain REST throttling (1 call/3 s); no rate-limit headers (first signal =
   HTTP 429). Handed to the broker-infra workstream. A dead morning = a forced NO_TRADE day.
8. **Cosmetic data debt.** The ₹35.03 → ₹35.53/lakh intermediate NSE circular is not yet located
   (<₹0.04/side/lot impact — immaterial; close on build day).

---

## Provenance and demotion notes

Synthesized from F6 (which merged R10 + R11 through the quality gate). Tier-A/S evidence carries every
quantitative claim in §§1–5: SEBI studies and circulars, NSE/BSE notices, peer-reviewed
DSR/backtest-overfit and purged-CV work, and the 842k-contract-minute alphabench cost panel.
Practitioner narratives (verified scalper interviews, kill-switch anecdotes) inform only the
*defaults* — the hard daily kill-switch, the tiny deployed fraction of net worth, discipline over
indicators. They are cited in no quantitative claim. B-tier expiry-day quantification (the
75%-by-14:00 decay, the VIX>16 sizing rule, the dead-zone bounds) is carried as hypotheses under
§5/§7, pending re-estimation in our own shadow data. No contradiction in the sources required a
deletion. The three "conflicts" found upstream (the 3-step STT rate path, ₹35.03 vs ₹35.53 txn, and
the 93%/91%/87.7% SEBI figures) each resolve as rate history, live-vs-circular tariff, and successive
study vintages.
