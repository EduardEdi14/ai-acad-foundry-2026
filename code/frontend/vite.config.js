import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The backend URL differs between "npm run dev" on the host (localhost:7799)
// and docker compose (the service name). VITE_API_TARGET overrides it.
const target = process.env.VITE_API_TARGET || 'http://localhost:7799'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 7800,
    host: '0.0.0.0',
    watch: { usePolling: true },      // reliable file watching inside containers
    proxy: {
      // every backend route the console uses, proxied to avoid CORS entirely
      '/health': target,
      '/config': target,
      '/azure': target,
      '/chunk': target,
      '/ingest': target,
      '/collection': target,
      '/search': target,
      '/ask': target,
      '/agents': target,
      '/tools': target,
    },
  },
})
