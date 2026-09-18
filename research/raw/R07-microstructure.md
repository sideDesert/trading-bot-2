# R07: Market-microstructure features for seconds-to-minutes price prediction

Scope: which order-flow / book features actually predict price moves at 10s–15min horizons, with what R² in- vs out-of-sample; VPIN evidence; trade signing; volume clock; L1-vs-L2 realism; how findings translate to index options (NIFTY).

Tiers: T1 = top peer-reviewed finance journal (JF/JFE/RFS/JFQA/JFinEc/Quant Fin); T2 = other peer-reviewed journal (JFM, Financial Review, FRL, JPM, ABR, J. Prediction Markets); T3 = working paper / arXiv / SSRN.

## Sources

| # | Title | Authors/Org | Year | Tier | URL | One-line claim |
|---|-------|-------------|------|------|-----|----------------|
| S1 | The Price Impact of Order Book Events | Cont, Kukanov, Stoikov (Columbia/Cornell) | 2014 | T1 (J. Financial Econometrics) | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1712822 | Best-bid/ask order flow imbalance explains ~65% of contemporaneous price-change variance at 10s scale, linear, slope ∝ 1/depth |
| S2 | Cross-Impact of Order Flow Imbalance in Equity Markets | Cont, Cucuringu, Zhang (Oxford) | 2023 | T1 (Quantitative Finance) / arXiv | https://arxiv.org/abs/2112.13213 | Integrated multi-level OFI gets in-sample adj-R²≈87%, but strictly lagged 1-min-ahead OOS R² ≈ −0.4% to −0.1%; predictability decays within minutes |
| S3 | Universal features of price formation in financial markets: perspectives from deep learning | Sirignano, Cont (Oxford/UIUC) | 2019 | T1 (Quantitative Finance) | https://doi.org/10.1080/14697688.2019.1622295 | A universal, stationary order-flow→price-move relation exists; deep models beat linear, remain accurate OOS and on unseen stocks |
| S4 | The Micro-Price: A High Frequency Estimator of Future Prices | Stoikov (Cornell) | 2018 | T1 (Quantitative Finance) | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2970694 | Micro-price (mid adjusted by spread × top-of-book imbalance) beats mid and weighted-mid as short-horizon price predictor, L1-only |
| S5 | The Accuracy of Trade Classification Rules: Evidence from Nasdaq | Ellis, Michaely, O'Hara | 2000 | T1 (JFQA) | https://ideas.repec.org/a/cup/jfinqa/v35y2000i04p529-551_00.html | Quote rule 76.4%, tick rule 77.7%, Lee–Ready 81.1% correct signing; poor inside the spread |
| S6 | Trade signing in fast markets | Carrion, Kolay (Financial Review) | 2019 | T2 | https://doi.org/10.1111/fire.12218 | With 1-s timestamps Lee–Ready signs 86.9% vs tick rule 78.6%; with ms data LR reaches 93.6% and still works in fast markets |
| S7 | Evaluating trade classification algorithms: BVC vs tick rule and Lee–Ready | Chakrabarty, Pascual, Shkilko (J. Financial Markets) | 2015 | T2 | https://ideas.repec.org/a/eee/finmar/v25y2015icp52-79.html | Tick rule / Lee–Ready classify markedly better than Bulk Volume Classification; BVC-based VPIN is the least accurate |
| S8 | The Microstructure of the "Flash Crash": Flow Toxicity… (VPIN) | Easley, López de Prado, O'Hara (Cornell) | 2011 | T2 (J. Portfolio Mgmt) | https://doi.org/10.3905/jpm.2011.37.2.118 | Original pro-VPIN claim: VPIN CDF ≥0.9 hours before the May 2010 flash crash; order flow became "toxic" beforehand |
| S9 | Flow Toxicity and Liquidity in a High Frequency World | Easley, López de Prado, O'Hara | 2012 | T1 (RFS) | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1695596 | Introduces volume-bucket VPIN via bulk volume classification; claims VPIN indicates short-term toxicity-induced volatility |
| S10 | VPIN and the Flash Crash | Andersen, Bondarenko (Northwestern/UIC) | 2014 | T2 (J. Financial Markets) | https://ideas.repec.org/a/eee/finmar/v17y2014icp1-46.html | Anti-VPIN: poor volatility predictor, peaked after (not before) flash crash, predictive content is mechanical relation with trading intensity |
| S11 | Reflecting on the VPIN Dispute | Andersen, Bondarenko | 2014 | T2 (J. Financial Markets) | https://www.sciencedirect.com/science/article/abs/pii/S1386418113000475 | VPIN by construction correlates with volume & volatility innovations; zero incremental predictive power after controls; sign flips with better trade classification |
| S12 | The Volume Clock: Insights into the High-Frequency Paradigm | Easley, López de Prado, O'Hara | 2012 | T2 (J. Portfolio Mgmt) | https://doi.org/10.3905/jpm.2012.39.1.019 | HFT operates in volume-time; sampling in volume buckets (not clock time) is the natural analysis frame |
| S13 | Order Flow, Transaction Clock, and Normality of Asset Returns | Ané, Geman | 2000 | T1 (J. Finance) | https://doi.org/10.1111/0022-1082.00286 | Number-of-trades clock returns asset returns to near-normality; trade count is a better stochastic clock than volume |
| S14 | Order Imbalance, Liquidity, and Market Returns | Chordia, Roll, Subrahmanyam | 2002 | T1 (JFE) | https://www.anderson.ucla.edu/documents/areas/fac/finance/28-00.pdf | Daily aggregate order imbalance is persistent, predicts market returns; high negative imbalance + down day ⇒ predictable reversal |
| S15 | Information content of order imbalance in an order-driven market: Indian Evidence | Tripathi, Dixit, Vipul (Finance Research Letters) | 2021 | T2 | https://ideas.repec.org/a/eee/finlet/v41y2021ics1544612320316779.html | NSE: OIB predicts returns strongly for first 5 min, effect perishes within 30 min; informed flow impacts deeper book levels |
| S16 | Information Content of an Open Limit-Order Book: Indian Evidence | Gupta, Tripathi (IIT Kanpur/IIM; Asia-Pacific… Accounting… ABR) | 2023 | T2 (Australian Business… "ABR" 28(1)) | https://doi.org/10.37625/abr.28.1.34-64 | NSE: deeper LOB levels (L2–L5+) contribute ~50% of price discovery; deeper-level imbalance adds short-horizon predictability beyond L1 |
| S17 | Order Imbalances and Market Efficiency: Evidence from a Pure Order-Driven Market | Jindal, Bajpai, Yadav (J. Prediction Markets) | 2025/26 | T2 | https://doi.org/10.5750/jpm.v19i2.2235 | NSE hourly OIB persistent to 4 lags and predicts returns, but OIB trading-strategy profits vanish after transaction costs |
| S18 | Order-Flow Filtration and Directional Association with Short-Horizon Returns | arXiv authors (NSE BankNifty futures tick data) | 2025 | T3 | https://arxiv.org/abs/2507.22712 | BankNifty futures: unfiltered book imbalance is already a strong short-horizon directional indicator; filtering on parent orders of executed trades strengthens it |
| S19 | The Information of Option Volume for Future Stock Prices | Pan, Poteshman | 2006 | T1 (RFS) | https://www.nber.org/papers/w10925 | Buyer-initiated option put/call ratios predict stocks 40bp next day, >1%/week; publicly observable signed option volume predicts only 1–2 days then reverses (price pressure) |
| S20 | Does option trading convey stock price information? | Hu (SMU; JFE 111(3):625–645) | 2014 | T1 (JFE) | https://doi.org/10.1016/j.jfineco.2013.12.004 | Option-induced stock imbalance (delta-hedge flow of option market makers) significantly predicts future stock returns; non-option imbalance is transitory |
| S21 | Who and what drives informed options trading after the market opens? | Kang, Kang, Lee (KAIST/Gachon; J. Futures Markets 42:338–364) | 2022 | T2 | https://doi.org/10.1002/fut.22301 | Index-option order imbalance in first 10 min predicts index & index-futures returns for rest of day; institutional-driven; profitable after costs |
| S22 | Gamma Fragility | Barbon, Buraschi (Imperial) | 2021 | T1/T3 (RFS/SSRN wp) | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3725454 | Negative ex-ante dealer gamma imbalance + illiquidity → intraday momentum; positive gamma → reversal; explains flash-crash frequency |
| S23 | 0DTEs: Trading, Gamma Risk and Volatility Propagation | Dim, Eraker, Vilkov (SSRN) | 2023 | T3 | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4692190 | 0DTE SPX: MM net gamma usually positive and inversely related to future intraday vol; positive(negative) gamma strengthens intraday reversal(momentum) |
| S24 | Returns and Order Flow Imbalances: Intraday Dynamics and Macroeconomic News Effects | arXiv authors (E-mini S&P futures structural VAR) | 2025 | T3 | https://arxiv.org/abs/2508.06788 | At 1-second frequency both price impact and flow impact are significant, but shocks dissipate almost entirely within ~1s; magnitudes vary with spread/liquidity intraday |

