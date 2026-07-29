import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import http from 'node:http'

// Where the backend lives depends on where THIS dev server runs — on your machine,
// in a container next to the API, or in a container while the API runs on the host.
// Rather than making you remember which, the config *probes* at startup and uses the
// first candidate that answers /health:
//
//   VITE_API_TARGET            an explicit choice always wins if it answers
//   http://api:7799            the API container, when everything is in compose
//   http://host.docker.internal:7799   the host, when only the console is in Docker
//   http://localhost:7799      plain `npm run dev` on your machine
//
// So `docker compose up` and "qdrant + console in Docker, backend under uv" both work
// with no edit anywhere. The probe runs once, at start: if you launch the backend
// afterwards, restart the console.
const CANDIDATES = [
  process.env.VITE_API_TARGET,
  'http://api:7799',
  'http://host.docker.internal:7799',
  'http://localhost:7799',
].filter(Boolean)

// Every backend route the console uses. Proxied so there is no CORS to configure.
const ROUTES = [
  '/health', '/config', '/azure',
  '/chunk', '/ingest', '/collection', '/search', '/ask',
  '/agents', '/tools',
]

function answers(base, timeout = 2000) {
  return new Promise((resolve) => {
    const request = http.get(`${base}/health`, { timeout }, (response) => {
      response.resume()
      resolve(response.statusCode > 0 && response.statusCode < 500)
    })
    request.on('error', () => resolve(false))
    request.on('timeout', () => { request.destroy(); resolve(false) })
  })
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function pickTarget() {
  // An explicit choice is not a candidate to be tested — it is an instruction. Under
  // `docker compose up` the console and the API start together and the API takes about
  // ten seconds to boot, so probing it would fail and silently fall through to some
  // other address. Vite retries the proxy on every request, so trusting the setting is
  // both simpler and more reliable than racing the container.
  if (process.env.VITE_API_TARGET) {
    console.log(`  ➜  API:      ${process.env.VITE_API_TARGET}  (VITE_API_TARGET)`)
    return process.env.VITE_API_TARGET
  }

  // Nothing was specified, so find it. Four rounds, because inside a container the
  // first probe can run before DNS is ready and a false negative here would send every
  // request to the wrong place.
  for (let round = 0; round < 4; round++) {
    for (const candidate of CANDIDATES) {
      if (await answers(candidate)) {
        console.log(`  ➜  API:      ${candidate}`)
        return candidate
      }
    }
    await wait(1500)
  }
  const fallback = CANDIDATES[0]
  console.log(`  ➜  API:      ${fallback}  (nothing answered — start the backend, then restart this)`)
  return fallback
}

// A proxy error means the backend is not where the console thinks it is. Vite's
// default response is a bare 500 with no body, which tells you nothing — so we
// answer with the diagnosis and the command that fixes it. The console reads
// `detail` out of error responses, so this text lands directly in the interface.
function proxyTo(target) {
  return {
    target,
    changeOrigin: true,
    configure: (proxy) => {
      proxy.on('error', (err, req, res) => {
        const detail =
          `The console cannot reach the backend at ${target} (${err.code || err.message}). ` +
          'Start it with:  cd code/backend && uv run uvicorn app.main:app --reload --port 7799 ' +
          '— then restart the console so it can find it again.'
        if (res && !res.headersSent && res.writeHead) {
          res.writeHead(502, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ detail }))
        }
      })
    },
  }
}

export default defineConfig(async ({ command }) => {
  // `vite build` produces static files: there is no dev server, so there is no
  // proxy and nothing to probe for. Skipping it keeps the production image build
  // from waiting on three connections that cannot succeed. In production nginx
  // forwards the same routes — see frontend/nginx.conf.template.
  if (command === 'build') return { plugins: [react()] }

  const target = await pickTarget()
  return {
    plugins: [react()],
    server: {
      port: 7800,
      host: '0.0.0.0',
      watch: { usePolling: true },    // reliable file watching inside containers
      proxy: Object.fromEntries(ROUTES.map((route) => [route, proxyTo(target)])),
    },
  }
})
