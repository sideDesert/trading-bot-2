# R04: Implied-Volatility & Greeks-Based Signals for Intraday Option Buying (NIFTY 0DTE-style scalping)

## Sources

| # | Title | Authors/Org | Year | Tier | URL | One-line claim |
|---|-------|-------------|------|------|-----|----------------|
| 1 | Selling Options When IV Is High: Does Timing Work? | The Options Bench (T. Chen) | 2026 | B (industry backtest, 20yr SPX) | https://theoptionsbench.com/selling-options-when-iv-is-high/ | High-IV-rank filtering improves per-trade quality for sellers (5.89%→3.30% CAGR but −28.7%→−20.6% DD) — IVR is a risk dial for sellers, not a buyer's entry signal |
| 2 | Does Selling Puts in High IV Work? 166,000 Trades | Expire Worthless | 2024 | B (data blog, 166k trades) | https://www.expireworthless.com/blog/does-selling-puts-in-high-iv-actually-work | High IV does NOT change win rate at fixed delta (82.0% vs 82.5% at 0.20Δ); it doubles premium — IVR levels are a sell-side signal |
| 3 | IV Rank for NIFTY Options: When to Sell Premium vs Buy Options | MarketNetra | 2025 | C (India desk blog, backtests cited) | https://marketnetra.in/blog/iv-rank-nifty-options-when-to-buy-sell | NIFTY backtests 2019–24: IVR>50 favors sellers; IVR percentile more robust than rank for NIFTY (single spikes like 4-Jun-2024 compress rank) |
| 4 | The Behaviour of Option's Implied Volatility Index: A Case of India VIX | Business: Theory & Practice (Vilnius Tech journal) | 2019 | A (peer-reviewed) | https://journals.vilniustech.lt/index.php/BTP/article/download/8279/7143/19585 | India VIX rises significantly on Mondays (+2.35–2.44% at open, 1% sig.), falls on expiry day — weekend uncertainty priced in Monday AM |
| 5 | What Actually Happens to Option Premium on Nifty Expiry Day | Intraday Lab | 2025 | C (data blog, 100 expiry sessions) | https://intradaylab.com/blog/nifty-expiry-premium-decay-backtest | On NIFTY expiry days, ~75% of ATM premium is gone by 2 PM; slowest decay in first 45 min; fastest consistent decay 1:00–2:30 PM; correct-but-late directional buys still lost 20–30% |
| 6 | Nifty Premium Decay Analysis | JustTicks | 2025 | C (live-data tool vendor) | https://justticks.in/premium-decay/NIFTY | Expiry-day ATM NIFTY option loses 70–80% of remaining value between 1:00–3:00 PM; time-of-day matters more than day-of-week late in the week |
| 7 | Nifty Expiry Day Analysis: Patterns, Data | MarketNetra | 2025 | C (India desk, Jan 2023–Dec 2024 sample) | https://marketnetra.in/blog/nifty-expiry-day-analysis-patterns-data | Expiry-day range 180–220 pts vs 140–170 non-expiry (+25–30%); 68% of expiries stayed inside open ATM straddle expected move; 32% broke it; first 45 min + last 90 min ≈ 60% of day's range |
| 8 | NIFTY Weekly Expiry — Mechanics, IV Crush, Patterns | Strota Learn | 2025 | C (education) | https://strota.in/nifty-weekly-expiry-tuesday | Naive option buying on expiry day fights both theta and IV crush; max-pain pinning observable; settlement = last-30-min VWAP |
| 9 | 0DTEs: Trading, Gamma Risk and Volatility Propagation | Dim, Eraker, Vilkov (SSRN) | 2024 | A (working paper) | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4692190 | Market makers' net gamma on average positive and negatively related to future intraday vol; positive MM gamma strengthens intraday reversal, negative strengthens momentum |
| 10 | Gamma Hedging of 0DTE Options (white paper) | Numerix | 2026 | B (vendor white paper, cites Cboe data) | https://www.blog.numerix.com/sites/default/files/file/2026-01/Numerix_White_Paper_Gamma_Hedging_of_ODTE_Options.pdf | 0DTE Greek profile: vega minimal, gamma/theta extreme; net 0DTE MM gamma <1% of S&P futures volume; pinning near high-OI strikes in final hour |
| 11 | 0DTE Gamma Exposure & Pin Risk | FlashAlpha | 2025 | C (analytics vendor) | https://flashalpha.com/articles/0dte-gamma-exposure-pin-risk-intraday-options-analytics | 0DTE gamma 2–5× weekly contracts, up to 10× in final hour (Γ ∝ 1/√T); gamma-flip level = intraday pivot between mean-reversion and trend |
| 12 | 0DTE Trading Rules | Brotherson et al. (SSRN) | 2024 | A (working paper, SPX 2016–2024) | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4641356 | 0DTEs deliver significant variance risk premium; individual option returns highly skewed — only buying deep-ITM calls & selling OTM options statistically profitable at median; realized skewness of underlying is the key predictor |
| 13 | Retail Traders Love 0DTE Options... But Should They? | de Bandt, Gayda et al. (FoFI/Lancaster) | 2024 | A (academic, retail 0DTE fills) | https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf | Retail lost avg $241k/day Feb 2021–Sep 2023 ($350k/day after daily expiries); losses driven by single-leg buys, upfront-premium trades, and HIGH-IV options specifically |
| 14 | The Truth About 0DTE Options Time Decay + intraday hour-by-hour decay | Option Alpha / DaysToExpiry | 2024–25 | C (data collection, SPX minute quotes) | https://optionalpha.com/blog/0dte-options-time-decay ; https://www.daystoexpiry.com/blog/0dte-options-strategy | 0DTE theta non-linear: ATM option decay/hour ~20% morning → 35% at 1.5h left → ~67% in last 30 min; ~100%/hr at close; morning open has overnight-IV deflation |
| 15 | Option Mispricing around Nontrading Periods | Jones & Shemesh, Journal of Finance | 2017 | A (top journal) | https://doi.org/10.1111/jofi.12603 | Option returns significantly lower over weekends/nontrading periods due to persistent mispricing of variance when market closed — weekend theta is charged but not earned by buyers |
| 16 | Selling Saturdays: Weekend Risk Premia in 1DTE Put-Write | OptionMetrics | 2024 | B (vendor research) | https://optionmetrics.com/blog/selling-saturdays-weekend-risk-premia-in-1dte-put-write-strategies/ | Monday-expiry short puts earn mean 7.3–11.3bps with best Sharpe despite worst skew (−3.1): IV systematically overprices weekend gap risk → Friday-Monday options are expensive for buyers |
| 17 | How IV Moves Intraday | GreeksLab | 2025 | C (practitioner) | https://greekslab.com/learn/how-iv-moves-intraday | Reliable intraday IV pattern: elevated at open, compresses by 10–10:30 ("open IV crush"), quiet 10:30–2pm; event IV crush within minutes; skew steepens through day |
| 18 | Modeling Intraday Implied Volatility: EURO STOXX 50 | Aalto Univ. thesis | 2014 | B (academic thesis) | https://aaltodoc.aalto.fi/handle/123456789/8948 | IV declines first hour of trading, drifts up midday, declines before close; IV higher Mondays, Fridays lower |
| 19 | Smile in Motion: Intraday Asymmetric IV | El Aoud & others, Algorithmic Finance | 2015 | A (peer-reviewed, 14M trades EuroStoxx/DAX) | https://doi.org/10.3233/af-150048 | Intraday: index return impact on IV is 1.3–1.5× stronger than sticky-strike rule predicts — falling market inflates IV faster than naive models assume |
| 20 | Relative Option Prices and Risk-Neutral Skew as Predictors of Index Returns | Ratcliff, Journal of Derivatives | 2013 | A (peer-reviewed) | https://doi.org/10.3905/jod.2013.21.2.089 | Skew (OTM call IV − OTM put IV) holds weak short-horizon signal: more positive skew weakly predicts next-day index rise |
| 21 | The skewness index (ITSKEW/SKEW): relationship with volatility and returns | Applied Economics | 2021 | A (peer-reviewed) | https://ideas.repec.org/a/taf/applec/v53y2021i31p3619-3635.html | Changes in skew index Granger-cause returns (one direction); when skew & vol conflict, volatility signal dominates |
| 22 | Implied Volatility Indices as Leading Indicators of Stock Index Returns? / Relationships Between IV Indexes and Returns | Giot, CORE 2002 / J. Portfolio Mgmt | 2002–2005 | A | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=371461 ; https://doi.org/10.3905/jpm.2005.500363 | Very high IV levels statistically signal imminent short-term index reversal UP (oversold); moderate-high IV is unfavorable; VIX reacts more to down-moves (asymmetry) |
| 23 | The information content of implied volatility index (India VIX) | Shaikh & Padhi-type, Asia-Pacific Fin. Mkts | 2013 | A | https://doi.org/10.1007/s40196-013-0025-4 | India VIX is the best forecast of future realized NIFTY vol and subsumes historical-vol info (efficient forecaster) |
| 24 | Informational Content of India VIX: Evidence 2015–2025 | IJISEM | 2025 | B (journal) | https://ijisem.com/journal/index.php/ijisem/article/download/478/461/1710 | India VIX 1-sigma band contained ~75% of realized monthly NIFTY moves; ΔVIX Granger-causes NIFTY returns (unidirectional); VIX overestimates → persistent VRP |
| 25 | Does VRP from NIFTY options drive volatility-selling excess returns? | Economic Sciences journal | 2024 | B | https://economic-sciences.com/index.php/journal/article/download/356/299/644 | India VIX-implied variance regularly exceeds realized variance → statistically significant positive variance risk premium in Indian options (structural buyer headwind) |
| 26 | High-Frequency Nifty 50 vs India VIX asymmetry (15-min, Oct 2025) | IJISEM | 2025 | C | https://ijisem.com/journal/index.php/ijisem/article/view/423 | Significant negative contemporaneous NIFTY-return/ΔVIX relation at 15-min; VIX responds almost instantaneously, asymmetrically (declines > rallies) |
| 27 | What's the Better Buy: Expensive or Cheap Options? | Schaeffer's Research | 2024 | B (data study, weekly straddles 2023–24) | https://www.schaeffersresearch.com/content/analysis/2024/05/15/whats-the-better-buy-expensive-or-cheap-options | Buying weekly straddles on lowest-IV-quintile stocks: +2.29% avg vs −2.43% for highest-IV quintile; low IV = higher doubling rate (11% vs 9.8%) |
| 28 | Lower entry costs improve outcomes in pre-earnings long options | Noah Intelligence | 2024 | B (31,027 walk-forward cycles) | https://noah-news.com/lower-entry-costs-improve-outcomes-in-pre-earnings-long-options-strategies/ | Cheapest-fifth long straddle entries: 46.3% win, median +4.5%; most expensive fifth: 40.9% win, median 0% — monotone decline by entry cost |
| 29 | IV Change (IV30Chg) as a Volatility Momentum Signal | IVolatility.com | 2024 | B (data study) | https://oicpnl.ivolatility.com/news/3136 | Extreme 5-day IV spikes (>50%) precede +5.45% mean 20-day stock returns (71.4% win); moderate IV changes carry NO edge; IV-change+high-IVP regime strongest |
| 30 | SEBI: Analysis of P&L in Equity Derivatives FY22–FY24 | SEBI | 2024 | A (regulator) | https://rockettrades.com/wp-content/uploads/2024/09/sebi-analysis-of-profits-losses.pdf | 91.1% of individual F&O traders lost money in FY24 (avg −₹1.20 lakh); 60% lose in futures vs 91.5% in options; transaction costs = 28% of losses — buying options is structurally the hardest seat |
| 31 | Do Intraday Volatility Patterns Follow a 'U' Curve? Evidence from Indian Market | SSRN (NSE Nifty tick data) | 2013 | A | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2255391 | NIFTY realized intraday vol is U-shaped: high first 30 min, rising again in last 15 min |
| 32 | A Temporal Analysis of Intraday Volatility of Nifty Futures | MPRA | 2018 | A | https://mpra.ub.uni-muenchen.de/89689/ | Confirms U-shape on 1-min Nifty futures 2011–2018; hourly vol declining over time |
| 33 | The Myth of Option Weekend Decay | Six Figure Investing | 2014 | C | https://www.sixfigureinvesting.com/2014/10/option-weekend-decay-and-volatility-annualizing/ | Options typically open Monday ~unchanged vs Friday close: market makers pre-discount weekend — weekend decay is taken out in advance, not monday-morning visible |
| 34 | 0DTE Options Explained: Real P&L Distribution | Coriva (survey of academic evidence) | 2025 | C | https://coriva.eu.org/en/0dte-options-guide/ | Compiles Bryzgalova-Pavlova-Sikorskaya (2023): retail option traders net losers via spreads/decay/adverse selection; short-dated = worst loss rates; distribution right-skewed, median ≈ full premium loss |

