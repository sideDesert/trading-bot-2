# 03 — Economics, Realism & Operating Playbook

**Synthesis of F6 (filtered R10 + R11).** The definitive answer to: what does this actually cost, what's realistically achievable, and how do we run the play honestly. All numbers carry through exactly from sources. Every 2026 regulatory fact is **config-driven, never hard-coded**, and must be **re-verified on build day** (STT alone has hiked twice in 18 months).

---

## 1. Regulatory constants 2026 — authoritative table

| Item | Value (authoritative) | Source | Reverify-by |
|---|---|---|---|
| STT, option **sale**, on premium | **0.15%** (path: 0.0625% → 0.1% on 1-Oct-2024 [Finance (No.2) Act 2024] → **0.15% on 1-Apr-2026** [Finance Act 2026]; all three steps true) | BSE notice 20260331-7; Zerodha bulletin 445377; NSE circular FATAX73524; CNBC-TV18 | **Build day** (rate drifted twice in 18 mo) |
| STT, option exercise | 0.15% of intrinsic (buyer pays; was 0.125%) | Same as above | Build day |
| STT, futures sale | 0.05% (context only; bot trades options) | Same as above | Build day |
| Brokerage | Flat **₹20 per executed order**, each side; one order per leg assumed | Zerodha charges page (live) | Build day |
| NSE transaction charge, equity options | **₹35.53/lakh of premium per side = 0.03553%** (NSE circular FA64232 set ₹35.03/lakh Oct-2024; live broker pass-through ₹35.53 wins as operative rate; difference <₹0.04/side/lot — immaterial) | Zerodha live tariff | Build day |
| GST | **18% on (brokerage + exchange txn + SEBI fee)** | Zerodha | Build day |
| SEBI fee | ₹10/crore of turnover (0.0001%), each side | Zerodha | Build day |
| Stamp duty | 0.003% of buy-side premium | Zerodha | Build day |
| NIFTY lot size | **75 units** (25→75 for contracts from 20-Nov-2024; min contract ₹15–20L) | SEBI/HO/MRD/TPD-1/P/CIR/2024/132; NSE FAOP64625 | Build day |
| 1 lot notional / point risk | ₹15–18L notional; **₹75 per 1 index point** (100-pt adverse = ₹7,500) | Derived from lot=75 | Static |
| Tick | ₹0.05 ⇒ **₹3.75 per tick per lot** | NSE contract spec | Static |
| Expiry day | **Tuesday** for ALL NSE expiries (Thu→Tue for contracts expiring on/after 1-Sep-2025; first Tuesday weekly = 2-Sep-2025). BSE/SENSEX = Thursday | NSE FAOP68747 (primary; resolves R10 open question) | Build day (regime moved twice since 2024) |
| Weekly contracts | NIFTY only on NSE; SENSEX only on BSE. BANKNIFTY/FINNIFTY/MIDCPNIFTY weeklies dead since Nov-2024 | SEBI 2024/132 | Build day |
| Upfront option premium collection | Since 1-Feb-2025 — full premium debited at order; no collateral-timing tricks; funded buffer mandatory | SEBI 2024/132 | Build day |
| Expiry-day margins | +2% ELM on short options on expiry day (from 20-Nov-2024); no calendar-spread margin benefit on expiring leg (from 1-Feb-2025); short-side expiry margin ≈ **₹1.65–1.7L/lot** vs ~₹1.5L normal | SEBI 2024/132 (₹1.65–1.7L figure B-tier ballpark) | Build day |
| Intraday index FutEq limits | From 1-Oct-2025: NET ₹5,000 cr, GROSS ₹10,000 cr/side per entity per index; ≥4 random snapshots (one mandatory **14:45–15:30**); expiry-day ASD penalties from 6-Dec-2025 | SEBI/HO/MRD/TPD-1/P/CIR/2025/122 | Build day |
| Retail order-rate ceiling | **<10 orders/sec** — above → exchange algo-registration territory | SEBI-NEST practice (B-tier) | Build day |
| Empirical round-trip baseline | **59.1 bps of premium median**: 28.4 bps statutory+brokerage + 30.7 bps spread (842,350 contract-minutes, NIFTY/BANKNIFTY, 27 sessions, 461 contracts) | alphabench (empirical, tier-A) | Re-baseline with own fill data in pilot |

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