## Findings

### (a) OFI / trade imbalance: magnitudes of predictability
- [S1] Cont-Kukanov-Stoikov, 50 NYSE stocks, 10s–1min windows: regressing mid-price change on contemporaneous best-level OFI gives **average R² ≈ 65%** (half-hourly regressions; β significant in 98% of sub-samples; slope inversely proportional to queue depth; linear — higher-order terms insignificant). OFI at best bid/ask dominates; deeper-book events add only second-order explanatory power.
- CRITICAL realism caveat [S2][marketmaker.cc summary of S1]: the 65% figure is a **contemporaneous decomposition, not a forecast**. Cont-Cucuringu-Zhang (2023) run the strictly-lagged version on minute data: integrated multi-level OFI gives contemporaneous in-sample adj-R² ≈ **87%**, but **one-minute-ahead out-of-sample R² is negative-to-nil (−0.37% to −0.10% mean)**, estimated on rolling 30-min windows for ~100 US stocks. Lagged cross-asset OFI helps only up to a few minutes; predictability "decays quickly" over horizons f∈{2,3,5,10,20,30} min. Economic takeaway: OFI is world-class at explaining what is happening *now* at the tick level (excellent execution/momentum-ignition conditioning feature), modest-to-negligible as a standalone point forecast at ≥1 min.
- [S3] Nonlinear (deep) models of order-flow history predict the *direction* of next mid-price moves with stable out-of-sample accuracy across stocks and a full year out of sample; universal model beats asset-specific models; adding longer OFI/price history helps (path dependence). No causal-tradeable Sharpe proven, but establishes direction-predictability is real and stationary.
- [S15] NSE (195 active stocks): OIB return predictability is **strong for the first 5 minutes and perishes within 30 minutes** — consistent with an Indian 5–15 min ceiling for imbalance signals.
- [S14] Chordia-Roll-Subrahmanyam (daily): order imbalance is highly persistent and affects market returns contemporaneously and lagged; after high negative imbalance + big down days there is a **partially predictable reversal** — a conditioning rule (imbalance × return interaction), not a pure momentum signal.
- [S18] BankNifty futures (NSE tick data, 2025): unfiltered book imbalance is *already* a strong short-horizon directional indicator; filtering to executed parent orders strengthens association; order-lifetime/modification filters on quotes add little — in noisy Indian order flow, executed-flow imbalance > quote imbalance.
- [S24] E-mini at 1-s resolution: price-impact/flow-impact shocks dissipate almost entirely within ~1 second — sub-second persistence is irrelevant for a 10s+ bot; but impact coefficients vary intraday with spread/liquidity (use as conditioning, not the signal at 1s).