## Findings

### (a) IV rank / IV percentile — who does it help?
- IVR/IVP are calibrated as **seller** filters across large backtests; high IVR raises per-trade premium but, in 20-year SPX tests, high-IVR-only selling actually *lowered* total CAGR (5.89% → 3.30%) because it traded only 14% of months — IVR is a risk dial, not an alpha signal even for sellers [S1].
- At fixed delta, win rate is identical in high vs low IVR (82.0% vs 82.5% at 0.20Δ, 166k trades) — delta already prices the risk; IVR does not carry directional probability information [S2].
- For **buyers**, the actionable reading of IV state is the inverse of folklore: low-IV environments are where long-vol entries historically work. Lowest-IV-quintile weekly straddles averaged **+2.29%** vs **−2.43%** for highest quintile [S27]; cheapest-fifth entry cost straddles won 46.3% / median +4.5% vs 40.9% / 0% for the most expensive fifth, monotone across buckets [S28].
- For NIFTY specifically, **IV percentile is preferred over IV rank** because single spikes (e.g., 26% VIX on 4-Jun-2024 election result) compress the rank for months afterward [S3].
- Retail 0DTE losses are concentrated precisely in **high-IV option buys** [S13] — buying when IV is elevated is the documented losing seat.

### (b) IV vs realized-vol spread (variance risk premium)
- India VIX-implied variance consistently exceeds realized variance → statistically significant, persistent positive VRP in NIFTY options [S25]. Same for SPX 0DTEs [S12].
- India VIX's 1-sigma band contained ~75% of realized monthly NIFTY moves (above the ~68% normal benchmark) — options are conservatively (i.e., expensively) priced on average [S24].
- Structure: per-mover, options buyers pay a chronic premium for convexity; per [S30], 91.5% of individuals in options lose (vs ~60% in futures). **Implication: any buying signal must overcome a structural drag; require IV-to-recent-RV ratio near/below 1 or falling.**

