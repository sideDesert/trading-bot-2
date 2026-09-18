# R06: Technical-indicator efficacy for intraday index scalping (NIFTY focus) — what has real evidence and what's folklore

Compiled 2026-09-16 for the NIFTY options intraday-scalping advisory bot project. Tier legend: A = peer-reviewed journal/top working paper, B = serious quasi-academic or practitioner replication with methodology, C = practitioner blog/indie backtest with stated rules and numbers (use as priors, not proof).

## Sources

| # | Title | Authors/Org | Year | Tier | URL | One-line claim |
|---|-------|-------------|------|------|-----|----------------|
| 1 | Market Intraday Momentum | Gao, Han, Li, Zhou — J. of Financial Economics | 2018 | A | https://doi.org/10.1016/j.jfineco.2018.05.009 | First 30-min return predicts last 30-min return (R²≈1.6%, economically significant) on SPY 1993–2013; stronger on high-vol/news days |
| 2 | Time Series Momentum | Moskowitz, Ooi, Pedersen — JFE | 2012 | A | https://doi.org/10.1016/j.jfineco.2011.11.003 | 1–12 month trend exists in all 58 futures markets; persistence then reversal; trend is a real anomaly at *multi-week* horizons |
| 3 | Does intraday technical analysis in the U.S. equity market have value? | Marshall, Cahan & Cahan — J. of Empirical Finance | 2008 | A | https://www.sciencedirect.com/science/article/abs/pii/S0927539807000588 | NONE of 7,846 popular intraday TA rules profitable once data-snooping bias corrected |
| 4 | Predictive ability of technical trading rules: developed and emerging equity markets | Springer, Financial Markets & Portfolio Mgmt | 2023 | A | https://link.springer.com/article/10.1007/s11408-023-00433-2 | 6,406 rules, 41 markets: outperformance not persistent, "markets turn unpredictable in last years"; only 5/23 developed-market rule-sets survive 20bp costs |
| 5 | Technical trading revisited: false discoveries, persistence and transaction costs | Bajgrowicz & Scaillet — JFE | 2012 | A | https://access.archive-ouverte.unige.ch/access/metadata/d1a36296-e8c4-423b-9ed9-9870cfc76d9c/download | Even in-sample technical-rule performance on DJIA 1897–2011 "completely offset by low transaction costs"; best rules not selectable ex ante |
| 6 | Can Day Trading Really Be Profitable? (ORB on QQQ) | Zarattini & Aziz — SSRN 4416622 | 2023/25 | B | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622 | 5-min ORB on QQQ 2016–23: annualized alpha 33% net of commissions; TQQQ version +1,484% vs QQQ +169% |
| 7 | A Profitable Day Trading Strategy for the U.S. Equity Market | Zarattini, Barbon, Aziz — SSRN 4729284 / SFI 24-98 | 2024 | B | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284 | 5-min ORB on 7,000 US stocks: profitable net ONLY when restricted to "stocks in play" (news/activity filter); top-20 portfolio Sharpe 2.81, alpha 36% |
| 8 | ORB Trading Strategy: What Replication Shows | Papers with Backtest | 2026 | B | https://paperswithbacktest.com/strategies/orb-trading-strategy | Independent replication of [6]: full-sample Sharpe −0.06 (in-sample 0.16, post-pub −0.84 over ~11 mo) — headline claim not reproduced |
| 9 | Is the Opening Range Breakout Dead? 16 Years of Nasdaq Data | EdgeLab | 2026 | C | https://edgelabtrading.com/blog/opening-range-breakout-nasdaq/ | Naive ORB is dead (in-sample Sharpe −0.27, PF 1.06); filtered variant (opening-bar direction + 200-DMA + tight stop) OOS Sharpe 0.84 but fading 2 yrs |
| 10 | Best Intraday Breakout Strategy for Nifty 50 (8+ Year Backtest) | Intraday Lab | 2026 | C | https://intradaylab.com/blog/nifty-orb-breakout-strategy-backtest | 30-min ORB, 2:1 R:R, 2,122 trades, 2017–2026: +91.6% total, 48.7% WR, PF 1.23, Sharpe 1.16, MDD −11.2% |
| 11 | What Happens After Nifty's First 15-Minute Candle? | Intraday Lab | 2026 | C | https://intradaylab.com/blog/nifty-first-15-minute-candle-analysis | 2,148 Nifty sessions: 71–76% of days break first-candle range, only ~52% sustain — "statistically indistinguishable from a coin flip"; edge needs filters |
| 12 | All About Opening Range Breakout — Part 1 (NIFTY test) | Zerodha, "The Long and the Short" | 2026 | B | https://inthemoneybyzerodha.substack.com/p/all-about-opening-range-breakout | NIFTY ORB 2019–Feb 2026 (no costs): 9:15–11:15 window outperforms all others; long-side WR ~60%, short ~50%; early-day breakouts carry the edge |
| 13 | ORB backtest on Nifty futures, 4 exit variants | DailyBulls | 2025 | C | https://dailybulls.in/orb-intraday-trading-strategy-backtest/ | Small sample (42 trades, Jul–Oct 2025): 1.5×ATR stop variant LOST (−0.16%); OR-low/ATR-trail (+1.09%); tight stops destroy ORB |
| 14 | Opening Range Breakout — A Century of Evidence | Toby Crabel (substack/book) | 2025 | B | https://tobycrabel.substack.com/p/opening-range-breakout-a-century | 84 futures markets, 1923–2025: baseline stretch breakout "works, and has for a century" but edge "thinned"; payoff depends on contraction→expansion regime |
| 15 | Supertrend: 200,000+ trade backtest on Nifty 500 | Share.Market (PhonePe) | ~2025 | C | https://www.share.market/buzz/insights/i-backtested-200000-trades-using-the-supertrend-indicator-here-is-what-actually-works/ | Daily, 2012–2025: WR remarkably flat 40.7–43.2% across ALL (period,multiplier); edge is win-size asymmetry (avg win 8.5%→25.5% as multiplier 1→3), not accuracy |
| 16 | Back-Testing Super Trend in 15-min TF on top-5 Nifty stocks | Inspira Journals | 2025 | C | https://inspirajournals.com/uploads/Issues/871152129.pdf | 15-min supertrend on RIL/HDFC/ICICI/INFY/Airtel Feb 2019–Feb 2025 incl. slippage/costs; profitable in trending conditions, whipsawed sideways (low-quality venue — treat as indicative) |
| 17 | Supertrend strategy backtest (3 versions, Nifty/BankNifty/stocks) | DailyBulls | ~2025 | C | https://dailybulls.in/supertrend-strategy-backtest/ | Daily TF long-only: weekly-filter + 2.5 ATR trail best — 127 trades, 44.9% WR, PF 2.40, MDD −22.4%; plain flip version MDD −39.9% |
| 18 | VWAP Intraday Strategy — Do Simple Trading Strategies Really Work? Part 4 | Marketcalls (OpenAlgo, Rajandran R) | 2019 | B | https://www.marketcalls.in/amibroker/vwap-intraday-trading-strategy-do-simple-trading-strategies-really-work-part4.html | Nifty fut 15-min VWAP-cross 2011–2019: profitable BEFORE costs, a LOSER after realistic commissions+slippage; BankNifty loser even before costs. Classic negative result |
| 19 | Mean Reversion backtest on Nifty intraday VWAP | Intraday Lab | ~2025 | C | https://intradaylab.com/blog/mean-reversion-nifty-backtest | 12 mo, 5-min: price >1σ from VWAP reverts ~68% of time (68–84% band); VWAP-most-useful reference because institutional flow benchmarks to it |
| 20 | Net market returns of moving-average crossover systems (synthesis) | Mental Momentum research | ~2024 | C | https://research.mental-momentum.ai/r/net-market-returns-moving-average-40z4hc | Isolated MA crossovers on single assets "generally fail to beat buy-and-hold after transaction costs"; only diversified vol-scaled multi-asset portfolios show positive net returns |
| 21 | EMA crossover strategy: 6 assets backtested | Quant-Signals | ~2025 | C | https://quant-signals.com/ema-crossover-strategy/ | EMA cross positive expectancy only on D1 (e.g., BTC +0.33R); H1 timeframe mostly negative (GBPUSD H1 −0.071R, EURUSD H1 −0.036R) — intraday crossover edge drowns in noise |
| 22 | Does Connors' RSI(2) mean-reversion actually work? | Quant for Free | 2025 | C | https://quant4free.com/analysis/rsi2-mean-reversion/ | S&P 1500 stocks, 8,261 trades, 2015–26: 63.1% WR but PF 0.99, CAGR −0.7%, MDD −57.3% net of 10bp/side — "the win rate is real; the profit is not" |
| 23 | Can Day Trading Really Be Profitable? + Stocks-in-Play critique context: post-publication decay | QuantPedia, "How do strategies perform after publication" (McLean & Pontiff cited) | n.d. | B | https://quantpedia.com/how-do-investment-strategies-perform-after-publication/ | Published anomalies lose 26% of return out-of-sample and 58% in 5 yrs post-publication — apply a decay haircut to any published edge incl. ORB |
| 24 | Intraday price reversals in US stock index futures: 15-year study | Miller et al. lineage / J. Banking & Finance | 2005 | A | https://www.sciencedirect.com/science/article/abs/pii/S0378426604000949 | Highly significant intraday reversal after large open moves (1987–2002, stronger after up-moves), BUT significance "sharply reduced" after bid-ask cost proxy |
| 25 | Order-flow realism: tick-rule CVD error test | intrepidkarthi/orderbook research | ~2025 | C | https://github.com/intrepidkarthi/orderbook/blob/main/docs/research/order-flow.md | Tick rule is 94.5% accurate per trade yet CVD error averages 169% of true magnitude — sign can be wrong; retail CVD approximations are unreliable without aggressor flags |
| 26 | Predicting intraday price movements with CNN-LSTM, Indian markets | IJRPR | 2026 | C | https://ijrpr.com/uploads/V7ISSUE4/IJRPR62371.pdf | CNN-LSTM on NSE tick data + RSI/MACD/BB/VWAP features claims 93.8% directional accuracy — implausible; classic overfit/leakage pattern typical of low-tier Indian ML journals |
| 27 | XGBoost feature engineering for NIFTY intraday (83 features) | Shakti Tiwari, DEV Community | 2025 | C | https://dev.to/shaktitiwari/nifty-intraday-backtest-vwap-breakout-strategy-with-xgboost-signals-367g | Practitioner: VWAP-breakout filter via XGBoost cut trades 63% (342→127), WR 48.2%→67.3%, Sharpe 0.82→1.94 — i.e., ML's value is trade FILTERING not direction prediction |

