# R10: Backtesting rigor — MAE/MFE excursion analysis, multiple-testing correction (Deflated Sharpe), walk-forward / purged K-fold, and exact Indian transaction-cost reality for NIFTY option scalping

## Sources

| # | Title | Authors/Org | Year | Tier | URL | One-line claim |
|---|-------|-------------|------|------|-----|----------------|
| 1 | The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality | Bailey & López de Prado (J. Portfolio Mgmt / SSRN) | 2014 | Primary (peer-reviewed) | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 | A backtest that doesn't report the number of trials N attempted is "worthless, regardless of how excellent the reported performance"; DSR deflates SR for multiple testing + non-normality. |
| 2 | Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance | Bailey, Borwein, López de Prado, Zhu (Notices of the AMS) | 2014 | Primary | https://www.davidhbailey.com/dhbpapers/backtest-pseudo.pdf | E[max SR] over N skill-less trials ≈ (1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne)), bounded above by √(2·ln N); N=10 junk trials already yields expected IS Sharpe ≈ 1.57. |
| 3 | The Deflated Sharpe Ratio in Practice | Dmitri De Freitas | 2024 | Working paper/implementation | https://dmitridefreitas.com/papers/Deflated-Sharpe-Ratio-Working-Paper.pdf | Best of 200 zero-skill strategies shows Sharpe 2.12 and naive PSR 0.9999, but DSR drops it to 0.81 — failing a 95% bar, correctly. |
| 4 | The Deflated Sharpe Ratio, read closely | Interactive ML (blog) | 2024 | Explainer | https://interactiveml.org/blog/deflated-sharpe-ratio | "False Strategy Theorem": after 1,000 independent skill-free backtests the expected best Sharpe is ≈ 3.26; almost no backtest reports trial count. |
| 5 | MAE/MFE-informed management (Risk, Sizing & Exits concept) | LuxAlgo Library | n.d. | Practitioner explainer | https://www.luxalgo.com/library/concept/mae-mfe-informed-management/ | Framework from John Sweeney: plot each trade's MAE/MFE vs final outcome; stops wider than the winners' MAE cliff pay for losers without saving winners; normalize in R/ATR and re-estimate per regime. |
| 6 | MAE and MFE — trade analysis & stop/TP calibration | forex-basics.com | n.d. | Practitioner explainer | https://forex-basics.com/practice/mae-mfe-trade-analysis/ | Sweeney (Wiley 1996) coined MAE; need ≥100 trades; set stop at 1.1–1.2× the average MAE of *winning* trades; recalibrate position size after widening. |
| 7 | Calibrate Stops and Targets with MFE/MAE Data | Tradewink | n.d. | Practitioner explainer | https://www.tradewink.com/learn/mfe-mae-exit-calibration-guide | Optimal stop ≈ 85th–90th percentile of the winning-trade MAE distribution (bucketed in 0.2R bins over 50+ trades, ideally 100+); use only eventual winners for stop calibration. |
| 8 | MAE/MFE Excursion Analyzer in MQL5 | MQL5 Articles | 2024 | Practitioner/code | https://www.mql5.com/en/articles/23245 | Concrete protocol: reconstruct per-trade MAE/MFE from M1 candles; stop suggestion = winners' p90 MAE, target suggestion = winners' median MFE. |
| 9 | Cross Validation in Finance: Purging, Embargoing, Combinatorial | QuantInsti (summarizing López de Prado, *Advances in Financial ML*, Wiley 2018, ch. 7 & 12) | 2018/2020s | Primary-derived explainer | https://blog.quantinsti.com/cross-validation-embargo-purging-combinatorial/ | Labels with forward-looking windows leak across folds; purge training rows whose label windows overlap the test set and embargo a post-test buffer. |
| 10 | Purged & Embargoed Cross-Validation, Explained | Quant Memo | n.d. | Explainer | https://quantmemo.com/concepts/purged-embargoed-cv | Purging closes direct label-overlap leakage; embargo neutralizes serial-correlation leakage *after* the test window — both are required for unbiased CV scores on financial data. |
| 11 | Walk-Forward Optimization — Hardening Strategy Parameters Against Overfit | Keel | n.d. | Practitioner explainer | https://usekeel.io/learn/walk-forward-optimization | IS window typically 2–3× OOS; aggregate stitched OOS performance is the honest metric; wild best-parameter drift across windows = fitting noise. |
| 12 | Walk-Forward Validation: Anchored vs Rolling Windows | QuanterLab | n.d. | Practitioner explainer | https://quanterlab.com/articles/foundations-walk-forward | Anchored (expanding) vs rolling (fixed-width) windows diagnose regime stability; compute OOS/IS "decay ratio" — 1.0 means no decay; also compute DSR on the stitched OOS curve. |
| 13 | Budget 2024: STT rate revised w.e.f. 1 Oct 2024 | TaxGuru (Finance (No.2) Act 2024) | 2024 | Secondary (statute-based) | https://taxguru.in/income-tax/budget-2024-securities-transaction-tax-rate-revised-wef-1st-october-2024.html | STT on sale of options raised 0.0625% → 0.1% of premium; futures 0.0125% → 0.02%; effective 1 Oct 2024. |
| 14 | STT hike on F&O effective April 1, 2026 (Finance Act 2026) | NSE circular (via Bigul PDF) / CNBC-TV18 / Business Today | 2026 | Primary (exchange circular) + news | https://bigul.co/pdf/FATAX73524.pdf ; https://www.businesstoday.in/markets/story/bt-explainer-how-stt-charges-hike-from-april-1-will-impact-investors-fo-traders-old-vs-new-tax-522755-2026-03-27 | From 1 Apr 2026: STT on option-sale premium 0.1% → **0.15%**; options exercise 0.125% → 0.15%; futures 0.02% → 0.05%. **This is the rate in force today (2026-09).** |
| 15 | NSE circular: Revision in Transaction Charges (FA64232) | NSE | 2024 | Primary (exchange circular) | https://archives.nseindia.com/content/circulars/FA64232.pdf | From 1 Oct 2024, SEBI "true-to-label/uniform" regime: equity options ₹35.03 per lakh of premium each side (0.03503%); cash ₹2.97/lakh; futures ₹1.73/lakh. |
| 16 | Zerodha charges page | Zerodha | 2026 (current) | Primary (broker tariff) | https://zerodha.com/charges/ | Options brokerage flat ₹20/executed order; STT now shown as 0.15% sell-side on premium; NSE options txn 0.03553% on premium (₹35.53/lakh — small revision vs ₹35.03); GST 18% on brokerage+SEBI+txn; SEBI ₹10/crore; stamp 0.003% buy side. |
| 17 | Revision in lot size of index derivative contracts (SEBI circular SEBI/HO/MRD/TPD-1/P/CIR/2024/132) | NSE / Zerodha bulletin | 2024 | Primary | https://zerodha.com/marketintel/bulletin/393605/revision-in-lot-size-of-index-derivative-contracts-from-november-20-2024 | Min contract value ₹15–20 lakh ⇒ **NIFTY lot 25 → 75** for contracts introduced from 20 Nov 2024 (BANKNIFTY 15→30, SENSEX 10→20). |
| 18 | What buying an option on NSE actually costs | alphabench (842,350 contract-minutes of NIFTY/BANKNIFTY quotes, 27 sessions, 461 contracts) | 2026 | Empirical study | https://www.alphabench.in/blog/what-buying-an-option-actually-costs | Median option round trip = **59.1 bps of premium**: 28.4 bps statutory+brokerage, 30.7 bps bid-ask spread (spread is 52% of the bill); breakeven = 23.4% of a typical 15-min move but only 4.7% of a full-session move; flat ₹20 means 43 bps cost on ₹25k positions vs 25 bps on ₹3 lakh. |
| 19 | Option Chain Bid-Ask Spread — Liquidity Read | Strota | n.d. | Practitioner data guide | https://strota.in/option-chain-bid-ask | NIFTY ATM weekly spreads ₹0.50–2.00 (1–2% of premium); 3–5% OTM ₹2–5; >5% of mid = limit orders only at mid. |
| 20 | Updated SEBI study: 93% of individual F&O traders lost money FY22–FY24 | SEBI (press release + research paper) | 2024 | Primary (regulator) | https://www.sebi.gov.in/media-and-notifications/press-releases/sep-2024/updated-sebi-study-reveals-93-of-individual-traders-incurred-losses-in-equity-fando-between-fy22-and-fy24-aggregate-losses-exceed-1-8-lakh-crores-over-three-years_86906.html | 92.8% of individuals (1.13 crore) lost avg ≈ ₹2 lakh each, aggregate ₹1.81 lakh crore over FY22–24, *inclusive of transaction costs*; only ~1% earned >₹1 lakh after costs. |
| 21 | Kelly Criterion for Traders / Fractional Kelly guides | Complete Traders Edge; withengine.ai; Pomegra | 2024–26 | Practitioner explainers (based on Kelly 1956; MacLean-Thorp-Ziemba fractional Kelly) | https://completetradersedge.com/kelly-criterion-trading/ ; https://www.withengine.ai/blog/kelly-vs-fixed-fractional-sizing | f* = (bp − q)/b; full Kelly gives 30–50% drawdowns and is catastrophically wrong under estimation error (55% WR over 100 trades has ±10% CI); institutional practice is ¼–½ Kelly, often with a hard NAV cap; ½-kelly keeps ~75% of growth with ~half the variance. |