### (c) IV momentum / rising IV
- Extreme 5-day IV changes (>+50%) in equities precede outsized mean-reversion moves (+5.45% / 20d, 71.4% win); **moderate IV changes (<20%) carry no signal** [S29].
- ΔIndia VIX **Granger-causes** NIFTY returns (unidirectional), and 15-min data show VIX reacts nearly instantaneously and asymmetrically (falls more on NIFTY drops) [S24, S26]. For a 5–15-min scalping bot, IV is largely coincident with, not leading, spot — use ΔIV as confirmation/regime filter, not a sole trigger.

### (d) Skew
- Skew changes contain weak next-day directional info (more positive call−put IV gap → slight up bias) [S20]; Δskew Granger-causes returns but **volatility dominates when signals conflict** [S21].
- Intraday, smile dynamics violate sticky-strike: IV responds to index returns 1.3–1.5× more strongly than sticky-strike implies — on sharp NIFTY drops, put IV inflates faster than naive models, so late put buys overpay [S19].
- Put-call IV skew is a viable **snapshot feature** (cheap to compute from chain), but evidence for it as a standalone scalping trigger is weak.

### (e) India VIX dynamics
- **Monday effect**: India VIX up ~+2.35–2.44% at Monday open (1% significance); bleeds lower Tuesday onward [S4]. Monday-morning options are systematically richer — a documented buyer trap coinciding with the folklore.
- India VIX **falls significantly on expiry day** [S4] — consistent with expiry IV crush: naive expiry-day buying fights both theta and collapsing IV [S8].
- VIX asymmetry: reacts harder to NIFTY declines than rallies [S26]; extremely high IV levels statistically precede positive short-term returns (oversold/bounce signal) [S22] — useful contrarian context for call-buy timing after VIX spikes.