## Findings

**Opening Range Breakout (best-combined evidence)**
- Strong peer-review-adjacent result: 5-min ORB on QQQ 2016–23 produced 33% annualized alpha net of commissions [S6]; on 7,000 US stocks the edge essentially only existed in "stocks in play" — high-activity/news stocks — where a top-20 portfolio made >1,600% cum., Sharpe 2.81 [S7]. Unfiltered ORB was much weaker; the FILTER is the edge [S7].
- Independent replication on 16 y of index data does NOT reproduce the headline: full-sample Sharpe −0.06, post-publication −0.84 (short window caveat noted by replicators) [S8]. EdgeLab: naive both-sides 5-min ORB on NQ is dead (Sharpe −0.27); a heavily filtered variant reached OOS Sharpe 0.84 but is fading [S9].
- Classic lineage: Crabel's century-scale test (84 markets, 1923–2025) finds a real but "thinned" edge driven by volatility regime (NR4/contraction preceding expansion) [S14].
- NIFTY-specific: 30-min ORB with fixed 2:1 R:R over 8+ y: PF 1.23, Sharpe 1.16, 48.7% WR, MDD −11.2% — modest positive but barely above the Indian cost hurdle once STT/slippage included [S10]. Zerodha's cost-free test shows the edge concentrates in the 9:15–11:15 window and on the long side (~60% WR vs ~50% short) [S12].
- Naive first-candle ORB on NIFTY ≈ coin flip: ~52% of first-15-min-candle breakouts sustain [S11]. Tight stops kill ORB variants (−0.16% with 1.5×ATR stop in a 42-trade test) [S13].

