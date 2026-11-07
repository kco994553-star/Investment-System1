'use strict';
// Development engine route of the sector QGV screen (Main, owner 2026-11-06 「섹터 QGV 실제 연결」; not a test, not deployed).
// start() runs tools/sector_qgv_engine_bridge.py (Codex's common engine #505, synthetic inputs only) as one child process and
// returns {route, call, calls, close}:
//  - route(bodyText) answers the development site's POST `sector-qgv-engine` (web_app_test_site.js `posts`): the request line
//    goes to the bridge unchanged and its one answer line comes back as JSON; `calls` records each request's op / request_id /
//    input_id / answer code (never a value) so a test can see that every preview was a real engine call;
//  - hold(n) makes the next n answers wait until release() (a test's late-answer case), so a later request can overtake.
// Answers are matched to requests in order (the bridge answers one line per line, in order). Nothing is written to disk.
const path = require('node:path');
const { spawn } = require('node:child_process');
const { ROOT } = require('./web_app_reuse');

const BRIDGE = path.join(ROOT, 'implementation/tools/sector_qgv_engine_bridge.py');
const ROUTE = 'sector-qgv-engine';

function start({ python = 'python3' } = {}) {
  const child = spawn(python, [BRIDGE], { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } });
  const waiting = [], calls = [], stderr = [];
  let buf = '', held = 0, holds = [], dead = null;
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', (d) => {
    buf += d;
    for (let i = buf.indexOf('\n'); i >= 0; i = buf.indexOf('\n')) {
      const line = buf.slice(0, i); buf = buf.slice(i + 1);
      const w = waiting.shift(); if (w) w.resolve(line);
    }
  });
  child.stderr.on('data', (d) => stderr.push(String(d)));
  child.on('exit', (code) => { dead = code; for (const w of waiting.splice(0)) w.reject(Error('BRIDGE_EXITED')); });
  function call(text) {
    if (dead !== null) return Promise.reject(Error('BRIDGE_EXITED'));
    const line = String(text).replace(/\n/g, ' ');
    return new Promise((resolve, reject) => { waiting.push({ resolve, reject }); child.stdin.write(line + '\n'); });
  }
  const record = (req, json) => calls.push({ op: req && req.op, request_id: req && req.request_id, input_id: req && req.input_id, ok: json.ok, code: json.code || null });
  async function route(bodyText) {
    let req = null; try { req = JSON.parse(bodyText); } catch (_) { /* the bridge answers REQUEST_NOT_JSON */ }
    const line = await call(bodyText), json = JSON.parse(line);
    record(req, json);
    if (held > 0) { held--; await new Promise((r) => holds.push(r)); }
    return { status: 200, json };
  }
  return {
    ROUTE, route, call: async (obj) => { const json = JSON.parse(await call(JSON.stringify(obj))); record(obj, json); return json; }, calls, stderr,
    hold(n = 1) { held += n; }, release() { const h = holds; holds = []; for (const r of h) r(); },
    async close() { if (dead === null) { child.stdin.end(); await new Promise((r) => child.once('exit', r)); } },
  };
}

module.exports = { start, ROUTE, BRIDGE };
