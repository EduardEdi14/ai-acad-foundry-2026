#!/usr/bin/env node
/* ============================================================================
   Classroom Heartbeat — zero-dependency Node server.

   Students (or beat.js, or a browser tab on /poll) hit GET /heartbeat every
   few seconds; every hit is appended to a JSON-lines log and kept in memory.
   /ui serves a live dashboard that renders the beats as a timeline where
   connection gaps are impossible to miss, with second-precision timestamps.

   Run:        node server.js            (or: npm run dev)
   Configure:  PORT=5798 EXPECTED_INTERVAL_S=5 node server.js
   ============================================================================ */
'use strict';

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const PORT = Number(process.env.PORT || 5798);
const HOST = process.env.HOST || '0.0.0.0';
const EXPECTED_INTERVAL_S = Math.max(1, Number(process.env.EXPECTED_INTERVAL_S || 5));
const LOG_FILE = process.env.LOG_FILE || path.join(__dirname, 'heartbeat-log.jsonl');
const MAX_MEMORY_BEATS = Number(process.env.MAX_MEMORY_BEATS || 100000);

/** In-memory beats: { ms, t, id, ip } — mirror of the log's tail. */
let beats = [];

/* ---- restore the tail of the log so the UI survives restarts ------------- */
try {
  if (fs.existsSync(LOG_FILE)) {
    const lines = fs.readFileSync(LOG_FILE, 'utf8').split('\n').filter(Boolean);
    for (const line of lines.slice(-MAX_MEMORY_BEATS)) {
      try {
        const b = JSON.parse(line);
        if (b && typeof b.ms === 'number') beats.push(b);
      } catch { /* skip malformed line */ }
    }
    console.log(`[heartbeat] restored ${beats.length} beats from ${LOG_FILE}`);
  }
} catch (e) {
  console.error(`[heartbeat] could not read ${LOG_FILE}: ${e.message}`);
}

const logStream = fs.createWriteStream(LOG_FILE, { flags: 'a' });
logStream.on('error', e => console.error(`[heartbeat] log write error: ${e.message}`));

/* ---- helpers -------------------------------------------------------------- */
function clientIp(req) {
  const fwd = req.headers['x-forwarded-for'];
  if (fwd) return String(fwd).split(',')[0].trim();
  const ip = req.socket.remoteAddress || '?';
  return ip.replace(/^::ffff:/, '');
}

function sanitizeId(raw) {
  if (!raw) return 'anon';
  return String(raw).slice(0, 40).replace(/[^\w.\-]/g, '_');
}

function sendJson(res, code, obj) {
  res.writeHead(code, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Cache-Control': 'no-store',
  });
  res.end(JSON.stringify(obj));
}

function servePage(res, file) {
  fs.readFile(path.join(__dirname, file), 'utf8', (err, html) => {
    if (err) return sendJson(res, 500, { ok: false, error: `page missing: ${file}` });
    html = html.split('__EXPECTED_INTERVAL__').join(String(EXPECTED_INTERVAL_S));
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(html);
  });
}

/* ---- server --------------------------------------------------------------- */
const server = http.createServer((req, res) => {
  let url;
  try {
    url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  } catch {
    return sendJson(res, 400, { ok: false, error: 'bad url' });
  }
  const p = url.pathname;

  /* CORS preflight — lets browser pollers on any origin reach us */
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': '*',
    });
    return res.end();
  }

  /* The beat itself — GET or POST both accepted */
  if (p === '/heartbeat') {
    const now = new Date();
    const beat = {
      ms: now.getTime(),
      t: now.toISOString(),
      id: sanitizeId(url.searchParams.get('id')),
      ip: clientIp(req),
    };
    beats.push(beat);
    if (beats.length > MAX_MEMORY_BEATS) beats = beats.slice(-Math.floor(MAX_MEMORY_BEATS * 0.9));
    logStream.write(JSON.stringify(beat) + '\n');
    return sendJson(res, 200, { ok: true, t: beat.t, id: beat.id, total: beats.length });
  }

  /* Data feed for the dashboard (incremental via ?since=<epoch ms>) */
  if (p === '/api/beats') {
    const since = Number(url.searchParams.get('since') || 0);
    const list = since > 0 ? beats.filter(b => b.ms > since) : beats;
    return sendJson(res, 200, {
      now: Date.now(),
      expectedIntervalS: EXPECTED_INTERVAL_S,
      total: beats.length,
      beats: list.slice(-20000),
    });
  }

  if (p === '/ui') return servePage(res, 'ui.html');
  if (p === '/poll') return servePage(res, 'poll.html');
  if (p === '/') { res.writeHead(302, { Location: '/ui' }); return res.end(); }

  sendJson(res, 404, {
    ok: false,
    error: 'not found',
    endpoints: ['/heartbeat?id=NAME', '/api/beats?since=MS', '/ui', '/poll?id=NAME'],
  });
});

server.listen(PORT, HOST, () => {
  console.log(`[heartbeat] listening on http://${HOST}:${PORT}`);
  console.log(`[heartbeat]   students poll : GET /heartbeat?id=NAME   (expected every ${EXPECTED_INTERVAL_S}s)`);
  console.log(`[heartbeat]   dashboard     : /ui`);
  console.log(`[heartbeat]   browser poller: /poll?id=NAME`);
  console.log(`[heartbeat]   CLI poller    : node beat.js http://<this-host>:${PORT} --id NAME`);
  console.log(`[heartbeat]   log file      : ${LOG_FILE}`);
});

/* never die mid-lesson */
process.on('uncaughtException', e => console.error('[heartbeat] uncaught:', e));
process.on('unhandledRejection', e => console.error('[heartbeat] unhandled:', e));