### (b) VPIN — for and against
- FOR [S8][S9]: Easley-López de Prado-O'Hara: volume-bucket VPIN (bulk volume classification) hit CDF≥0.9 before the flash crash and correlates with future short-term volatility; no parameter estimation needed.
- AGAINST [S10][S11]: Andersen-Bondarenko on E-mini tick data: VPIN (i) did **not** reach extremes before the flash crash (peaked after); (ii) has **no incremental power for future volatility once current volume and volatility are controlled** — its "predictive content" is a mechanical trading-intensity relation; (iii) flips behavior (sign reversal) when trades are classified transaction-by-transaction instead of BVC. [S7] independently shows BVC is the least accurate signer.
- Verdict for us: do not deploy VPIN as a toxicity/crash predictor. The salvageable components are its *inputs* — volume-bucketed signed-buy-minus-sell imbalance and trade intensity — used directly, standardized by contemporaneous volume/vol regime.

### (c) Tick-rule trade signing & buy/sell volume imbalance
- [S5] Nasdaq: tick rule 77.7%, quote rule 76.4%, Lee–Ready 81.1% correct; all degrade inside the spread.
- [S6] In fast markets with 1-s timestamps (our realistic retail resolution): **LR 86.9% vs tick rule 78.6%**; with ms stamps LR reaches 93.6%. Quote data materially improves signing.
- Practical: on Upstox LTP ticks (no aggressor flag, ~1 per second per instrument on liquid strikes), sign by tick rule *hybridized with the prevailing best bid/ask when available* (i.e., LTP change relative to quote midpoint → Lee–Ready-lite). Expect ~80–87% per-trade accuracy; at 10s–60s aggregation the noise partially cancels since misclassification is roughly symmetric.
- Signed volume imbalance over rolling windows (10s/60s/300s) and cumulative delta (Σ signed volume) are the usable outputs. NSE evidence [S15][S17][S18] says these carry real 5–30 min signal but gross alpha dies after costs [S17] — so use as *conditioning/filter* features, and for trade-side asymmetry, not as naive standalone triggers.