## Findings

**MAE/MFE (topic a)**
- Origin: John Sweeney, *Maximum Adverse Excursion* (Wiley, 1996) [S5, S6]. The question it answers: *given my entries, where do stops/targets belong, and how much P&L am I donating by misplacing exits?* Final P&L records the destination; MAE/MFE record the path [S5].
- Method: per trade, MAE = entry − lowest price while open (long), MFE = highest − entry; **normalize in R (or ATR) so trades are comparable** [S5, S7].
- Need **≥100 trades per setup** before distributions mean anything; 50+ minimum [S6, S7].
- Stop placement: use the **MAE distribution of winning trades only** (losers tell you nothing about how much noise winners survive). Optimal stop ≈ p85–p90 of winners' MAE; practical shortcut = 1.1–1.2× mean winner MAE [S6, S7, S8]. Example given: 89% of winners never exceeded 0.6R adverse ⇒ a 1.0R stop keeps all winners but is wider than needed [S7].
- Target placement: winners' median MFE; if average winner MFE is 50 pts but you exit at 30, capture ratio is 60% (<70% ⇒ target too tight); widen target or trail to lift capture toward median MFE [S6, S8].
- Caveat: excursion stats are sample- and regime-dependent; re-estimate periodically, don't treat as fixed truths [S5].