**VWAP / AVWAP**
- Direct Indian test of a popular retail 15-min VWAP-cross system on Nifty futures 2011–2019: marginally profitable gross, NEGATIVE after realistic costs; BankNifty negative even gross [S18]. This is the honest retail-folklore answer: VWAP-cross alone is not an edge.
- VWAP as *reference level* has more support: price stretched >1σ from VWAP reverted ~68% of the time (12-mo Nifty 5-min test) [S19]; the mechanism (institutional execution benchmarking) is economically plausible, unlike most retail indicators.
- Institutional/practitioner consensus: VWAP works as context/filter (above/below regime, band-extreme reversion on low-VIX range days), not as a standalone entry trigger [S18, S19, S27].

**Supertrend**
- 200k-trade Nifty-500 daily study: win rate stuck at 40.7–43.2% regardless of parameters — the "edge" is purely payoff asymmetry (trend-following right tail), and ONLY the multiplier matters materially [S15]. Daily-timeframe Indian tests with filters: PF 2.23–2.40 but MDD −22% to −40% [S17].
- The only 15-min Indian study found (in a low-tier journal) reports profitability only in trending conditions with whipsaw losses in sideways markets [S16]. Honest assessment: supertrend is a re-parameterized ATR trailing stop; it inherits generic trend-following properties — no evidence it adds anything over simpler constructs, and intraday whipsaw + Indian transaction costs are likely fatal for scalping use [S15, S16, S17].