Component detail at the anchor case (L=1, P=₹100, round trip): brokerage ₹40.00 · STT ₹11.25 · NSE txn ₹5.33 · SEBI ₹0.02 · stamp ₹0.23 · GST ₹8.16 ⇒ explicit **₹64.98/lot**; + slippage ≈ ₹23/lot ⇒ **all-in ≈ ₹88–95/lot**.

**Sensitivities:** exiting at Px=₹80 cuts STT to ₹9.0 (−₹2.3); at ₹130 STT is ₹14.6. Brokerage/GST dominate and are fixed — the toll barely cares how the trade went.

### 2.3 Breakeven math and the scaling law

- **Index breakeven:** with ATM delta ≈ 0.5, NIFTY must move ≈ **2.5 points (1 lot) / 1.4 points (5 lots)** in your favour just to offset friction — before any alpha.
- **Flat brokerage dominates small size:** ~43 bps on a ₹25k position vs ~25 bps at ₹3L (alphabench). Explicit cost/lot falls from **87 bps (1 lot) → ~30 bps (10 lots)**; the ₹40 toll amortizes.
- **Corollary 1 — minimum viable thesis size:** **sizing floor ≥ 5 lots per alert** (explicit 36 bps at ₹100 premium), or accept a 2× cost drag. Single-lot scalping is *structurally the most expensive way to trade*.
- **Corollary 2 — hold horizon:** costs are a fixed toll; edge must scale with hold. Breakeven = **23.4% of a typical 15-min move but only 4.7% of a full-session move** ⇒ sub-15-min scalps are structurally marginal; **default horizon 30 min–2 h** (breakeven capture 8–17%).
- **Corollary 3 — minimum-edge alert gate:** fire only when expected MFE (signal forecast) ≥ **3× all-in cost** — at 1 lot at ₹100 premium that is ≥ ~₹3.6–4/unit ≈ ≥75–80 ticks of expected move.
- **The 23% verdict in one line:** a 1-lot 15-minute scalper must capture ~a quarter of a typical 15-minute move, every single trade, just to stand still. That is why single-lot scalping is nearly unwinnable.

---

## 3. Expectancy honesty

### 3.1 SEBI loss base rates (primary studies, successive vintages — all true simultaneously)

| Vintage | Losers | Aggregate net loss | Avg loss/trader |
|---|---|---|---|
| FY22–24 | 92.8% ("93%") of 1.13 cr individuals | ₹1.81 lakh cr | ≈ ₹2 lakh |
| FY25 | ~91% | ₹1.06 lakh cr (+41% YoY) | — |
| FY26 | 87.7% | ₹91,685 cr | **₹1.17 lakh (rising despite fewer traders)** |

Participation fell (active traders −20% in FY26); **loser share is basically invariant**. Loss rates scale down with wealth: 93% (no equity holdings) → 58% (>₹10 cr portfolios).

### 3.2 Who makes the money

- ~92% of individual losses come from **options**; **97% of individuals are primarily/exclusively option buyers**.
- Option **sellers were the only positive-median cohort** (FY26).
- FY26 counterparty books: prop **+₹44,000 cr**, FPI **+₹14,000 cr** vs individuals **−₹72,000 cr** gross + **~₹25,000 cr in transaction costs**.
- **96–97% of FPI/prop profits came from algo entities.**

### 3.3 What this means for a BUYER-side advisory bot

We are building an advisory bot for **buying-side intraday options** — the single highest-mortality strategy in the market, executed retail-late against institutional algos that hold 96–97% of the winning counterparty books, in a market that extracts ~₹25,000 cr/yr of friction from the retail side. Realistic framing:

- The **average signal-follower's expectancy is plausibly negative after costs**, even if the signals are directionally decent. The bot sells a **risk-controlled process, never returns**.
- Edge, if any, is thin and capacity-free: replication evidence on the one surviving retail signal family (ORB with filters) shows headline alphas that fail independent replication and decay ~26% OOS. Frame probability-of-edge as *a hypothesis to be continuously re-tested*, not a property of the product.
- **Bandwagon disclosure (mandatory onboarding):** the user competes against institutional algos with a two-step (alert → human) latency disadvantage. Say so.
- **Every alert and dashboard shows cost-inclusive P&L and "ticks to breakeven."** Never quote gross moves.

---

## 4. Capital & risk defaults

