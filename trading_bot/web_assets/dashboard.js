"use strict";
let newTradesPaused = false;
let entryControlPending = false;
let entryControlRevision = 0;
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const formatRupees = amount => amount == null ? "—" : new Intl.NumberFormat("en-IN", {style:"currency", currency:"INR", maximumFractionDigits:0}).format(amount);
const setText = (elementId, value) => { document.getElementById(elementId).textContent = value; };
function showProfit(elementId, value) {
  const element = document.getElementById(elementId);
  element.textContent = formatRupees(value);
  element.classList.toggle("positive", value > 0);
  element.classList.toggle("negative", value < 0);
}
function showRows(elementId, records, emptyMessage, describe) {
  const container = document.getElementById(elementId);
  container.replaceChildren();
  if (!records.length) {
    const message = document.createElement("p"); message.className = "empty"; message.textContent = emptyMessage; container.append(message); return;
  }
  for (const record of records) {
    const rowDetails = describe(record);
    const row = document.createElement("div"); row.className = "row";
    const rowDescription = document.createElement("div");
    const title = document.createElement("div"); title.className = "row-title"; title.textContent = rowDetails.title;
    const description = document.createElement("p"); description.className = "muted"; description.textContent = rowDetails.description;
    const value = document.createElement("div"); value.className = "row-value"; value.textContent = rowDetails.value;
    if (rowDetails.profit != null) value.classList.add(rowDetails.profit >= 0 ? "positive" : "negative");
    rowDescription.append(title, description); row.append(rowDescription,value); container.append(row);
  }
}
async function refreshDashboard() {
  const requestedControlRevision = entryControlRevision;
  try {
    const response = await fetch("/api/state", {cache:"no-store", credentials:"same-origin"});
    if (response.status === 401) { window.location.assign("/login"); return; }
    if (!response.ok) throw new Error("State unavailable");
    const dashboardState = await response.json();
    if (entryControlPending || requestedControlRevision !== entryControlRevision) return;
    const connected = dashboardState.connection.status === "CONNECTED";
    setText("connection-status", dashboardState.demo ? "Preview · no account connected" : connected ? "Kite connected" : dashboardState.connection.status === "STALE" ? "Kite status needs refresh" : "Daily Kite login required");
    document.getElementById("connection-status").classList.toggle("connected", connected);
    setText("connection-detail", connected ? "Verified by the broker. Daily login stays on Zerodha." : "Connect securely on Zerodha’s website.");
    document.getElementById("kite-login").disabled = !dashboardState.login_ready || dashboardState.demo;
    setText("available", formatRupees(dashboardState.capital.available_for_new_trade_inr));
    setText("allocation", formatRupees(dashboardState.capital.allocation_inr));
    showProfit("total-pnl",dashboardState.capital.realized_net_pnl_inr); showProfit("daily-pnl",dashboardState.daily_pnl);
    setText("budget-detail", dashboardState.capital.available_for_new_trade_inr == null ? "Available cash is unverified. Trading budget is unavailable." : `Broker cash ${formatRupees(dashboardState.capital.broker_cash_inr)} · committed ${formatRupees(dashboardState.capital.committed_inr)}. Loss and lot caps still apply.`);
    const halted = dashboardState.open_trades.some(trade => trade.halted);
    setText("notice", dashboardState.demo ? "DEMO PREVIEW. No account calls, real trades or working controls." : halted ? "Attention required. Inspect Kite orders and positions before continuing." : dashboardState.paused ? "New trades are paused. Existing stops and exits keep running." : "₹10,000 starting allocation. Only completed net profits or losses change it.");
    setText("trading-status", dashboardState.paused ? "New trades paused" : "New trades control");
    setText("control-detail", `Runner: ${dashboardState.runner.status.toLowerCase().replaceAll("_"," ")}. Pausing does not sell an open position.`);
    newTradesPaused = dashboardState.paused;
    const entryControlButton = document.getElementById("entry-control");
    entryControlButton.disabled = entryControlPending || dashboardState.demo || (newTradesPaused && Boolean(dashboardState.resume_block_reason));
    entryControlButton.textContent = newTradesPaused ? "Resume new trades" : "Stop new trades";
    entryControlButton.classList.toggle("stop", !newTradesPaused);
    if (newTradesPaused && dashboardState.resume_block_reason) setText("control-detail",dashboardState.resume_block_reason);
    setText("position-count",dashboardState.positions.length); setText("order-count",dashboardState.orders.length);
    showRows("positions",dashboardState.positions,connected ? "No broker-confirmed open positions." : "Positions unavailable until Kite verifies.",position=>({title:position.tradingsymbol,description:`${position.product} · ${position.quantity} units`,value:formatRupees(position.pnl),profit:position.pnl}));
    // A pending fill/protection state can exist before the broker position snapshot refreshes.
    if (dashboardState.open_trades.length) {
      const detail = document.createElement("p"); detail.className = "muted";
      detail.textContent = dashboardState.open_trades.map(trade=>`${trade.symbol}: ${trade.status.replaceAll("_"," ")} · ${trade.bought-trade.sold} confirmed units · stop ${formatRupees(trade.stop)}`).join(" | ");
      document.getElementById("positions").append(detail);
    }
    showRows("orders",dashboardState.orders,connected ? "No working broker orders." : "Orders unavailable until Kite verifies.",order=>({title:order.tradingsymbol,description:`${order.transaction_type} ${order.order_type} · ${order.status}`,value:`${order.filled_quantity || 0} / ${order.quantity} units`}));
    showRows("completed",dashboardState.completed,"Completed live trades will appear here.",trade=>({title:trade.symbol,description:`${trade.closed_at ? new Date(trade.closed_at).toLocaleString("en-IN",{timeZone:"Asia/Kolkata"}) : "Closed"} · charges ${formatRupees(trade.charges)}`,value:formatRupees(trade.net_pnl),profit:trade.net_pnl}));
    setText("refreshed",`Page refreshed ${new Date(dashboardState.generated_at).toLocaleTimeString("en-IN",{timeZone:"Asia/Kolkata"})} IST · broker checked ${dashboardState.connection.verified_at ? new Date(dashboardState.connection.verified_at).toLocaleTimeString("en-IN",{timeZone:"Asia/Kolkata"})+" IST" : "not yet"}.`);
  } catch (error) { setText("notice","Dashboard connection lost. Displayed facts may be old; check Kite directly."); }
  finally { window.setTimeout(refreshDashboard,5000); }
}
document.getElementById("entry-control").addEventListener("click", async () => {
  const button = document.getElementById("entry-control"); button.disabled = true;
  entryControlPending = true;
  entryControlRevision += 1;
  const requestedPause = !newTradesPaused;
  try {
    const response = await fetch(requestedPause ? "/pause" : "/resume", {method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams({csrf:csrfToken})});
    if (!response.ok) {
      setText("notice",response.status === 409 ? "Resume blocked. Resolve the stop request or execution halt first." : "Control change could not be confirmed. Try again.");
      return;
    }
    newTradesPaused = (await response.json()).paused;
    setText("trading-status",newTradesPaused ? "New trades paused" : "New trades control");
    setText("notice",newTradesPaused ? "New trades paused. Existing stops and exits keep running." : "Entry pause removed. This does not start the runner; all trading checks still apply.");
    button.textContent=newTradesPaused ? "Resume new trades" : "Stop new trades";
    button.classList.toggle("stop",!newTradesPaused);
  } catch (error) { setText("notice","Control change could not be confirmed. Refresh to check its state."); }
  finally { entryControlRevision += 1; entryControlPending = false; button.disabled = false; }
});
refreshDashboard();