### (d) Volume clock / trade intensity
- [S13] Ané-Geman: returns measured on a **trade-count clock are nearly Gaussian**; number of trades is a better clock than volume. [S12] ELO: sophisticated flow operates in volume time.
- Implication: sample/compute features in event/volume time (per N ticks or per X lots traded), and include **trade intensity** itself (ticks/second, time-to-fill a fixed volume bucket, expected vs actual ticks vs time-of-day baseline) as a feature set. Intensity spikes standardize regime (liquidity events vs quiet tape) — and per [S10], intensity is the channel through which VPIN appeared to work.

### (e) Spread & depth as conditioning features
- [S1] OFI price-impact slope ∝ 1/(queue depth): the same imbalance moves price more when the book is thin → divide OFI by contemporaneous depth (Kyle-lambda-style normalization).
- [S24] Impact parameters and vol vary intraday with spread/liquidity/trading intensity; [S15][S16] informed flow shows up at deeper levels and during low-liquidity regimes. [S22][S23] momentum-vs-reversal conditioning flips with dealer gamma sign and illiquidity.
- Actionable conditioning set: spread (ticks & bps), top-5 depth totals, book slope, imbalance×(1/depth) interaction, India VIX / regime flag, time-of-day dummy (open/close vs midday), gamma-exposure sign (from option-chain OI).

### (f) What is realistic from L1-only (or no quotes at all)
- L1-only studies with proven short-horizon value: S1 (best bid/ask only is where ~most of OFI signal lives), S4 (micro-price needs only best bid/ask/qty), and imbalance I=(Qbid−Qask)/(Qbid+Qask) is the "worst-kept secret of HFT" per later literature citing queue-imbalance findings.
- No-quotes-at-all (plain LTP/volume/OI ticks): tick-rule signed volume imbalance [S5][S6 ~78-87% accuracy], tick-count imbalance, trade intensity/volume-clock features [S13][S12], VWAP deviation, LTP-change volatility, OI-change features. All computable.
- 5-depth (Upstox full mode) adds: true OFI event stream [S1], multi-level imbalance (worth ~[S16] deeper-level info in Indian data — ~50% of price discovery beyond the touch in NSE equities), micro-price, book slope.
- Marginal value ordering for us: L1 quote imbalance ≈ true OFI (needs quotes) > tick-rule signed trade imbalance (no quotes) > L2-5 imbalance > VPIN (skip).

### (g) Translation to index options / hedging flows
- [S22] Barbon-Buraschi: large negative aggregate dealer gamma + illiquid underlying ⇒ delta-hedging feedback creates **intraday momentum**; positive gamma ⇒ **reversal**. Gamma imbalance also predicts flash-crash frequency/magnitude.
- [S23] 0DTE evidence (SPX): MM net gamma positive on average; positive.(negative) MM gamma strengthens intraday reversal (momentum); gamma negatively related to future intraday vol. Consistent with hedging-flow feedback, not information.
- [S21] KOSPI index options: order imbalance in options in the first 10 minutes predicts index AND index-futures returns for the rest of the day (institutions, survives costs) — the direct template for NIFTY: opening-window option flow is a day-horizon feature.
- NIFTY-specific caveat: weekly/daily-expiry 0DTE-style NIFTY options with massive retail premium selling ⇒ dealer gamma sign flips intraday far more often than US; compute GEX from option-chain OI each snapshot (proxy gamma with BSM using LTP-implied or VIX-scaled vol), and treat (GEX sign)×(illiquidity) as the momentum-vs-reversal regime selector per [S22][S23].

### (h) Options-market aggregate flow predicting underlying
- [S19] Pan-Poteshman: buyer-initiated option put/call ratios predict underlying stocks 40bp next day / >1% next week; **publicly observable signed option volume predicts only 1–2 days then reverses** (price pressure, not pure information). For intraday use, the reversal part matters: extreme option-flow imbalance → drift then partial reversion.
- [S20] Hu (JFE 2014): the genuinely predictive component is **option-induced stock imbalance** = delta-weighted signed option flow that market makers must hedge in the underlying; the option-independent imbalance is only transitory. Direct implication: compute **delta×ΔOI** (or delta×signed-volume) aggregated across strikes as "implied hedge flow" on NIFTY futures — it should lead the underlying at minute horizons.
- [S21] Opening 10-min index-option imbalance → rest-of-day index returns. For our scalping horizons this is a slow background feature; the fast version is rolling 1–5 min aggregate option signed-ΔOI.