- **Capital floor (honesty):** ≈ **₹10–15 lakh** for selling/hedged flows (1-lot short needs ~₹1.5–1.7L margin ⇒ 2–4 concurrent positions + 30–40% free buffer ⇒ ₹8–12L); **≥₹3–5L** minimum for buying-side scalping to survive 75-unit-lot variance. **Do not market to sub-₹3 lakh users** — sub-₹1L-portfolio traders are the ~93%-loser cohort; sub-₹5L-income traders carry >half of aggregate losses (~₹50,000 cr).
- **Per-trade size (engine-computed, never LLM-computed):** `size = min(¼–½ Kelly from trailing ≥100-trade stats, 1–2% NAV risk cap, margin cap)`. Full Kelly is never suggested: it implies 30–50% drawdowns and is catastrophically wrong under p mis-estimation (a 55% win rate over 100 trades has ±10% CI). ½-Kelly ≈ 75% of growth at ~half variance; ¼-Kelly ≈ 56% at ~quarter variance.
- **Daily kill-switch (hard):** close at ± daily-loss budget; code-enforced, no override path in the alert flow.
- **Funded buffer mandatory:** upfront premium collection (since 1-Feb-2025) debits full premium at order — no timing tricks; multi-order bursts need headroom.

### 4.1 MAE/MFE protocol — exact procedure (mandatory in sim AND live shadow log)

1. **Instrument excursions:** per trade log entry price/time + running min/max of option **mid price every tick** while open, plus recorded bid/ask at entry/exit. MAE = entry − min(adverse-side); MFE = max(favourable-side) − entry.
2. **Normalize to R:** MAE_R = MAE / planned initial risk per unit; MFE_R likewise (ATR units if risk varies), so trades are comparable across regimes.
3. **Accumulate ≥100 trades per setup type**, bucketed by regime (trend vs chop; expiry-Tuesday vs non-expiry). 50+ absolute minimum; below that percentiles are noise.
4. **Stop calibration — winners only:** filter to winning trades, bucket MAE_R in 0.2R bins, proposed stop = **p85–p90 of winners' MAE** (sanity shortcut: 1.1–1.2× mean winners' MAE). Shallower clips real winners; deeper pays for losers without saving winners.
5. **Target calibration:** candidate target = **winners' median MFE**; capture ratio = realized avg win / avg winners' MFE; if < **0.70** the exit donates profit → widen target or trail. Every alert carries: stop = winners' p90 MAE, target = winners' median MFE, recomputed weekly from live logs.
6. **Losers' check:** losers with small MAE that then explode past the stop ⇒ the problem is **entries**, not stops — tighten the entry filter, do not widen stops.
7. **Anti-overfit:** re-derive percentiles on a rolling window (last ~3 months / 200 trades); **refuse stop changes < 0.1R**; never calibrate stops on the sample used to select the signal.

### 4.2 Anti-overfit evaluation gates (apply to any signal/backtest)

- **DSR > 0.95 given N trials attempted**, on the stitched out-of-sample curve. For N skill-less trials E[max Sharpe] ≈ (1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne)) ≤ √(2 ln N): N=10 junk trials already imply expected IS Sharpe 1.57; N=1,000 ⇒ ~3.26.
- **Trials diary:** log every configuration ever tested. Undisclosed search intensity is the most corrosive overfit.
- Walk-forward: stitched-OOS with **OOS/IS decay ratio ≥ 0.5**, stable parameters across windows (anchored ≈ rolling); parameterized drift (lookback jumping 20→60→30) = noise.
- **Purged + embargoed K-fold (or CPCV)** for any ML component — financial labels span forward windows; standard CV leaks.
- Backtests use the §2.1 hard cost model with per-leg slippage = max(half quoted spread, 1 tick); **exits never simulated at mid/LTP**.

---

## 5. The operating playbook

### 5.1 Session clock and blocked windows

