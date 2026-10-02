# Pilot Database Design

## Purpose

The pilot stores three kinds of information:

1. What the market looked like.
2. What the model advised.
3. What happened after the advice.

```text
market_data
    ↓
model_advice
    ↓
trade_feedback
```

## Design principles

- Use three tables for the pilot.
- Use `advice_id` as the only generated ID. It connects advice to feedback.
- Store market data by time. A model invocation can use a range of market rows rather than one snapshot.
- Preserve the exact input sent to the model and its exact output.
- Do not include raw NIFTY futures price in the model input. If enabled later, the engine can supply the already-calculated `synthetic_fwd_basis` value.
- The model never selects the number of lots. Position size remains engine-owned.
- Trade feedback must not rewrite the original model advice.
- System-prompt changes are proposed from batches of completed trades, versioned, reviewed, and approved by a human. One trade must not automatically change the prompt.

## Table 1: `market_data`

One row represents the market at one point in time. The initial cadence is one row per minute.

| Column | Meaning |
|---|---|
| `time` | Time of the market observation, truncated to the minute in Asia/Kolkata |
| `nifty_price` | NIFTY index price from the `NSE_INDEX\|Nifty 50` quote |
| `india_vix` | India VIX value from the `NSE_INDEX\|India VIX` quote |
| `expiry_date` | Resolved nearest listed NIFTY expiry used for the option chain |
| `atm_strike` | At-the-money option strike nearest to `underlying_spot_price` |
| `atm_call_instrument_key` | Canonical instrument key of the ATM call |
| `atm_put_instrument_key` | Canonical instrument key of the ATM put |
| `atm_call_price` | ATM call option price from quote `last_price`, falling back to chain `ltp` |
| `atm_put_price` | ATM put option price from quote `last_price`, falling back to chain `ltp` |
| `iv_percentile` | Current implied-volatility percentile, calculated by the engine |
| `pcr` | Put-call ratio: total put OI divided by total call OI across the chain |
| `relative_volume` | Current volume compared with its normal level |
| `vwap_position` | NIFTY's position relative to VWAP |
| `opening_range_state` | Current opening-range state |
| `call_oi_wall` | Strike with the maximum call open interest in the chain |
| `put_oi_wall` | Strike with the maximum put open interest in the chain |
| `spread` | Worse of the ATM call/put proportional bid-ask spreads `(ask-bid)/midpoint`, from quote depth first then chain bid/ask; NULL unless both sides have a valid spread |
| `source_age_seconds` | Maximum age in seconds across required NIFTY, VIX, ATM call, and ATM put quotes, from `last_trade_time` epoch-ms with quote `timestamp` ISO fallback, clamped to zero |
| `chain_age_seconds` | Seconds since the last successful option-chain retrieval, clamped to zero |
| `data_is_stale` | Whether required market data is missing or too old |
| `trading_is_blocked` | Whether an engine safety rule blocks a new trade |
| `block_reason` | Why trading is blocked: `STALE_DATA`, `KILL_SWITCH`, or `SHADOW_MODE` |
| `bar_time` | Timestamp of the latest common completed 1-minute bar across the spot and future streams |
| `spot_bar_open` / `spot_bar_high` / `spot_bar_low` / `spot_bar_close` | OHLC of the latest completed NIFTY 1-minute bar |
| `future_bar_open` / `future_bar_high` / `future_bar_low` / `future_bar_close` / `future_bar_volume` | OHLCV of the latest completed futures 1-minute bar |
| `nifty_future_price` | Raw NIFTY futures quote price |
| `lot_size` | Contract lot size resolved dynamically from exchange instrument metadata for the ATM options |
| `session_state` | Session bucket: `PREOPEN`, `OPENING_RANGE`, `PRIME`, `MIDDAY`, `LATE`, `CAS`, or `CLOSED` |
| `is_expiry_day` | Whether the row date equals the resolved expiry date |
| `minutes_to_derivatives_close` | Whole minutes until the 15:40 derivatives close, clamped at zero |
| `synthetic_fwd_basis` | Median put-call-parity forward minus futures price across the ATM±1 strikes |
| `atm_iv` | Mean of valid ATM call/put implied volatilities in percentage units |
| `atm_expected_move` | Spot-scaled one-day expected move derived from `atm_iv` |
| `opening_straddle` | ATM call-plus-put mid captured during the 09:15–09:20 window |
| `expected_move_consumed_pct` | Share of the opening straddle consumed by the move since the 09:15 open |
| `realized_vol_10d` | Annualized realized volatility from recent daily log returns |
| `vrp_ratio` | `atm_iv` divided by `realized_vol_10d` when both are positive |
| `opening_range_high` / `opening_range_low` / `opening_range_width` | Completed 09:15–09:30 opening range levels |
| `narrow_range_threshold` | 20th percentile of recent daily true ranges used to classify narrow opens |
| `opening_range_is_narrow` | Whether the opening range width is below the narrow threshold |
| `relative_volume_spike` | Whether relative volume meets the spike threshold |
| `futures_vwap` | Explicit 1-minute-bar proxy VWAP of the futures contract |
| `vwap_sigma` | Current futures VWAP deviation in historical same-minute standard deviations |
| `first_30m_return_pct` | Percentage return over the first 30 completed minutes |
| `call_oi_walls` | JSON top-2 `[strike, oi]` call OI walls sorted by descending OI then ascending strike |
| `put_oi_walls` | JSON top-2 `[strike, oi]` put OI walls |
| `local_gex` | Aggregated near-ATM gamma exposure contribution |
| `local_gex_sign` | `POSITIVE`, `NEGATIVE`, `NEUTRAL`, or `UNAVAILABLE` |
| `momentum_reversion_selector` | `REVERSION_BIAS`, `MOMENTUM_BIAS`, or `NEUTRAL` context selector |
| `gate_reasons` | JSON array of deterministic risk-gate blockers applied to this row |
| `gate_warnings` | JSON array of non-blocking risk warnings |
| `shadow_candidate` | JSON serialized shadow trade candidate, or `null` when none was constructible |
| `bar_age_seconds` | Seconds since the last successful intraday-bar refresh |

