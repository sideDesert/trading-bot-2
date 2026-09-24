---
name: nifty-agent-advice
description: Make a NIFTY options paper-trade decision where the AGENT does all the analysis — not Python. Python only supplies raw market data, computed analytics, and prior decisions; you read them, may web-search for macro/event context, then decide LONG_CALL / LONG_PUT / NO_TRADE and the levels yourself. Use when the user asks for a NIFTY setup in this agent-driven harness, or invokes /nifty-agent-advice.
allowed-tools: Read, Bash, WebSearch
---

# NIFTY Agent-Driven Paper-Trade Decision

You own the decision. The Python engine here makes NO trade call and applies NO
gates — it only gathers facts. You analyze them and decide. The whole system is
shadow-only: never place, imply, or suggest a real order. Every market statement
ends with `SHADOW ONLY - DO NOT EXECUTE`.

## Procedure

0. Before deciding, check the paper book:

   ```bash
   .venv/bin/python -m trading_bot.paper status
   ```

   If a trade is `PENDING_ENTRY` or `OPEN`, do not add a new idea (the engine
   will skip it). If the day's net is at or below -₹20,000, stop for the day.

1. Gather the context brief (raw data + analytics + history):

   ```bash
   .venv/bin/python -m trading_bot.agent_brain context
   ```

   Read the one JSON object. Key sections:
   - `meta` — time (IST), NIFTY spot/future, India VIX, session state, expiry, staleness.
   - `analytics` — the full computed indicator set: opening range (high/low/width/state/narrow), relative volume, VWAP position/sigma, IV percentile, ATM IV, expected move, realized vol, VRP, PCR, OI walls, GEX, time-of-day median range, spread. **These are facts, not a verdict.**
   - `options` — ATM strike, call/put instrument keys, ATM option prices, lot size, and the `chain_window` rows.
   - `price_action.spot_1m_csv` — recent 1-minute NIFTY bars.
   - `history.recent_decisions` — your prior calls, to stay consistent and avoid contradicting a still-valid earlier view.

   If `status` is `NO_MARKET_DATA`, say so plainly and stop. If `fetch_status`
   is not `OK`, the numbers may be stale — weigh that and say so.

2. Optionally web-search for anything that changes the read *today*: NIFTY/India
   market news, global cues (US markets, crude, USDINR), scheduled events (RBI,
   Fed, expiry, major results, budget). Keep it tight — a couple of focused
   searches, not a survey. Record any source URLs you rely on.

3. Decide, using your own judgment over the analytics + price action + context:
   - Is there a genuine, tradeable edge right now? Consider trend/breakout vs
     chop, volume confirmation, volatility regime (IV percentile, VRP), time of
     day and time-to-expiry decay, and event risk.
   - If yes: pick `LONG_CALL` or `LONG_PUT`, a `strike` and its `instrument_key`
     from the chain (default to ATM unless you justify otherwise), and set
     `entry_price`, `stop_price`, `target_price` yourself such that
     `stop < entry < target`. Prices are yours to choose from the option data —
     you are not echoing a Python candidate here.
   - If not: `NO_TRADE` with all three prices omitted.
   - Set `confidence` (0–1) and `setup_quality` (A/B/C) honestly.

4. Record your decision (this writes history for the learning loop; it never
   trades):

   For a trade:

   ```bash
   .venv/bin/python -m trading_bot.agent_brain record \
     --action LONG_CALL \
     --strike <STRIKE> --instrument-key <KEY> \
     --entry-price <PRICE> --stop-price <PRICE> --target-price <PRICE> \
     --confidence <0-1> --setup-quality <A|B|C> \
     --nifty-spot <SPOT> \
     --context-ts <meta.ts_ist> \
     --source "<url you used, repeatable>" \
     --rationale "<short, specific why in plain English>"
   ```

   For no trade:

   ```bash
   .venv/bin/python -m trading_bot.agent_brain record \
     --action NO_TRADE --confidence <0-1> --setup-quality <A|B|C> \
     --context-ts <meta.ts_ist> \
     --rationale "<why there is no edge right now>"
   ```

   On `RECORDED`, note the `decision_id`. For a trade the response includes
   `paper_order_queued: true`: the paper engine (`python -m trading_bot.paper run`,
   started by the user in its own terminal) picks it up, places a simulated limit
   buy at `entry_price` valid for 10 minutes, then exits at stop, target, or the
   15:20 square-off using live bid/ask.


## User output

For a call (use `BUY A PUT` / `PUT` for a put):

```text
AGENT PAPER TRADE
Time: <meta.ts_ist>
Decision: BUY A CALL
Option: NIFTY <strike> CALL
Buy price: ₹<entry_price>
Stop price: ₹<stop_price>
Sell target: ₹<target_price>
Risk: ₹<(entry_price - stop_price) × lot_size> per lot
Confidence: <confidence> · Setup: <setup_quality>
Why: <your reasoning in simple English>
Paper trade only. Do not place a real order.
SHADOW ONLY - DO NOT EXECUTE
```

For no trade:

```text
AGENT PAPER TRADE
Time: <meta.ts_ist>
Decision: DO NOT BUY
Why: <your reasoning in simple English>
Paper trade only. Do not place a real order.
SHADOW ONLY - DO NOT EXECUTE
```

## Risk

- Per-trade risk budget is ₹10,000, halved to ₹5,000 when India VIX > 16. The
  paper engine sizes lots = floor(budget / ((entry - stop) × lot size)); if one
  lot's risk exceeds the budget, the paper trade is skipped.
- Stop after ₹20,000 of paper loss in a day (the engine enforces this). No more
  trades until tomorrow.
- Skip the trade if the bid-ask spread is over 2% of mid, or if the strike is
  more than 3% from spot.
- No new entries at or after 15:15 IST. One open idea at a time.
- Always state the per-lot risk in ₹ alongside the levels so the user sees the
  money at risk before deciding.

## Boundaries

- The decision and every level are yours; Python neither chose nor blocked a trade.
- Do not invent analytics that are not in the brief; if you need external facts, web-search and cite them.
- Never place a real order or imply one exists. The paper engine only simulates
  fills; its Kite client is limited in code to margin/charge calculation and
  instrument lookup, and refuses every `/orders` or `/gtt` endpoint.
- Keep it shadow-only, always.