| Window | Rule | Basis |
|---|---|---|
| Pre-open (~8:30–9:05) | Daily OAuth re-auth (tokens die 3:30 AM IST); WS connect + stall watchdog armed; charge table config-check; India VIX vs prev close; event calendar flag; verify funded buffer | R11 ops reality; charges config-driven |
| **9:05 start gate** | Go/no-go: feed healthy, VIX regime tagged, capital/margin check passed. Any fail ⇒ bot announces NO_TRADE day | Process default |
| **9:15–9:45 rule** | **No buy advisories in the first 15–30 min** (suppress fresh longs 9:15–9:45 hardest); Monday open = **full block** at this window | A-tier: Monday India VIX +2.35–2.44% at open; U-shaped vol highest first 30 min |
| **Monday-open rule** | Monday carries overnight-to-expiry gap risk (Sat/Sun + Mon sits 1 day before Tuesday expiry) — treat Monday open as a blocked window; fresh weekly risk starts **Wednesday** | Expiry moved to Tuesday |
| 9:45–11:15 | Prime momentum/ORB window (ORB eligible 9:15–11:15 once the suppress window expires); LLM gets first-30-min momentum state | Session-clock tags |
| **Midday dead zone** | Inhibit new directional buys **~12:30–14:00 on expiry days (11:30–13:30 non-event days)** | Desk practice + A-tier U-shape lows |
| **Expiry 13:15 cutoff** | Tuesday: **no new longs after ~13:15–13:30** unless opening-straddle EM already broken AND strong momentum tape | Corroborating desks + 1/√T decay |
| 14:00–14:45 | Rising VIX after 13:00 = warning; ~75% of ATM premium gone by ~14:00 (89% for 1-strike OTM on range days) — late entries decay even when directionally right | Expiry studies (B-tier hypotheses; re-estimate in shadow data) |
| **Flat by 14:45 (Tuesday)** | 14:45 starts SEBI's mandatory snapshot window (14:45–15:30) → expect positioning unwinds and margin-shock flow from calendar-spread deleveraging | SEBI 2025/122 + expiry ops |
| Any window, VIX > 16 | **Halve size** | Expiry-day hypothesis (B-tier) |

### 5.2 Tuesday-expiry session plan (NIFTY weekly)

- Regime facts: expiry-day range **+25–30% vs non-expiry (~180–220 pts vs ~140–170)**; direction coin-flip (~52/48); **~68% of expiries finish inside the opening straddle**; **first 45 min + last 90 min ≈ 60% of the day's range**; India VIX typically **falls 3–5%** intraday.
- **Plan:** (a) no fresh longs 9:15–9:45 — wider opening 15-min range whipsaws entries; (b) primary entries = **early-window momentum 9:45–11:15**, sized to the larger expected range (wider stops in R terms, same % NAV); (c) observe the midday dead zone block; (d) hard new-long cutoff 13:15–13:30; (e) flat by 14:45; (f) treat final-hour mean-reversion toward high-OI strikes as a veto on breakout-chase entries, not a fade signal.
- **ORB filter integration (per features doc):** ORB is the **sole surviving signal family** — but only with mandatory filters: skip if the opening-range width < 20th percentile of 20d ATR (contraction proxy); skip non-"in-play" days (low rel-volume, no news/expiry — note Tuesday expiry itself counts as an in-play event); **no tight stops** (≥ OR width or trail OR extreme); relative-volume ≥1.5× same-time 20d median confirmation; impose the §2.3 cost floor (gross edge ≥ 2–3× all-in round trip incl. STT); run a rolling-decay monitor (expect ~26% OOS decay). Naive ORB = coin flip; the filter IS the edge.
- Liquidity gate all days: alert only when quoted spread ≤ 2% of mid premium and strike within ±3% of spot.

### 5.3 When the bot must tell the user NOT to trade

The NO_TRADE advisory is a first-class output. Fire it when: any start-gate check fails; within any blocked-window rule above; expected MFE < 3× all-in cost; quoted spread > 2% of mid or strike beyond ±3% of spot; VIX > 16 (halve, or veto on expiry afternoons); rising VIX after 13:00 on Tuesday; daily loss budget hit (kill-switch already flat); MAE/MFE capture ratio degraded < 0.70 on rolling window (exit logic donating profit — pause and recalibrate); DSR/forward shadow stats fall below the §6 thresholds; or the signal's rolling OOS decay breaches monitor limits. Silence is also a position.

---

## 6. Go/No-Go criteria — graduation ladder and kill switches

**Stage 0 → Stage 1 (shadow-log mode entry):** build passes §1 config verification; forward-only shadow architecture live — every candidate alert logged at emission with entry quote (bid/ask, never mid/LTP fills), tick-level MAE/MFE mid path, hypothetical fill at quote + realized-spread model, full §2.1 cost equation, signal snapshot. Backtest prerequisites met: hard cost model, no mid/LTP exits, trials diary started.