Raw futures price and completed-bar OHLCV fields are stored for deterministic audit and replay; they are omitted from the model payload, which receives only derived values such as `synthetic_fwd_basis`. The JSON columns hold structured serialized state (OI-wall tuples, gate blocker/warning lists, and the shadow candidate) rather than free text. Missing values are always NULL, never zero.

Rows are keyed by `time`; the collector writes one row per minute and repeats a write for the same minute replaces it.

The collector can produce shadow advice rows after each market row via the opt-in `--enable-advisory` flag (disabled by default). All output is terminal-only and labelled `SHADOW ONLY - DO NOT EXECUTE`.

## Table 2: `model_advice`

One row represents one model invocation and its advice.

| Column | Meaning |
|---|---|
| `advice_id` | Unique receipt number for the advice |
| `advice_at` | Time the model produced the advice |
| `context_from` | Beginning of the market-data range given to the model |
| `context_to` | End of the market-data range given to the model |
| `prompt_version` | Version of the system prompt used |
| `model_name` | Model that produced the advice |
| `action` | `LONG_CALL`, `LONG_PUT`, or `NO_TRADE` |
| `confidence` | Model confidence |
| `setup_quality` | Setup grade: `A`, `B`, or `C` |
| `entry_price` | Suggested option entry price |
| `stop_price` | Suggested option stop price |
| `target_price` | Suggested option target price |
| `idea_fails_if` | Price condition that would prove the trade idea wrong |
| `data_conflict` | Whether the model found conflicting market evidence |
| `reason` | Short explanation for the advice |
| `exact_model_input` | Exact payload sent to the model |
| `exact_model_output` | Exact response returned by the model |
| `exact_model_output_raw` | Byte-exact raw model text, preserved even when malformed |

Raw malformed model text is preserved in `exact_model_output_raw` for legacy schema compatibility (older databases keep `exact_model_output` as JSON); the storage API always exposes the raw text as `exact_model_output`.

There is no `snapshot_id`. The `context_from` and `context_to` values identify the range of market rows considered by the model. `exact_model_input` preserves the final assembled input for replay and audit.

There is no `passed_validation` column. Technical checks for malformed output or invented values happen in application code and are separate from whether the trade later worked.

## Table 3: `trade_feedback`

Each row records one kind of result for one piece of advice: either the outcome the user actually reports (`evaluation_mode = 'USER'`) or the automatic 30-minute modeled shadow outcome (`evaluation_mode = 'SHADOW_30M'`). Rows are keyed by the pair `(advice_id, evaluation_mode)`, so one advice can truthfully hold both results — the modeled outcome never blocks the user's real fills, and recording the user's fills never blocks later settlement. Each row remains immutable once stored; a second result of the same kind for the same advice is rejected.