**Deflated Sharpe / multiple testing (topic b)**
- Core overfitting math [S2]: for N independent skill-less trials, E[max SR] ≈ (1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne)), ≤ √(2 ln N) × σ(SR). Concrete: N=10 junk configs → expected best IS Sharpe 1.57; N=1,000 → ≈3.26 [S2, S4].
- DSR = Probabilistic Sharpe Ratio with the benchmark set to E[max SR] (the hurdle luck alone produces), also correcting for skew/kurtosis (non-normality) and track-record length [S1, S3].
- Worked Monte Carlo: best of 200 zero-skill strategies shows Sharpe 2.12, naive PSR 0.9999, but DSR = 0.81 — fails a 95% bar [S3].
- Practical rule: **log every configuration you ever test** (the "trials diary") — undisclosed search intensity is the most corrosive form of overfitting [S3, S4].

**Walk-forward & purged K-fold (topic c)**
- Walk-forward: optimize on IS, freeze, test on next OOS slice, slide; stitch OOS slices into one curve; compute composite Sharpe + DSR on it. IS:OOS ratio typically 2–3:1 [S11, S12].
- Anchored (expanding) vs rolling (fixed) windows: run both — similar composite Sharpes ⇒ regime-stable strategy; rolling ≫ anchored ⇒ regime shift / stale data hurts [S12].
- Watch **parameter drift** across windows: lookback jumping 20→60→30 means the optimization surface is noise [S11]. OOS/IS decay ratio far below 1 ⇒ overfit [S12].
- Purged K-fold (López de Prado AFML ch.7): standard k-fold leaks because financial labels span forward windows — a training row's label window can overlap the test period. **Purge** those training rows; **embargo** a buffer after the test set to kill serial-correlation leakage [S9, S10]. CPCV (ch.12) builds C(N,K) combinatorial paths for many OOS estimates.