**EMA crossovers / intraday momentum signals on 1–15-min**
- Cross-asset: EMA crossover positive expectancy only on daily; negative on H1 for 3 of 6 assets tested [S20, S21]. Synthesis of the literature: single-asset MA crossovers fail after costs, period [S20].
- Academic verdict on intraday TA broadly: Marshall et al. tested 7,846 intraday rules — none survive data-snooping correction [S3]; Bajgrowicz–Scaillet find even in-sample DJIA rule profits "completely offset by low transaction costs" [S5]; 41-market study finds predictability collapsing over time and dying at 20bp costs [S4]. GRAVEYARD CONFIRMED by academia for raw intraday TA rules.
- BUT genuine intraday time-series momentum exists at specific horizons: first-30-min return predicts last-30-min return (JFE) [S1] — an institutional-crowding story (rebalancing flow), not a chart-pattern story. Classic 1–12-month time-series momentum [S2] is a real anomaly but at horizons useless for scalping.

**RSI intraday**
- No credible peer-reviewed support for RSI as an intraday entry on indices. Honest teardown of the famous RSI(2) mean-reversion system: 63.1% win rate, still loses money net (PF 0.99, CAGR −0.7%) because mean-reversion losers are huge [S22]. Win rate is a marketing statistic; expectancy is the metric.
- Practitioner consensus from these tests: RSI usable at most as an extreme-reading filter/exit heuristic, never standalone.

**Volume-price action / cumulative delta**
- Order-flow primitives (delta/CVD) are conceptually sound but measurement-fragile: tick-rule classification hits ~94.5% per-trade accuracy yet cumulative CVD error averages 169% of series magnitude — the sign can be wrong; without true aggressor flags from the exchange feed, retail CVD approximations are unreliable [S25]. NSE feeds lack aggressor identification, so NIFTY "delta" tools inherit this problem.
- Relative-volume spikes (volume > 1.5× average) do appear as a useful filter in practitioner ML systems for NIFTY VWAP breakouts [S27].

**ML vs TA comparisons (NIFTY intraday)**
- Low-tier Indian journals claim 93.8% CNN-LSTM directional accuracy [S26] — treat as leakage/overfit artifacts; consistent with the known graveyard of lookahead-biased intraday ML papers.
- More credible practitioner result: ML's demonstrated value is as a signal FILTER on top of price structure (XGBoost filtering VWAP breakouts: trades −63%, WR 48→67%, Sharpe 0.82→1.94) [S27]. Same lesson as ORB studies: filters/context > raw triggers.