| Column | Meaning |
|---|---|
| `advice_id` | Advice being evaluated |
| `feedback_at` | Time the feedback was recorded |
| `trade_was_taken` | Whether the user acted on the advice |
| `entered_at` | Actual trade entry time |
| `exited_at` | Actual trade exit time |
| `actual_entry_price` | Actual option purchase price |
| `actual_exit_price` | Actual option sale price |
| `lots` | Number of lots actually traded |
| `user_verdict` | `WORKED`, `DID_NOT_WORK`, or `NOT_TAKEN` |
| `mae` | Worst price movement against the trade after entry |
| `mfe` | Best price movement in favor of the trade after entry |
| `user_notes` | User's explanation or observations |
| `evaluation_mode` | `USER` for manually recorded feedback, `SHADOW_30M` for automated 30-minute shadow settlement |
| `price_basis` | `ACTUAL_FILL` for real fills, `SHADOW_QUOTE_MODEL` for modeled option prices |
| `result_status` | `USER_RECORDED`, `NOT_TAKEN`, `STOP_HIT`, `TARGET_HIT`, `STOP_HIT_AMBIGUOUS`, `HORIZON_EXIT`, or `MISSING_DATA` |
| `lot_size` | Contract lot size used for the outcome |
| `quoted_spread` | Option bid/ask spread quoted at advice time |
| `excursion_source` | `OPTION_1M_LTP_PROXY`, `USER_PROVIDED`, or `UNAVAILABLE` |

For `SHADOW_30M` rows the `actual_entry_price`, `actual_exit_price`, `entered_at`, and `exited_at` columns hold modeled values rather than real fills — a legacy-schema naming compromise; `price_basis` and `excursion_source` always identify modeled data. Shadow excursions use 1-minute OHLC/LTP as an explicit proxy, never tick-mid accuracy. The proxy uses conservative event-bar accounting: an exit bar's intrabar extremes are never credited to MAE/MFE (the exit may precede them), a bar hitting both stop and target is recorded as `STOP_HIT_AMBIGUOUS` at the stop price, and only fully completed bars inside the horizon are eligible. Settlement failures (API errors or missing option candles) insert nothing — the advice stays pending and is retried on the next run.

All PnL and cost figures (`gross_pnl_inr`, `costs_inr`, `net_pnl_inr`) are derived at report time from prices, lots, lot size, and quoted spread — they are never stored.

The evaluation report computes a Deflated Sharpe Ratio over per-trade net PnL using the supplied `trial_count` (default 1; CLI `--trial-count`). DSR is a report-time statistic only; graduation requires at least 100 costed records, positive expectancy, DSR > 0.95, and a capture ratio of at least 0.70 (an unavailable capture ratio blocks graduation).

Calibrated stop/target levels activate only after at least 50 objectively winning, cost-complete outcomes exist for the candidate action (`calibrated_mae_p90` / `expected_mfe_per_unit` on `market_data`, and `level_source` `CALIBRATED_MAE_MFE` inside `shadow_candidate`). Below that threshold levels stay `PROVISIONAL_OR_WIDTH` and the row carries the tolerated `CALIBRATION_HISTORY_INSUFFICIENT` blocker. The 100-record threshold still governs graduation.

The theta gate is an explicit proxy: `theta_decay_per_unit = abs(theta) * 30 / 385` models 30 minutes of theta decay over the 385-minute F&O session, and `theta_required_underlying_move` compares that decay plus per-unit round-trip cost against the historical same-time-of-day median 30-minute NIFTY range (`tod_median_30m_range`). Missing inputs produce the tolerated `THETA_CLOCK_UNAVAILABLE` blocker; a required move larger than the median range produces the hard `THETA_CLOCK_BLOCK`.

Daily P&L is derived only from `USER` feedback rows whose trades were actually taken and exited on the current IST date; any USER row with incomplete cost inputs fails closed via `DAILY_PNL_UNAVAILABLE`. Shadow outcomes never count toward the daily loss limit.

When the collector runs with `--enable-advisory`, it auto-settles pending shadow advice after each row's advice step (advice always runs first to preserve the snapshot-age bound). `--no-auto-settle` opts out. Settlements are emitted as `shadow_settlement` JSON events or a `Settled shadow outcomes: N` text line with failures reported on stderr as `shadow_settlement_failure`.

