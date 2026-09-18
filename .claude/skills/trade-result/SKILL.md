---
name: trade-result
description: Record what actually happened after a NIFTY paper-trade decision — the user's buy/sell prices, lots, and result, or that the trade was skipped. Use when the user says things like "I bought at 120 and sold at 150, one lot", "I entered at 120 and got stopped at 110", "I skipped that trade", or otherwise reports the outcome of an earlier advisory, or invokes /trade-result.
allowed-tools: Read, Bash
---

# Record a NIFTY Trade Result

The user is reporting what they actually did with an earlier shadow advisory. Record it deterministically with no calculated, invented, or rounded numbers of your own. This flow only writes history for the learning loop; it never places or implies orders, and every related market statement stays `SHADOW ONLY - DO NOT EXECUTE`.

## Steps

1. Find candidate advice:

   ```bash
   .venv/bin/python -m trading_bot.feedback recent-advice
   ```

   One JSON object lists recent advice. Each entry carries the engine's `action`, `entry_price`, `stop_price`, `target_price`, `advice_at` (IST), and a `feedback` map showing which result kinds are already stored (`USER` and/or `SHADOW_30M`, each absent when not recorded yet).

2. Pick the matching advice:
   - Default: the most recent entry whose `action` is `LONG_CALL` or `LONG_PUT`.
   - If the user names a time, direction (call/put), or price level, match that entry instead.
   - If no entry fits, say so plainly and stop. Never guess an `advice_id`.

3. Interpret the report in plain language:
   - Traded and exited ("bought 120, sold 150", "entered 120, stopped at 110") → `record-trade`.
   - Traded but still holding → do not store a partial row. Tell the user to come back with the exit price and time; keep the entry details only in the conversation.
   - Deliberately skipped ("I passed", "didn't take it") → `record-not-taken`.

4. Collect the required fields:
   - `entry-price`, `exit-price`: exactly the user's numbers. Never recalculate or round them.
   - `lots`: "one lot" → `1`, "two lots" → `2`, etc. If the user did not say, ask.
   - `entered-at`, `exited-at`: required. If the user gave times, use them (today's session in IST; ISO 8601 like `2026-09-18T10:12:00+05:30`). "A few minutes ago" or "just now" means the current IST time, stated by the user in context — use it. If no times were given at all, ask.
   - `verdict`: take the user's own words — "it worked" → `WORKED`, "it didn't" → `DID_NOT_WORK`. If unstated, use `WORKED` when the exit price is above the entry price and `DID_NOT_WORK` when below; if the prices are equal or the direction is unclear, ask.
   - Ask at most one short combined question covering every field that is genuinely missing. Batch them; do not drip-feed questions.

5. Check what is already stored for the picked advice:
   - `feedback.USER` present → a personal result already exists. Show the stored entry/exit/lots/verdict from the payload, say that earlier result is kept as-is, and stop. Never overwrite or delete.
   - `feedback.SHADOW_30M` present → mention that the automatic 30-minute modeled outcome exists and stays untouched; your recording is stored alongside it.

6. Record a taken trade (values exactly as collected):

   ```bash
   .venv/bin/python -m trading_bot.feedback record-trade \
     --advice-id <ADVICE_ID> \
     --entered-at <ISO_TIMESTAMP> \
     --exited-at <ISO_TIMESTAMP> \
     --entry-price <PRICE> \
     --exit-price <PRICE> \
     --lots <LOTS> \
     --verdict <WORKED_OR_DID_NOT_WORK> \
     --notes "<one short user quote, if it adds context>"
   ```

   Or a skipped advice:

   ```bash
   .venv/bin/python -m trading_bot.feedback record-not-taken \
     --advice-id <ADVICE_ID> --notes "<why, if the user said>"
   ```

7. Report back in simple buy/sell language:
   - On `ok: true` from `record-trade`, echo the tool's `derived` block verbatim — `gross_pnl_inr`, `costs_inr`, `net_pnl_inr` — as "before costs / costs / after costs". Never compute money, points, or percentages yourself.
   - On `ok: true` from `record-not-taken`, confirm the skip is recorded.
   - Mention whether an automatic modeled outcome also exists for this advice, and that both results are now on file separately.

## Failure handling

- `USER feedback already recorded` → follow step 5's stored-result path. Do not retry with changed values.
- `unknown advice_id` → re-run `recent-advice`; if it still does not appear, tell the user no matching advice is on file and stop.
- `user trade requires a LONG_CALL or LONG_PUT advice` → the matched advice was a `NO_TRADE`; a real trade cannot be attached to it. Say so and stop.
- Other validation errors (times, prices, lots, verdict) → fix only the named field; if the user's own report is inconsistent (for example exit time before entry time), ask them to clarify rather than adjusting it yourself.
- Database or environment failures → report the plain error without exposing paths, tokens, or `.env` contents, and leave the recording for a later attempt.

## Boundaries

- Record only what the user reports; never infer fills from market data.
- Never modify, overwrite, or delete stored rows. One `USER` row and one `SHADOW_30M` row per advice is the whole storage contract here.
- Never suggest that recording a result affects live trading; the entire system remains shadow-only.