### (f) Greeks for scalping expiry-day buys
- **Gamma/theta dominate; vega is nearly irrelevant intraday on expiry** (theta ∝ 1/√T; ATM 0DTE gamma 2–5× weekly, up to 10× in final hour) [S10, S11, S14].
- NIFTY-specific decay numbers: ~75% of ATM premium gone by 2 PM on expiry; **slowest decay in the first 45 min** (opening vol keeps premiums alive); fastest window 1:00–2:30 PM; ATM options lose 70–80% of remaining value between 1–3 PM [S5, S6]. Correct direction entered late still lost 20–30% [S5] — **decision speed matters more than strike choice on expiry day.**
- Hour-by-hour SPX 0DTE profile corroborates: ~20%/h decay morning → ~35%/h at 90-min left → ~67%/h in final 30 min [S14].
- Delta selection evidence: in static SPX 0DTE rules, only **deep-ITM calls** among buys were statistically profitable at median (delta ≈ reducing extrinsic exposure = reducing theta/vega drag); OTM lottery-style buys are the worst seat [S12]. Retail losses concentrate in single-leg, premium-paid, high-IV trades [S13].
- 68% of NIFTY expiries closed inside the opening ATM straddle's expected move — the straddle price is an informative daily-cap feature; on the 32% "break" days, gamma-chasing pays [S7].