The `market_data` table also persists `tod_median_30m_range`, `daily_net_pnl`, `daily_pnl_costed_trades`, `daily_pnl_uncosted_trades`, `expected_mfe_per_unit`, `calibration_sample_size`, and `calibrated_mae_p90` so each row is self-describing about the calibration and daily-PnL context used by its gates.

Prompt-analysis proposals are file artifacts under `data/prompt-proposals/` (one JSON per proposal), not database tables. They are always `PENDING_HUMAN_REVIEW` (or a failure audit) and are never applied automatically; the production prompt bytes are embedded for reference but never modified.

Agent-tool advice requests are file artifacts under `data/agent-requests/` (one JSON per request), not a fourth table. A `PENDING` request carries the snapshot and exact model input; `submit` validates the harness agent's raw output, persists a `model_advice` row with `source = 'shadow-harness'` and the agent name as `model_name`, and marks the artifact `SUBMITTED`. This path uses the model already running in the agent harness — no separate model API key. The standalone OpenAI adapter (`--enable-openai-advisory`, alias `--enable-advisory`; `trading_bot.advisory`) remains available but optional.

There is no separate generated result ID. A feedback row is identified by its `(advice_id, evaluation_mode)` pair: `advice_id` connects the result to its advice, and `evaluation_mode` distinguishes the user's actual result from the modeled shadow outcome. Within one `(advice_id, evaluation_mode)` pair at most one row exists.

Databases created before the composite key are migrated on open inside one transaction: all rows and every stored value are copied into a rebuilt table, and the old table name remains the only `trade_feedback` table afterward. Legacy rows with a NULL `evaluation_mode` are backfilled deterministically — taken trades and `WORKED`/`DID_NOT_WORK` verdicts become `USER`; untaken rows that carry modeled entry/MAE values become `SHADOW_30M`; bare `NOT_TAKEN` skips become `USER`. Because the old single-column key allowed at most one row per advice, the backfilled `(advice_id, evaluation_mode)` pairs cannot collide.

There is no `minutes_after` column. The holding duration can be calculated from `entered_at` and `exited_at`.

There is no stored `trading_cost` column. Costs can be calculated later from actual entry price, exit price, lots, and the versioned charge configuration. Cost-inclusive results are still required when evaluating whether the strategy is profitable.

MAE and MFE belong here rather than in `market_data` because they are only known after the trade has happened.

## Prompt-improvement loop

```text
Market data accumulates
    ↓
The model receives a recent range and produces advice
    ↓
The user takes or skips the trade
    ↓
The user records whether it worked and what happened
    ↓
An analysis agent reviews a batch of completed trades
    ↓
The agent proposes a versioned system-prompt change
    ↓
A human approves or rejects the proposed change
```

The analysis agent must use both the user's verdict and the objective trade data. It must not update the system prompt automatically after an individual trade.


## Separate live execution journal (03-Oct-2026)

The pilot/advisory DuckDB schema above remains unchanged. Explicit live execution
uses `data/live/state.sqlite3` and `data/live/inbox`, never `paper.duckdb` or the
paper inbox. Agent decisions still persist in the existing `agent_decision` table
through `agent_brain`; live boundaries/lot proposals are recorded before execution.

SQLite tables:

- `live_meta(key PRIMARY KEY, value)`: immutable account identity and starting allocation binding.
- `live_trade(decision_id PRIMARY KEY, state JSON text)`: contract, prices, entry/sell tags and IDs, monotonic confirmed quantities, broker snapshots, pending write intent, status, sticky halt, realized fills/charges/net P&L. CLOSED records cannot be rewritten.
- `live_event(id PRIMARY KEY, decision_id, event JSON text)`: append-only state-transition snapshots. Credentials/headers are never stored. Identical snapshots do not create duplicate events.

FULL-synchronous transactions commit intents before broker mutations. Exclusive
runner locking prevents concurrent controllers of one journal. Broker order tags
identify crash-recovery placements but are not server-side idempotency keys;
uncertain unmatched writes cannot be retried automatically. No assumed fills enter
the capital ledger. Closed P&L is derived from actual `/trades` and broker charges
calculation for executed orders and stored immutably for allocation recovery.
Starting allocation plus completed net P&L controls profit reuse, bounded by broker
cash/commitments; missing fills/costs fail closed. See `docs/kite-live.md` for the
DAY-order and contract-note reconciliation limitations.
