# Classroom Heartbeat

A zero-dependency Node app for one job: **knowing, to the second, when the
classroom's connection drops**. Students poll `/heartbeat` every few seconds;
every hit is appended to a JSON-lines log; `/ui` renders a live timeline where
gaps are highlighted in red with exact from/to timestamps.

```
students' room ── GET /heartbeat?id=ana ──►  server (this app)
   browser tab /poll · node beat.js · curl        │
                                                  ├─► heartbeat-log.jsonl  (one JSON per beat)
your PC ───────── GET /ui ◄───────────────────────┘   (live dashboard)
```

No dependencies — `npm install` is **not needed**. Node ≥ 18.

## Run

```bash
cd resources/heartbeat-app
npm run dev                      # same as: node server.js
```

| Env var | Default | Meaning |
|---|---|---|
| `PORT` | `5798` | Listening port |
| `HOST` | `0.0.0.0` | Bind address |
| `EXPECTED_INTERVAL_S` | `5` | How often clients are told to beat; UI flags gaps ≥ 2× this |
| `LOG_FILE` | `./heartbeat-log.jsonl` | Where beats are appended |

Example: `PORT=5798 EXPECTED_INTERVAL_S=5 node server.js`

## Deploy on a Linux server

```bash
scp -r heartbeat-app user@teamcoding.ro:~/
ssh user@teamcoding.ro
cd heartbeat-app
nohup node server.js > server.out 2>&1 &      # quick & dirty
sudo ufw allow 5798/tcp                       # if ufw is active
```

Or as a systemd service (`/etc/systemd/system/heartbeat.service`):

```ini
[Unit]
Description=Classroom Heartbeat
After=network.target

[Service]
WorkingDirectory=/home/user/heartbeat-app
ExecStart=/usr/bin/node server.js
Restart=always
Environment=PORT=5798

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now heartbeat
```

## Endpoints

| Endpoint | What it does |
|---|---|
| `GET /heartbeat?id=NAME` | Records one beat (also accepts POST). CORS open. |
| `GET /ui` | The live dashboard — open this on your PC. |
| `GET /poll?id=NAME` | Browser-based sender for students: open, keep the tab open. |
| `GET /api/beats?since=MS` | JSON feed the dashboard polls (incremental). |
| `GET /` | Redirects to `/ui`. |

## What to give the students

Any **one or more** of these (more senders = more signal):

- **Browser (easiest):** `http://teamcoding.ro:5798/poll?id=ana` — keep the tab open.
- **Node CLI:** `node beat.js http://teamcoding.ro:5798 --id ana --every 5`
  (just the one `beat.js` file is needed; every attempt prints a timestamped OK/FAIL line,
  so the student's console doubles as a client-side connectivity log).
- **curl (macOS/Linux):** `while true; do curl -s "http://teamcoding.ro:5798/heartbeat?id=ana" > /dev/null; sleep 5; done`
- **PowerShell (Windows):** `while($true){ irm "http://teamcoding.ro:5798/heartbeat?id=ana" | Out-Null; Start-Sleep 5 }`

## The dashboard (`/ui`)

- **Status pill** — LIVE while beats arrive; DOWN (with "how long ago") the moment the room goes silent.
- **Timeline** — one cyan tick per beat; a merged ALL lane plus one lane per client id;
  red bands over every gap ≥ 2× the expected interval, labelled with duration; gold line = now.
- **Outages table** — every gap with from/to timestamps at second precision (the thing you'll
  screenshot when arguing with the venue's IT).
- **Window switch** (5 min → 3 h) and per-client filter chips.
- Times are rendered in the viewer's local timezone; the log stores UTC ISO + epoch ms.

## Log format

`heartbeat-log.jsonl` — one JSON object per line, append-only:

```json
{"ms":1753167064123,"t":"2026-07-22T06:51:04.123Z","id":"ana","ip":"86.120.x.x"}
```

The server reloads the tail of this file on restart, so history survives restarts.
Rotation, if ever needed: stop, `mv heartbeat-log.jsonl archive/`, start.
