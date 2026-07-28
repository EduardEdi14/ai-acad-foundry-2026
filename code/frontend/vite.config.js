import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Where the backend lives depends on where THIS dev server is running, so compose
// sets VITE_API_TARGET per lane and the default covers plain `npm run dev`:
//   host          → http://localhost:7799            (the default below)
//   all in Docker → http://api:7799                  (docker-compose.yml)
//   API on host   → http://host.docker.internal:7799 (docker-compose.host-api.yml,
//                    which also needs uvicorn started with --host 0.0.0.0 on Linux)
const target = process.env.VITE_API_TARGET || 'http://localhost:7799'

// Every backend route the console uses. Proxied so there is no CORS to configure.
const ROUTES = [
  '/health', '/config', '/azure',
  '/chunk', '/ingest', '/collection', '/search', '/ask',
  '/agents', '/tools',
]

// A proxy error means the backend is not where the console thinks it is. Vite's
// default response is a bare 500 with no body, which tells you nothing — so we
// answer with the diagnosis and the command that fixes it. The console reads
// `detail` out of error responses, so this text lands directly in the UI.
function proxyTo(target) {
  return {
    target,
    changeOrigin: true,
    configure: (proxy) => {
      proxy.on('error', (err, req, res) => {
        const toContainer = target.includes('//api:')
        const detail =
          `The console cannot reach the backend at ${target} (${err.code || err.message}). ` +
          (toContainer
            ? 'It is proxying to the "api" container, which is not running. ' +
              'If your backend runs on your machine instead, start compose with the ' +
              'host-api override: docker compose -f docker-compose.yml ' +
              '-f docker-compose.host-api.yml up -d'
            : 'Start it with: cd code/backend && uv run uvicorn app.main:app ' +
              '--reload --port 7799')
        if (res && !res.headersSent && res.writeHead) {
          res.writeHead(502, { 'Content-Type': 'application/json' })
          res.end(JSON.stringify({ detail }))
        }
      })
    },
  }
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 7800,
    host: '0.0.0.0',
    watch: { usePolling: true },      // reliable file watching inside containers
    proxy: Object.fromEntries(ROUTES.map((route) => [route, proxyTo(target)])),
  },
})
