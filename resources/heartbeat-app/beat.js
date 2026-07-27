#!/usr/bin/env node
/* ============================================================================
   beat.js — tiny CLI heartbeat sender. Zero dependencies, Node >= 18.

   Someone in the classroom runs this once and leaves it running:

     node beat.js http://teamcoding.ro:5798 --id ana --every 5

   Arguments (all optional except the server URL):
     <url>          server base or full /heartbeat URL   (env HEARTBEAT_URL)
     --id NAME      client name shown on the dashboard   (env HEARTBEAT_ID,
                    default: <user>@<hostname>)
     --every SECS   seconds between beats, default 5     (env HEARTBEAT_EVERY)

   It never exits on network errors — every attempt is printed with a
   second-precision timestamp so the console itself is a connectivity log.
   Stop with Ctrl+C (prints a summary).
   ============================================================================ */
'use strict';

const os = require('node:os');

/* ---- parse config --------------------------------------------------------- */
const args = process.argv.slice(2);
const cfg = {
  url: process.env.HEARTBEAT_URL || '',
  id: process.env.HEARTBEAT_ID || '',
  every: Number(process.env.HEARTBEAT_EVERY || 5),
};
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--id') cfg.id = args[++i] || cfg.id;
  else if (a === '--every') cfg.every = Number(args[++i] || cfg.every);
  else if (a === '--url') cfg.url = args[++i] || cfg.url;
  else if (a === '--help' || a === '-h') { usage(); process.exit(0); }
  else if (!a.startsWith('--') && !cfg.url) cfg.url = a;
}

function usage() {
  console.log('usage: node beat.js <server-url> [--id NAME] [--every SECONDS]');
  console.log('  e.g. node beat.js http://teamcoding.ro:5798 --id ana --every 5');
}

if (!cfg.url) { usage(); process.exit(1); }
if (!/^https?:\/\//i.test(cfg.url)) cfg.url = 'http://' + cfg.url;
if (!/\/heartbeat\b/.test(cfg.url)) cfg.url = cfg.url.replace(/\/+$/, '') + '/heartbeat';
if (!cfg.id) {
  let user = 'user';
  try { user = os.userInfo().username; } catch { /* keep default */ }
  cfg.id = `${user}@${os.hostname()}`;
}
cfg.id = String(cfg.id).slice(0, 40).replace(/[^\w.\-@]/g, '_');
cfg.every = Math.max(1, Number.isFinite(cfg.every) ? cfg.every : 5);

const target = cfg.url + (cfg.url.includes('?') ? '&' : '?') + 'id=' + encodeURIComponent(cfg.id);

/* ---- the loop ------------------------------------------------------------- */
let sent = 0, ok = 0, fail = 0;
const started = Date.now();

function pad(n) { return (n < 10 ? '0' : '') + n; }
function stamp() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
         `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

async function tick() {
  sent++;
  const n = sent;
  const t0 = Date.now();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), Math.min(4000, cfg.every * 900));
  try {
    const res = await fetch(target, { signal: ctrl.signal });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    await res.json().catch(() => ({}));
    ok++;
    console.log(`${stamp()}  OK    #${n}  (${Date.now() - t0} ms)`);
  } catch (e) {
    fail++;
    const reason = e && e.name === 'AbortError' ? 'timeout' : (e && e.message) || 'network error';
    console.log(`${stamp()}  FAIL  #${n}  ${reason}`);
  } finally {
    clearTimeout(timer);
    setTimeout(tick, cfg.every * 1000);
  }
}

console.log(`[beat] target : ${target}`);
console.log(`[beat] id     : ${cfg.id}`);
console.log(`[beat] every  : ${cfg.every}s   (Ctrl+C to stop)`);
tick();

process.on('SIGINT', () => {
  const mins = ((Date.now() - started) / 60000).toFixed(1);
  console.log(`\n[beat] stopped after ${mins} min — sent ${sent}, delivered ${ok}, failed ${fail}`);
  process.exit(0);
});