**Stage 1 → Stage 2 (user-facing alerting), ALL must hold:**
1. **≥100 forward shadow trades** per setup type (needed anyway for MAE/MFE percentiles);
2. **DSR > 0.95 given N trials attempted** on the stitched OOS curve;
3. Walk-forward stitched-OOS decay ratio ≥ 0.5 with stable parameters;
4. Purged-embargoed K-fold / CPCV clean for any ML component;
5. Shadow cost-inclusive expectancy > 0 **at the commanded sizing floor (≥5 lots)** with realized-spread model, not quoted-spread medians;
6. Capture ratio ≥ 0.70 against winners' median MFE.

**Stage 2 → Stage 3 (semi-auto, only if ever):** additionally ≥200 live alerted trades with user execution slippage within 1 tick of shadow-modeled fills; realized cost per lot within +20% of model; no kill-switch breach in 40 consecutive sessions; manual approval gate on every order (the bot never self-executes without a human ack at this stage).

**Kill criteria (immediate rollback to shadow or off):** cost-inclusive expectancy ≤ 0 over trailing 100 alerted trades; capture ratio < 0.50 persisting after one recalibration; any month where realized costs exceed 150% of model (spread regime broke); parameter instability across two consecutive walk-forward windows; regulatory change invalidating a §1 constant (e.g., another STT/lot/expiry move) without a same-day config patch; any order-rate or position-limit incident.

---

## 7. Open risks — merged and ranked

1. **No demonstrated buyer-side edge net of costs (highest).** Base rate says 88–93% lose; the only positive-median cohort sells; ORB-with-filters is the sole surviving retail signal family and its headline alphas fail independent replication. The entire product rests on shadow-log proof, not on published evidence.
2. **Cost regime drift.** STT hiked twice in 18 months (1-Oct-2024, 1-Apr-2026); rates must be config-driven and re-verified on build day. A third hike at scalping horizons directly kills marginal setups.
3. **Slippage uncertainty.** The 30.7 bps median spread figure is quoted-spread medians across a broad panel, not our achieved fills; ATM NIFTY weekly spreads range ₹0.5–2 and under-₹20 premiums run 57 bps. Pilot must re-baseline with realized order-level fills — a structurally wider regime breaks the L5 economics above.
4. **Sizing-floor tension (decision pending).** 1-lot economics (~87 bps explicit) vs ≥5-lot (~30–36 bps): if the alert audience can't fund 5 lots (₹37.5k premium at ₹100), the product's honest addressable user base is ₹5L+ accounts only — a market-sizing constraint, and an open policy decision.
5. **Expiry-day microstructure constants are B-tier hypotheses.** The 75%-by-14:00 decay, VIX>16 half-size rule, and dead-zone bounds come from self-published backtests; directionally consistent with SEBI microstructure changes but must be re-estimated in our own shadow data before hard-coding.
6. **Two-step latency vs algos.** Alert → human read → human execution adds seconds against 96–97%-algo counterparties in the same door; no fix, only honesty (onboarding disclosure) and design (30-min–2-h horizon where latency matters least).
7. **Ops fragility (feed/token).** Daily OAuth re-auth, WS silent stalls ("works after restart, dead next morning"), option-chain REST throttling (1 call/3 s), no rate-limit headers (first signal = HTTP 429). Handed to the broker-infra workstream; a dead morning = forced NO_TRADE day.
8. **Cosmetic data debt.** ₹35.03 → ₹35.53/lakh intermediate NSE circular not yet located (<₹0.04/side/lot impact — immaterial, close on build day).

---

## Provenance & demotion notes

Synthesized from F6 (which merged R10 + R11 through the quality gate). Tier-A/S evidence carries every quantitative claim in §§1–5: SEBI studies and circulars, NSE/BSE notices, peer-reviewed DSR/backtest-overfit and purged-CV work, the 842k-contract-minute alphabench cost panel. Practitioner narratives (verified scalper interviews, kill-switch anecdotes) inform only the *defaults* — hard daily kill-switch, tiny deployed fraction of net worth, discipline over indicators — and are cited in no quantitative claim. B-tier expiry-day quantification (75%-by-14:00 decay, VIX>16 sizing rule, dead-zone bounds) is carried as hypotheses under §5/§7 pending re-estimation in our own shadow data. Nothing contradicted in the sources required deletion; the three "conflicts" found upstream (STT 3-step rate path, ₹35.03 vs ₹35.53 txn, 93%/91%/87.7% SEBI figures) are resolved as rate history, live-vs-circular tariff, and successive study vintages respectively.