## Realism check — computability from our feeds

Computable from plain LTP/volume/OI ticks (Upstox `ltpc` mode, option-chain REST):
- Tick-rule signed volume, buy/sell volume imbalance at 10s/60s/300s (≈78.6% per-trade signing accuracy at 1-s stamps [S6]; aggregation mitigates)
- Tick-count imbalance; ticks-per-second; time-to-fill fixed-volume buckets (volume clock) [S12][S13]
- Realized vol, EWMA vol, LTP autocorrelation (reversal detection), VWAP + deviation
- ΔOI per strike, PCR(OI), PCR(volume), max-pain drift, GEX proxy (BSM gamma × OI), delta×ΔOI hedge-flow aggregate [S20][S22][S23]

Needs L1 quotes (Upstox `full` mode on premium — we have this per project constraints, confirm):
- Best-bid/ask volume imbalance I; micro-price [S4]; spread (bps); top-depth Kyle-lambda normalization of imbalance [S1]
- Hybrid Lee–Ready trade signing (LTP vs quote midpoint → ~87% accuracy) [S6]

Needs 5-depth (also in `full` mode):
- True Cont-et-al event-level OFI [S1]; multi-level imbalance L1…L5 [S16 ~50% of NSE price discovery beyond touch]; book slope; multi-level integrated OFI (PCA) [S2]

NOT recommended despite popularity: raw VPIN as predictor [S10][S11]; BVC classification [S7]; contemporaneous OFI used as if it were a forecast [S2].

Latency/limits to watch: Upstox websocket updates for option strikes are ~1/sec event-batched, so tick timestamps effectively 1-s → tick-rule accuracy ≈78–87%, LR-hybrid possible only when quote updates interleave; option-chain REST polling (~3–10s) limits ΔOI features to ≥ multi-second horizons. No aggressor-side flag in feed ⇒ all signing is inferred.

## Implications for our bot — features to add to the snapshot

Per instrument (NIFTY futures + focus ATM±3 strikes), at each tick/1s bin:
1. `ofi_l1_event` / rolling `ofi_10s`, `ofi_60s` — Cont-et-al top-of-book OFI if quotes present [S1]; else tick-rule signed-volume proxies.
2. `vol_imb_l1` = (Qbid−Qask)/(Qbid+Qask); `microprice_dev` = microprice − mid [S4].
3. `signed_vol_imb_{10s,60s,300s}` (tick/LR-hybrid signed; normalized by trailing median volume); `cum_delta_session`.
4. `tick_imb_{10s,60s}` (upticks−downticks / total ticks); `trade_intensity` = ticks/s vs time-of-day baseline; `t_per_volume_bucket` (volume-clock feature) [S12][S13].
5. Depth/side totals L1–L5, `book_slope`, spread_bps, `ofi × (1/depth)` Kyle-lambda interaction [S1][S24].
6. Conditioning: `gex_sign` × `illiquidity` regime flag (momentum if GEX<0, reversal if GEX>0) [S22][S23]; time-of-day bucket.
7. Options flow: per strike `delta_hedge_flow = ΔOI × delta_of_strike × sign(ΔLTP?)` aggregated; `pcr_oi_delta`, `pcr_vol`, `opt_flow_imb_{1m,5m}` [S19][S20][S21].
8. Signal horizons: trust imbalance features for 10s–5min; expect decay by 15–30 min (NSE evidence [S15]); treat anything beyond 30 min as regime/context, not signal.

## Open questions
- Does tick-rule signing accuracy hold on NIFTY option ticks, which are thinner, wider-spread, and often stale-mid? Needs validation against any sample with aggressor flags (e.g., recorded L1 + trade prints).
- On NIFTY, do *futures* flow (signed futures volume/OFI) lead option prices, or do fast option quotes lead futures? Indian evidence (spot↔SF futures) shows futures lead cash by ~1 min; options-vs-futures lead-lag untested in our stack.
- Is aggregated option ΔOI at 3–10s REST cadence early enough to matter at 10s–60s scalping horizons, or only for 5–15 min context?
- What survives costs? NSE OIB strategies lose alpha after transaction costs [S17]; bot must model STT/exchange charges/brokerage + slippage (spread on far OTM strikes is huge) before trusting any imbalance edge.
- Dealer gamma sign for NIFTY weekly expiries: empirical sign distribution unknown; mass retail short-premium flow may invert typical US intuitions near expiry afternoons.
- Whether 5-level OFI integrated via PCA [S2] adds anything at 1-s retail tick resolution, vs being noise-limited by snapshot batching.