**Academic architecture of the intraday problem**
- Intraday markets are closer to efficient than daily/monthly; published anomalies decay ~26% OOS and 58% over 5 y post-publication [S23]; Indian market added structural headwinds (STT hike on options, tighter spreads) since ~2019–2024, shortening edge half-lives [S12's caveat, S23].
- Mean reversion vs momentum on intraday: opening-move overreaction/reversal is real but thin after costs [S24]; first-hour momentum into close is real [S1]; mid-day chop reverts to VWAP [S19]. Net: regime-dependent — trend edges at open (expansion) and close, mean-reversion edges mid-session around VWAP.

## Indicator scorecard

| Indicator | Evidence grade (A–F) | Best timeframe / context | Source(s) |
|---|---|---|---|
| ORB with filters (vol-contraction, stocks/day-type "in play", no tiny-range days) | B+ | 5–60-min range, first 2 hours of session | S6, S7, S10, S12, S14 |
| First-30/60-min momentum (directional bias from open) | A− | First 30 min → bias for last 30 min / rest of day | S1, S12 |
| VWAP as context/band reversion | B− | 5–15-min; mean-revert extremes >1–2σ on range days | S19, S27 |
| Relative-volume spike filter | B− | Any intraday; confirms breakouts | S7, S27 |
| Supertrend | D+ | Only daily TF shows trend edge (stocks); no honest intraday index win after costs | S15, S16, S17 |
| EMA crossovers (1/3/5/15-min) | F | None — negative after costs intraday; positive only D1 | S3, S5, S20, S21 |
| RSI(2)/RSI intraday entries | D− | None net of costs; okay only as exit/extreme filter | S22, S3 |
| CVD/delta from inferred tick data | D | Any — measurement error defeats signal without true aggressor flags | S25 |
| Naive first-candle breakout (no filters) | F | None — coin flip | S11 |
| ML direction-prediction (high claimed accuracy) | F | Lookahead-bias graveyard | S26 |
| ML as signal filter over price-structure features | C+ | 5–15-min; cuts trades, raises Sharpe | S27 |

## Implications for our bot (ranked implementation priority)

1. **ORB engine with regime filters** — implement opening-range detection (5/15/30/60-min windows), skip days with compressed ranges (analog of NR4 / tiny OR), skip non-"in-play" days (low premarket news/activity, low relative volume). Strongest combined evidence [S6, S7, S10, S12, S14].
2. **First-hour momentum state** — compute first-30/60-min return as a session-direction prior fed to the LLM snapshot; documented institutional-flow mechanism [S1].
3. **VWAP context features** — distance-from-VWAP in σ, above/below regime, 1σ/2σ band touches; use for mean-reversion bias on range days and pullback context on trend days; NOT as a standalone crossover trigger [S19, S18, S27].
4. **Relative-volume / volume-spike metric** — cheap, robust filter [S7, S27].
5. **Session-clock regime tags** — trend allowed near open & final hour; mean-reversion bias mid-day [S1, S12, S24, S19].
6. **Explicitly DO NOT implement as signal generators**: EMA crossovers on ≤15-min, supertrend flips, RSI threshold entries, naive first-candle breakouts. If the LLM prompt mentions them, label as retail-folklore context, not advice [S3, S5, S11, S15, S20, S21, S22].
7. **CVD/delta only if** the data feed provides true buy/sell aggressor classification; otherwise skip entirely [S25].
8. **Cost floor in the deterministic engine** — model STT+slippage per options trade and reject any signal family whose documented gross edge is < ~2–3× the all-in round-trip cost; multiple studies show intraday edges die at 10–20bp [S4, S5, S18].
9. **Decay monitoring** — track per-signal rolling win rate/PF live; expect published-edge decay of ~26% OOS [S23]; a fading ORB was already observed post-2023 [S9, S14].

## Open questions

- Does the JFE first-30-min→last-30-min intraday momentum result replicate on NIFTY specifically (only US/ETF markets tested)? Needs internal backtest before trusting [S1].
- What is the Indian-options-specific all-in cost per scalp (STT hike 2024, stamp duty, exchange tx, spread/impact on liquid strikes), and which documented gross edges clear it? R04/R05 presumably cover.
- NIFTY ORB: does the 9:15–11:15-window edge Zerodha found survive costs, and does the long-side α (60% vs 50% WR) persist post-2024 STT changes? [S12]
- Day-type classification for NIFTY (trend day vs range day) from first-hour data — is there an Indian study? None found; candidate for internal research using OR-range percentile vs ATR.
- AVWAP (anchored to gap-open/event) on NIFTY: no rigorous tests found at all — evidence gap; treat as unvalidated visualization aid.
- How much of Zarattini's "stocks in play" concept maps to "index in play" days (RBI policy, election, expiry, global macro) for NIFTY — a categorical high-activity-day filter seems transferable but untested [S7].