### (g) Time-of-day vol patterns
- Realized NIFTY vol is U-shaped: highest first 30 min and last 15 min [S31, S32].
- IV itself: elevated at open, compresses by ~10–10:30 ("open IV crush"), quiet midday, event-driven spikes compress within minutes post-event [S17, S18].
- Expiry day concentrates: first 45 min + last 90 min ≈ **60% of the day's range**; mid-session 12:30–2:00 is a compression "dead zone" where theta bleeds and chop kills buyers [S7, S5].

### Traps (all evidence-backed)
- **Monday-morning IV spike**: VIX +2.4% at open Monday [S4]; weekend gap risk is systematically overpriced (Monday-expiry sellers earn the best Sharpe despite worst skew) [S16] → Monday AM is the worst time to buy premium.
- **Weekend theta is prepaid**: options open Monday roughly unchanged vs Friday close — decay is extracted Friday [S33, S15]; don't expect a Monday "decay bonus," but do expect Friday-Monday-long holds to bleed [S15].
- **Open IV crush**: first 15–30 min entries pay elevated IV that compresses by ~10:00–10:30 [S17].
- **Expiry afternoon**: buying after ~1:00–1:30 PM faces 70–80% decay by 3 PM [S5, S6]; require strong momentum + wide straddle-implied-move breaks to justify.
- **Buying after a sharp drop**: put IV inflates 1.3–1.5× sticky-strike → late put buys overpay [S19]; prefer buying pullback days early in the session, not after IV has re-priced.

## Folklore vs evidence

| Belief | Verdict | Source |
|---|---|---|
| "High IV rank → sell premium is always better" | Half-true: better per-trade economics, but filtering cut 20-yr CAGR (5.89%→3.30%) — risk dial, not return booster | [S1] |
| "High IV means higher chance of OTM options expiring worthless" | False: win rate identical at fixed delta regardless of IVR (82% vs 82.5%) | [S2] |
| "IV rank is the standard NIFTY metric" | Misleading after spikes: use IV percentile for NIFTY (election-day spike distortion) | [S3] |
| "Rising IV confirms a coming big move to buy into" | Only at extremes (>50% 5-day IV change); moderate IV changes carry no edge; IV largely coincident with spot intraday | [S29, S24, S26] |
| "Skew predicts direction for scalping" | Weak/mostly next-horizon; vol beats skew when conflicting | [S20, S21] |
| "Buy Monday-morning dips/spikes for a fast scalp" | Trap: India VIX ~+2.4% at Monday open; weekend risk overpriced; expiry-day IV crush compounds it if Monday is expiry-adjacent | [S4, S16] |
| "Weekend decay rewards Friday sellers at Monday open" | Priced in: MMs discount Friday; options open Monday roughly unchanged, and weekend option returns are reliably lower for holders | [S33, S15] |
| "Theta burns evenly through expiry day; anytime is OK" | False (dangerous): ≈75% of ATM premium gone by 2 PM; decay window 1–2:30 PM is fastest; first 45 min is slowest | [S5, S6, S14] |
| "Vega matters for 0DTE scalps" | Mostly false intraday on expiry: gamma & theta dominate; vega minimal except around events (IV crush) | [S10, S14, S8] |
| "Far OTM cheap strikes are the best lottery buys on expiry" | False: median deep-ITM call buys statistically profitable; OTM buys are the documented retail losing seat | [S12, S13] |
| "India VIX tells you fair daily range" | Directionally true but conservative: 1σ band captured ~75% of moves — implies buyers overpay on average | [S24, S25] |
| "NIFTY expiry day is directionally biased" | False: 52% up/48% down; but range is +25–30% wider and 32% of days break the straddle-implied move | [S7] |

