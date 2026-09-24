import html
import json
from dataclasses import asdict
from datetime import datetime

_FIELDS = (
    "decision_id", "created_at", "status", "action", "strike", "lots", "quantity",
    "limit_entry", "stop_price", "target_price", "entry_at", "entry_fill", "exit_at",
    "exit_fill", "exit_reason", "gross_pnl", "charges", "charges_source", "net_pnl",
    "tradingsymbol", "notes",
)


def _row(trade) -> dict:
    data = asdict(trade)
    data["quantity"] = trade.quantity
    return {k: data.get(k) for k in _FIELDS}


def render_dashboard(trades, generated_at: datetime, banner: "str | None" = None) -> str:
    payload = json.dumps(
        {"trades": [_row(t) for t in trades], "generated": generated_at.strftime("%d %b %Y, %H:%M IST")}
    ).replace("</", "<\\/")
    banner_html = f'<div class="banner">{html.escape(banner)}</div>' if banner else ""
    return _TEMPLATE.replace("__DATA__", payload).replace("__BANNER__", banner_html)


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paper Trading Dashboard</title>
<style>
:root {
  color-scheme: light;
  --surface-0: #f4f3f0; --surface-1: #fcfcfb; --border: #e4e2dd; --grid: #e9e8e4;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #7a7974;
  --profit: #2a78d6; --loss: #e34948; --wash: rgba(42,120,214,0.10);
  --good: #0ca30c; --critical: #d03b3b; --banner: #fff4d6; --banner-ink: #5c4300;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface-0: #111110; --surface-1: #1a1a19; --border: #2e2e2b; --grid: #2a2a27;
    --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #8f8e86;
    --profit: #3987e5; --loss: #e66767; --wash: rgba(57,135,229,0.12);
    --banner: #3a2f10; --banner-ink: #f5d98a;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0: #111110; --surface-1: #1a1a19; --border: #2e2e2b; --grid: #2a2a27;
  --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #8f8e86;
  --profit: #3987e5; --loss: #e66767; --wash: rgba(57,135,229,0.12);
  --banner: #3a2f10; --banner-ink: #f5d98a;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface-0); color: var(--text-primary);
  font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
header { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; }
h1 { font-size: 20px; margin: 0; font-weight: 600; }
h2 { font-size: 15px; margin: 0 0 2px; font-weight: 600; }
.sub { color: var(--text-secondary); font-size: 13px; }
.muted { color: var(--text-muted); }
.banner { background: var(--banner); color: var(--banner-ink); border-radius: 8px; padding: 8px 12px; margin: 16px 0 0; font-weight: 500; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.hero { margin-top: 16px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
.hero .value { font-size: 52px; font-weight: 600; letter-spacing: -0.02em; line-height: 1; }
.chip { display: inline-flex; gap: 6px; align-items: center; padding: 4px 10px; border-radius: 999px;
  border: 1px solid var(--border); font-size: 13px; color: var(--text-secondary); }
.chip .dot { width: 8px; height: 8px; border-radius: 50%; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 16px; }
.tile .label { color: var(--text-secondary); font-size: 13px; }
.tile .value { font-size: 22px; font-weight: 600; margin-top: 2px; }
.charts { display: grid; grid-template-columns: 3fr 2fr; gap: 12px; margin-top: 12px; }
@media (max-width: 760px) { .charts { grid-template-columns: 1fr; } .hero .value { font-size: 44px; } }
.chart { position: relative; margin-top: 12px; }
.chart svg { display: block; width: 100%; overflow: visible; }
.axis text { fill: var(--text-muted); font-size: 11px; }
.gridline { stroke: var(--grid); stroke-width: 1; }
.zero { stroke: var(--text-muted); stroke-width: 1; }
.tooltip { position: absolute; pointer-events: none; background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px 10px; font-size: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  white-space: nowrap; opacity: 0; transition: opacity 80ms; z-index: 2; }
.tooltip b { font-weight: 600; }
.key { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
.legend { display: flex; gap: 14px; font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
.tablecard { margin-top: 12px; }
.tablehead { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.tablewrap { overflow-x: auto; margin-top: 12px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { color: var(--text-secondary); font-weight: 500; font-size: 12px; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
tr.dim td { color: var(--text-muted); }
.pnl { display: inline-flex; align-items: center; gap: 6px; }
.pnl .dot { width: 8px; height: 8px; border-radius: 50%; }
label.toggle { font-size: 13px; color: var(--text-secondary); display: inline-flex; gap: 6px; align-items: center; cursor: pointer; }
.empty { padding: 40px 0; text-align: center; color: var(--text-muted); }
.footer { margin-top: 16px; font-size: 12px; color: var(--text-muted); }
</style>
</head>
<body>
<main>
  <header>
    <h1>Paper trading dashboard</h1>
    <span class="sub" id="generated"></span>
  </header>
  __BANNER__
  <div id="app"></div>
  <p class="footer">Paper trades only. No real order was placed. Net P&amp;L is after Zerodha charges.</p>
</main>
<script>
const DATA = __DATA__;
const $ = (s, el = document) => el.querySelector(s);
const inr = v => (v < 0 ? "−₹" : "₹") + Math.abs(Math.round(v)).toLocaleString("en-IN");
const signed = v => (v > 0 ? "+" : "") + inr(v);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const side = a => a === "LONG_CALL" ? "Call" : "Put";
const reasonText = r => ({TARGET_HIT:"Target hit", STOP_HIT:"Stop hit", SQUARE_OFF:"15:20 square-off",
  ENTRY_NOT_FILLED:"Entry not filled", DECISION_TOO_OLD:"Decision too old", LATE_ENTRY_CUTOFF:"After 15:15",
  ANOTHER_POSITION_ACTIVE:"Another position open", DAILY_LOSS_LIMIT:"Daily loss limit", RISK_BUDGET_TOO_SMALL:"Risk too large",
  LOT_SIZE_UNKNOWN:"Lot size unknown"}[r] || r || "");

$("#generated").textContent = "Updated " + DATA.generated;
const all = DATA.trades;
const closed = all.filter(t => t.status === "CLOSED" && t.net_pnl != null)
  .sort((a, b) => (a.exit_at || "").localeCompare(b.exit_at || ""));
const app = $("#app");

if (!closed.length) {
  app.innerHTML = `<div class="card" style="margin-top:16px"><div class="empty">No closed paper trades yet.<br>
    Run <code>python -m trading_bot.paper run</code> during market hours, then rebuild this page.</div></div>`;
} else {
  const net = closed.reduce((s, t) => s + t.net_pnl, 0);
  const gross = closed.reduce((s, t) => s + t.gross_pnl, 0);
  const charges = closed.reduce((s, t) => s + t.charges, 0);
  const wins = closed.filter(t => t.net_pnl > 0), losses = closed.filter(t => t.net_pnl <= 0);
  const avg = xs => xs.length ? xs.reduce((s, t) => s + t.net_pnl, 0) / xs.length : null;
  const open = all.filter(t => t.status === "OPEN" || t.status === "PENDING_ENTRY").length;
  const up = net >= 0;

  app.innerHTML = `
  <section class="card hero">
    <div>
      <div class="sub">Net P&amp;L, all paper trades</div>
      <div class="value">${signed(net)}</div>
    </div>
    <span class="chip"><span class="dot" style="background:var(${up ? "--good" : "--critical"})"></span>${up ? "▲ In profit" : "▼ In loss"} after ${inr(charges)} charges</span>
    ${open ? `<span class="chip">${open} open or pending, not counted</span>` : ""}
  </section>
  <section class="tiles">
    ${tile("Closed trades", closed.length)}
    ${tile("Win rate", Math.round(100 * wins.length / closed.length) + "%", `${wins.length} won · ${losses.length} lost`)}
    ${tile("Gross P&L", signed(gross))}
    ${tile("Average win", wins.length ? signed(avg(wins)) : "—")}
    ${tile("Average loss", losses.length ? signed(avg(losses)) : "—")}
    ${tile("Best / worst", signed(Math.max(...closed.map(t => t.net_pnl))), "worst " + signed(Math.min(...closed.map(t => t.net_pnl))))}
  </section>
  <section class="charts">
    <div class="card"><h2>Cumulative net P&amp;L</h2><div class="sub">After each closed trade</div>
      <div class="chart" id="equity"><div class="tooltip"></div></div></div>
    <div class="card"><h2>Net P&amp;L by day</h2>
      <div class="legend"><span><span class="key" style="background:var(--profit)"></span>Profit day</span>
        <span><span class="key" style="background:var(--loss)"></span>Loss day</span></div>
      <div class="chart" id="daily"><div class="tooltip"></div></div></div>
  </section>
  <section class="card tablecard">
    <div class="tablehead"><h2>All paper trades</h2>
      <label class="toggle"><input type="checkbox" id="showAll"> Show skipped and cancelled</label></div>
    <div class="tablewrap"><table><thead><tr>
      <th>Date</th><th>Option</th><th class="num">Lots</th><th class="num">Bought</th><th class="num">Sold</th>
      <th>Exit</th><th class="num">Charges</th><th class="num">Net P&amp;L</th></tr></thead><tbody id="rows"></tbody></table></div>
  </section>`;

  const renderRows = () => {
    const showAll = $("#showAll").checked;
    const rows = all.filter(t => showAll || !["SKIPPED", "CANCELLED"].includes(t.status))
      .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
    $("#rows").innerHTML = rows.map(t => {
      const dim = t.status !== "CLOSED" && t.status !== "OPEN";
      const d = new Date(t.created_at);
      const when = d.toLocaleDateString("en-IN", {day: "2-digit", month: "short"}) + " " + (t.created_at || "").slice(11, 16);
      const pnl = t.net_pnl == null ? `<span class="muted">${t.status === "OPEN" ? "open" : "—"}</span>` :
        `<span class="pnl"><span class="dot" style="background:var(${t.net_pnl >= 0 ? "--profit" : "--loss"})"></span>${signed(t.net_pnl)}</span>`;
      return `<tr class="${dim ? "dim" : ""}"><td>${esc(when)}</td>
        <td>NIFTY ${esc(t.strike)} ${side(t.action)}</td>
        <td class="num">${t.lots ?? "—"}</td>
        <td class="num">${t.entry_fill != null ? "₹" + t.entry_fill.toFixed(2) : "—"}</td>
        <td class="num">${t.exit_fill != null ? "₹" + t.exit_fill.toFixed(2) : "—"}</td>
        <td>${esc(t.status === "OPEN" ? "Open" : t.status === "PENDING_ENTRY" ? "Waiting to fill" : reasonText(t.exit_reason))}</td>
        <td class="num">${t.charges != null ? inr(t.charges) : "—"}</td>
        <td class="num">${pnl}</td></tr>`;
    }).join("");
  };
  $("#showAll").addEventListener("change", renderRows);
  renderRows();

  const draw = () => { drawEquity(closed); drawDaily(closed); };
  draw();
  let timer; addEventListener("resize", () => { clearTimeout(timer); timer = setTimeout(draw, 100); });
}

function tile(label, value, note) {
  return `<div class="card tile"><div class="label">${label}</div><div class="value">${value}</div>${note ? `<div class="sub">${note}</div>` : ""}</div>`;
}

function niceTicks(min, max, count = 4) {
  const span = max - min || 1;
  const raw = span / count, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw);
  const ticks = [];
  for (let v = Math.floor(min / step) * step; v <= max + 1e-9; v += step) ticks.push(Math.round(v));
  return ticks;
}

function compact(v) {
  const a = Math.abs(v), s = v < 0 ? "−" : "";
  return s + "₹" + (a >= 100000 ? (a / 100000).toFixed(a % 100000 ? 1 : 0) + "L" : a >= 1000 ? (a / 1000).toFixed(a % 1000 ? 1 : 0) + "K" : a);
}

function frame(el, height) {
  const w = el.clientWidth, m = {t: 8, r: 12, b: 24, l: 52};
  return {w, h: height, m, iw: w - m.l - m.r, ih: height - m.t - m.b};
}

function yAxis(f, ticks, y) {
  return ticks.map(v => `<line class="${v === 0 ? "zero" : "gridline"}" x1="${f.m.l}" x2="${f.w - f.m.r}" y1="${y(v)}" y2="${y(v)}"/>
    <text x="${f.m.l - 8}" y="${y(v) + 4}" text-anchor="end">${compact(v)}</text>`).join("");
}

function drawEquity(trades) {
  const el = $("#equity"), tip = $(".tooltip", el);
  el.querySelector("svg")?.remove();
  const f = frame(el, 240);
  let run = 0;
  const pts = [{v: 0, t: null}, ...trades.map(t => ({v: (run += t.net_pnl), t}))];
  const lo = Math.min(0, ...pts.map(p => p.v)), hi = Math.max(0, ...pts.map(p => p.v));
  const ticks = niceTicks(lo, hi);
  const y0 = Math.min(ticks[0], lo), y1 = Math.max(ticks[ticks.length - 1], hi);
  const x = i => f.m.l + (pts.length === 1 ? 0 : i * f.iw / (pts.length - 1));
  const y = v => f.m.t + (y1 - v) / (y1 - y0 || 1) * f.ih;
  const line = pts.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.v)}`).join("");
  const area = `${line}L${x(pts.length - 1)},${y(0)}L${x(0)},${y(0)}Z`;
  const last = pts[pts.length - 1];
  el.insertAdjacentHTML("afterbegin", `<svg viewBox="0 0 ${f.w} ${f.h}" height="${f.h}" role="img" aria-label="Cumulative net profit and loss over ${trades.length} trades, ending at ${signed(last.v)}">
    <g class="axis">${yAxis(f, ticks, y)}
      <text x="${f.m.l}" y="${f.h - 6}">Start</text><text x="${f.w - f.m.r}" y="${f.h - 6}" text-anchor="end">Trade ${trades.length}</text></g>
    <path d="${area}" fill="var(--wash)"/>
    <path d="${line}" fill="none" stroke="var(--profit)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    <line id="cross" y1="${f.m.t}" y2="${f.m.t + f.ih}" stroke="var(--text-muted)" stroke-width="1" opacity="0"/>
    <circle id="hoverDot" r="5" fill="var(--profit)" stroke="var(--surface-1)" stroke-width="2" opacity="0"/>
    <circle cx="${x(pts.length - 1)}" cy="${y(last.v)}" r="5" fill="var(--profit)" stroke="var(--surface-1)" stroke-width="2"/>
    <rect x="${f.m.l}" y="0" width="${f.iw}" height="${f.h}" fill="transparent" id="hit"/>
  </svg>`);
  const svg = $("svg", el), cross = $("#cross", svg), dot = $("#hoverDot", svg);
  const show = i => {
    const p = pts[i];
    cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i)); cross.setAttribute("opacity", 1);
    dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(p.v)); dot.setAttribute("opacity", 1);
    tip.innerHTML = p.t ? `<b>Trade ${i}</b> · ${esc(p.t.created_at.slice(0, 10))}<br>NIFTY ${esc(p.t.strike)} ${side(p.t.action)} · ${esc(reasonText(p.t.exit_reason))}<br>
      This trade <b>${signed(p.t.net_pnl)}</b><br>Running total <b>${signed(p.v)}</b>` : "<b>Start</b><br>₹0";
    tip.style.opacity = 1;
    const tx = Math.min(Math.max(x(i) + 12, 0), f.w - tip.offsetWidth);
    tip.style.left = (x(i) + 12 + tip.offsetWidth > f.w ? x(i) - 12 - tip.offsetWidth : tx) + "px";
    tip.style.top = Math.max(0, y(p.v) - tip.offsetHeight - 8) + "px";
  };
  $("#hit", svg).addEventListener("pointermove", e => {
    const r = svg.getBoundingClientRect();
    const i = Math.round((e.clientX - r.left - f.m.l) / (f.iw / Math.max(1, pts.length - 1)));
    show(Math.max(0, Math.min(pts.length - 1, i)));
  });
  $("#hit", svg).addEventListener("pointerleave", () => { tip.style.opacity = 0; cross.setAttribute("opacity", 0); dot.setAttribute("opacity", 0); });
}

function drawDaily(trades) {
  const el = $("#daily"), tip = $(".tooltip", el);
  el.querySelector("svg")?.remove();
  const byDay = {};
  trades.forEach(t => { const d = t.created_at.slice(0, 10); (byDay[d] ||= []).push(t.net_pnl); });
  const days = Object.keys(byDay).sort().map(d => ({d, v: byDay[d].reduce((s, x) => s + x, 0), n: byDay[d].length}));
  const f = frame(el, 216);
  const lo = Math.min(0, ...days.map(d => d.v)), hi = Math.max(0, ...days.map(d => d.v));
  const ticks = niceTicks(lo, hi);
  const y0 = Math.min(ticks[0], lo), y1 = Math.max(ticks[ticks.length - 1], hi);
  const y = v => f.m.t + (y1 - v) / (y1 - y0 || 1) * f.ih;
  const band = f.iw / days.length, bw = Math.max(4, Math.min(24, band - 2));
  const bar = (cx, v) => {
    const top = y(Math.max(v, 0)), bot = y(Math.min(v, 0)), h = Math.max(1, bot - top), r = Math.min(4, h, bw / 2);
    const l = cx - bw / 2, rr = cx + bw / 2;
    return v >= 0
      ? `M${l},${bot}V${top + r}Q${l},${top} ${l + r},${top}H${rr - r}Q${rr},${top} ${rr},${top + r}V${bot}Z`
      : `M${l},${top}V${bot - r}Q${l},${bot} ${l + r},${bot}H${rr - r}Q${rr},${bot} ${rr},${bot - r}V${top}Z`;
  };
  const label = d => new Date(d + "T00:00:00").toLocaleDateString("en-IN", {day: "2-digit", month: "short"});
  const every = Math.ceil(days.length / Math.max(1, Math.floor(f.iw / 56)));
  el.insertAdjacentHTML("afterbegin", `<svg viewBox="0 0 ${f.w} ${f.h}" height="${f.h}" role="img" aria-label="Net profit and loss by day for ${days.length} days">
    <g class="axis">${yAxis(f, ticks, y)}
      ${days.map((d, i) => i % every ? "" : `<text x="${f.m.l + band * (i + 0.5)}" y="${f.h - 6}" text-anchor="middle">${label(d.d)}</text>`).join("")}</g>
    ${days.map((d, i) => `<g class="bar" data-i="${i}"><rect x="${f.m.l + band * i}" y="${f.m.t}" width="${band}" height="${f.ih}" fill="transparent"/>
      <path d="${bar(f.m.l + band * (i + 0.5), d.v)}" fill="var(${d.v >= 0 ? "--profit" : "--loss"})"/></g>`).join("")}
  </svg>`);
  el.querySelectorAll(".bar").forEach(g => {
    g.addEventListener("pointerenter", () => {
      const d = days[+g.dataset.i], cx = f.m.l + band * (+g.dataset.i + 0.5);
      g.querySelector("path").style.opacity = 0.8;
      tip.innerHTML = `<b>${label(d.d)}</b><br>${d.n} trade${d.n > 1 ? "s" : ""}<br>Net <b>${signed(d.v)}</b>`;
      tip.style.opacity = 1;
      tip.style.left = Math.min(Math.max(0, cx - tip.offsetWidth / 2), f.w - tip.offsetWidth) + "px";
      tip.style.top = Math.max(0, y(Math.max(d.v, 0)) - tip.offsetHeight - 8) + "px";
    });
    g.addEventListener("pointerleave", () => { g.querySelector("path").style.opacity = 1; tip.style.opacity = 0; });
  });
}
</script>
</body>
</html>
"""