**Indian costs (topic d) & slippage (e) & breakeven (f)** — see calculator below.
- **STT history confirmed**: options sell-side STT on premium 0.0625% → 0.1% on 1 Oct 2024 [S13] → **0.15% on 1 Apr 2026 (Finance Act 2026) — in force today** [S14, S16]. Exercised options: 0.15% on intrinsic (buyer pays).
- NSE exchange txn on options: ₹35.03/lakh premium each side since Oct 2024 (uniform, true-to-label) [S15]; broker pages currently pass through ₹35.53/lakh (0.03553%) [S16] — ₹0.04/side/lot difference, immaterial.
- GST 18% on (brokerage + exchange txn + SEBI); SEBI ₹10/crore; stamp duty 0.003% buy-side on options [S16].
- Flat ₹20/executed-order brokerage **dominates single-lot scalping**: ~43 bps of premium on a ₹25k position, falling to ~25 bps at ₹3 lakh [S18].
- Slippage/spread reality: median round-trip spread cost ≈ **30.7 bps of premium** across the whole panel; ATM NIFTY weekly quoted spreads ₹0.5–2 absolute (~1–2% of premium); under-₹20 premiums are the worst (57 bps median spread) [S18, S19].
- Breakeven: a scalper holding 15 min must capture **23% of the typical 15-min move** just to break even; a full session only 4.7% [S18] — costs are a fixed toll, edge must scale with holding time.
- Context anchor: 93% of retail F&O traders lost money FY22–24, avg net loss ≈₹2 lakh *including costs* [S20] — cost drag is a major (silent) component.

**Kelly-lite sizing (topic g)**
- f* = (bp − q)/b with b = reward:risk, p = win prob [S21].
- Full Kelly ⇒ 30–50% drawdowns and violent sensitivity to mis-estimated p (a 55% win rate measured on 100 trades has ±10% CI) [S21].
- Consensus retail/institutional practice: **¼–½ Kelly**, plus a hard cap (e.g. max 1–2% NAV risk per trade, daily loss stop). ½-Kelly keeps ~75% of growth with roughly half the variance; ¼-Kelly keeps ~56% growth with ~quarter variance [S21].

## Cost calculator — exact per-trade cost breakdown for a NIFTY option round trip (₹ math, assumptions stated)

**Assumptions (2026-09-16 rates):** 1 lot = 75 units (post-Nov-2024 lot size [S17]). ATM NIFTY weekly, buy at premium ₹100.00, sell same day at ₹100.00 (zero gross P&L) ⇒ premium turnover ₹7,500 per side = ₹15,000 round trip. Discount broker, flat ₹20/executed order, one order per leg [S16]. Rates: STT 0.15% sell-side premium [S14]; NSE txn 0.03553% premium/side [S16]; GST 18% [S16]; SEBI ₹10/crore; stamp 0.003% buy-side [S16]. Tick ₹0.05 (1 tick = ₹3.75/lot).

| Component | Buy leg | Sell leg | Round trip |
|---|---|---|---|
| Brokerage | ₹20.00 | ₹20.00 | **₹40.00** |
| STT (0.15% × sell premium) | – | ₹11.25 | **₹11.25** |
| Exchange txn (0.03553% × premium) | ₹2.66 | ₹2.66 | **₹5.33** |
| SEBI fee (₹10/crore of turnover) | ₹0.0075 | ₹0.0075 | **₹0.02** |
| Stamp duty (0.003% buy side) | ₹0.23 | – | **₹0.23** |
| GST 18% on (brk + txn + SEBI) | ₹4.08 | ₹4.08 | **₹8.16** |
| **Explicit cost total** | ₹26.98 | ₹37.99 | **≈ ₹64.98 /lot** |