## Implications for our bot

**Vol/Greek features to compute per snapshot (deterministic engine):**
1. **IV percentile (252d) AND IV rank** on ATM weekly IV — prefer IVP for NIFTY [S3]; block/penalize buys when IVP > ~60–70 (buyers' documented losing zone [S13, S27, S28]), favor buys on IVP < ~30 with rising RV.
2. **IV/RV spread**: ATM IV vs trailing 5–10 day realized vol (and vs same-time-of-day realized vol); VRP is chronic, so require spread ≤ normal before buying; flag extreme spread as warning [S25, S24].
3. **ΔIV momentum (1h/5d)**: only extreme IV acceleration carries signal; use as confirmation, not trigger [S29].
4. **Skew snapshot**: IV(Δ25 put) − IV(Δ25 call) and its intraday change; weight low (weak evidence); watch for put-IV over-inflation after sharp drops (avoid chasing puts) [S20, S21, S19].
5. **Theta-per-hour / gamma clock**: required index move (in points) per next 30 min for the candidate strike to overcome decay — if required move > (time-bucket realized-vol median), block the buy [S5, S14].
6. **Time-of-day bucket model**: decay rate × and realized-vol U-shape per 15-min bucket (open crush till ~10:00, midday dead zone 12:30–2:00 expiry days, last-90-min gamma window) [S31, S17, S7].
7. **ATM straddle expected move at open + % consumed**: entry filter — if spot has already covered most of the straddle-implied daily move, odds of further expansion fall (68% containment) [S7].
8. **Delta targeting**: for expiry-day buys prefer ITM/near-the-money (Δ 0.55–0.8) over far OTM [S12].
9. **India VIX level/change**: extreme VIX readings → contrarian call-buy context [S22]; big negative spot move + instant VIX spike = avoid late put buys [S26, S19].

**Hard rules / traps to encode:**
- R1: No fresh longs in first 15–30 min after open (open IV crush + Monday-open IV spike doubly bad Monday) [S17, S4].
- R2: No expiry-day buys initiated after ~1:15–1:30 PM unless a genuine momentum breakout is detected (straddle move already exceeded / strong tape) [S5, S6].
- R3: Block buys when IVP/IVR high (buyer trap) and specifically avoid *high-IV* contracts as the instrument [S13, S27].
- R4: Midday (≈11:30–1:30 non-event, 12:30–2:00 expiry): suppress new directional buys — theta bleed window with lowest realized vol [S7, S5].
- R5: No holding through weekends (weekend option returns reliably negative; mispricing documented in JoF) and expect Friday-close IV to already discount the weekend [S15, S33, S16].
- R6: Post-event (RBI policy, budget, US data at 6–7 PM IST equivalents): delay entries 5–15 min — IV crush resolves within minutes [S17].
- R7: Transaction-cost gate: SEBI shows costs = ~28% of retail losses — require minimum expected move-to-cost ratio before advising any scalp [S30].

## Open questions
- What IVP/IVR threshold actually maximizes NIFTY intraday buy expectancy? (US equity quintile evidence [S27, S28] needs NIFTY-specific weekly backtest.)
- Does India VIX Δ lead NIFTY at 1–5 min or only 15-min+? [S26] uses 15-min bars; our scalping horizon may be below signal scale.
- Quantify expiry-day "dead zone" 12:30–2:00 statistics for NIFTY under the current Tuesday-expiry regime (post-2025 SEBI change); most published decay studies reference Thursday expiries.
- Is NIFTY skew (25Δ RR) intraday-predictive at all? Evidence is entirely US/EU-based [S20, S21, S19].
- What is NIFTY's dealer gamma-flip and max-pain reliability post weekly-expiry restructure? Only SPX evidence exists [S9, S10, S11]; NIFTY pinning claims [S7, S8] are desk-level, not peer-reviewed.
- Optimal delta band for expiry-day scalps balancing theta drag vs leverage — [S12] says deep-ITM median-profitable on SPX; needs NIFTY confirmation including wider spreads on ITM strikes.
