'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../trading_bot/web_assets/dashboard.js'), 'utf8');
const settle = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve;
  const promise = new Promise(complete => { resolve = complete; });
  return {promise, resolve};
}
function dashboardState(paused) {
  return {demo:false, paused, resume_block_reason:null, connection:{status:'CONNECTED'}, login_ready:true,
    capital:{available_for_new_trade_inr:10000, allocation_inr:10000, realized_net_pnl_inr:0, broker_cash_inr:10000, committed_inr:0},
    daily_pnl:0, runner:{status:'NOT_RUNNING'}, open_trades:[], positions:[], orders:[], completed:[], generated_at:'2026-10-03T10:00:00+05:30'};
}
const response = payload => ({status:200, ok:true, json:async () => payload});
function openDashboard() {
  const elements = new Map();
  const requests = [];
  const timers = [];
  function element() {
    return {textContent:'', disabled:false, classList:{toggle(){},add(){}}, replaceChildren(){}, append(){},
      addEventListener(event, listener) { this[event] = listener; }};
  }
  const document = {querySelector:() => ({content:'test-csrf'}), createElement:element,
    getElementById(id) { if (!elements.has(id)) elements.set(id,element()); return elements.get(id); }};
  vm.runInNewContext(source, {document, Intl, Date, URLSearchParams, Boolean,
    window:{location:{assign(){}},setTimeout(callback){timers.push(callback);}},
    fetch(url, options) { const pending = deferred(); requests.push({url,options,...pending}); return pending.promise; }});
  return {elements, requests, timers};
}

test('delayed pre-pause poll cannot revert acknowledged pause', async () => {
  const dashboard = openDashboard();
  const button = dashboard.elements.get('entry-control');
  const click = button.click();
  assert.equal(dashboard.requests[1].url,'/pause');
  dashboard.requests[1].resolve(response({paused:true}));
  await click;
  assert.equal(button.textContent,'Resume new trades');
  dashboard.requests[0].resolve(response(dashboardState(false)));
  await settle();
  assert.equal(button.textContent,'Resume new trades');
  assert.equal(dashboard.timers.length,1);
});

test('delayed pre-resume poll cannot revert acknowledged resume', async () => {
  const dashboard = openDashboard();
  dashboard.requests[0].resolve(response(dashboardState(true)));
  await settle();
  dashboard.timers.shift()();
  const button = dashboard.elements.get('entry-control');
  const click = button.click();
  assert.equal(dashboard.requests[2].url,'/resume');
  dashboard.requests[2].resolve(response({paused:false}));
  await click;
  assert.equal(button.textContent,'Stop new trades');
  dashboard.requests[1].resolve(response(dashboardState(true)));
  await settle();
  assert.equal(button.textContent,'Stop new trades');
  assert.equal(button.disabled,false);
});