- Explicit cost per unit of premium: 64.98/75 = **₹0.87 ≈ 17 ticks ≈ 87 bps of the ₹100 premium** [consistent with S18's finding that small positions pay ~2× the bps of large ones].
- Spread/slippage (must add): ATM weekly half-spread ×2 legs ≈ **30.7 bps median ⇒ ₹0.31/unit ⇒ ≈₹23/lot** [S18]; range ₹23–75 depending on strike/time (spread ₹0.5–2 [S19]). Market-order impact beyond spread: +1 tick/side = ₹7.5.
- **Realistic all-in round trip ≈ ₹95 (±20) per lot = ₹1.25/unit ≈ 25 ticks ≈ 1.3% of premium.**
- Underlying breakeven: with ATM delta ≈0.5, NIFTY must move ≈ **2.5 index points in your favour** just to offset ₹1.25 premium of frictions (before any alpha). To net a modest ₹10 premium points after costs, you need ≈11.3 premium points of favourable excursion (~22 index points of delta-equivalent move).
- Scaling law: on 10 lots in one order per side, explicit cost/lot falls to ≈ ₹22.5 (30 bps of premium) — the flat ₹40 brokerage amortizes [S16, S18]. **Single-lot scalping is structurally the most expensive way to trade.**
- Sensitivity: if the trade exits at ₹80 (a loss), STT falls to ₹9.0 (saving ~₹2.3); if at ₹130, STT ₹14.6. Brokerage/GST dominate and are fixed.

## MAE/MFE protocol — how we should use excursions to set stops/targets

1. **Instrument the sim first:** every backtested/paper trade logs entry price/time, plus the running min & max of the option *mid price* (not LTP) each tick while the position is open. MAE = entry − min_bid-side; MFE = max_ask-side − entry (short positions mirrored) [S5, S7].
2. **Normalize:** convert both to R units: MAE_R = MAE / planned initial risk per unit; MFE_R = MFE / same denominator (or ATR units if risk varies) [S5].
3. **Accumulate ≥100 trades per setup type** (per regime bucket: trend day vs chop day, expiry-day vs not). Below 50–100 trades the percentiles are noise [S6, S7].
4. **Stop calibration:** filter to *winning* trades only → bucket MAE_R in 0.2R bins → set proposed stop at the **p85–p90 of winners' MAE** (sanity shortcut: 1.1–1.2× mean winners' MAE). Rationale: a stop shallower than this clips real winners; deeper pays for losers without saving winners [S6, S7, S8].
5. **Target calibration:** from winners, take **median MFE** as candidate target; compute capture ratio = realized avg win / avg winners' MFE. If < ~0.7, the exit donates profit → raise target or switch to a trail [S6, S8].
6. **Losers' check:** if many losers had small MAE then explode past the stop, entries—not stops—are the problem (entry quality filter needed) [S5].
7. **Guard against overfit:** re-derive percentiles on a rolling window (e.g. last 3 months / 200 trades), refuse changes smaller than ~0.1R, and never tune stops on the same sample used for signal selection [S5, S3].
8. **Feed into alerts:** the bot's suggested stop = winners' p90 MAE; suggested target = winners' median MFE; both recomputed weekly from live trade logs.

## Implications for our bot — realism filters to encode

- **Hard cost model in every backtest:** ₹20/side brokerage, STT 0.15% sell premium, txn 0.03553%/side, GST 18%, stamp 0.003% buy, SEBI ₹10/cr, plus per-trade slippage = max(half quoted spread, 1 tick) per leg; never simulate exits at mid/LTP [S14, S15, S16, S19].
- **Minimum-edge gate per alert:** expected premium move (signal forecast) must exceed ≈ 3× the all-in cost (≈₹1.3/unit single-lot ⇒ demand ≥4 premium points ≈ 80 ticks of expected MFE) before firing an alert.
- **Liquidity gate:** only alert when quoted spread ≤ 2% of mid premium and strike is within ±3% of spot; prefential ATM/Nifty-weekly flow window [S18, S19].
- **Holding-time bias:** sub-15-minute scalps need to capture >23% of the typical move to break even [S18] — the bot's default horizon should sit at 30 min–2 h where breakeven capture is 8–17%.
- **Statistical hygiene:** maintain a trials log; signal go-live requires DSR > 0.95 given N trials attempted, walk-forward stitched-OOS Sharpe with decay ratio ≥ 0.5 of IS, and purged K-fold CV with embargo for any ML component [S1, S4, S9, S11, S12].
- **Sizing output:** alert includes position size = min(¼-Kelly from trailing 100+ trade stats, 1–2% NAV risk, margin cap); full Kelly never suggested [S21].
- **Honesty anchor:** 93% of retail F&O traders lose after costs [S20] — report cost-inclusive P&L in every dashboard, and show "ticks to breakeven" per alert.

## Open questions

1. Zerodha currently displays NSE options txn as 0.03553% (₹35.53/lakh) vs the Oct-2024 NSE circular's ₹35.03/lakh — locate the intermediate NSE revision circular to pin the live rate (impact <₹0.05/side/lot, immaterial, but nice to be exact) [S15, S16].
2. NIFTY weekly expiry weekday moved (Thursday→Tuesday standardisation, Sep 2025) — confirm current expiry day before encoding any expiry-day logic [S19/S21-adjacent webnotes reference].
3. Slippage numbers here are *quoted-spread* medians, not achieved fills [S18]; we should measure our own realized slippage from order-level paper fills during the pilot.
4. Does our signal's expected MFE distribution survive costs at 1-lot size, or is the bot only viable at ≥5–10 lots per alert (where explicit cost drops from ~87 to ~30 bps)? Sizing-floor policy needs deciding.
5. Any further Budget-2027 STT/charge changes (STT has now hiked twice in 18 months: Oct 2024, Apr 2026) — rate drift risk for a scalping product is real; charges must be config-driven, not hard-coded.
