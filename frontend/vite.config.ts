import { createReadStream, statSync } from 'node:fs'
import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const repoRoot = resolve(import.meta.dirname, '..')
const dataDir = resolve(repoRoot, 'data')

/**
 * Serverar repots data/-mapp under /data i dev, så 3D-vyn kan hämta 772_H811_new.ifc
 * (docs/adr.md ADR-3) utan att filen kopieras in i frontend/public.
 *
 * Endast läsning: filerna skrivs aldrig (AGENTS.md), och bara filnamn som faktiskt ligger i
 * data/ serveras (ingen traversering ut ur mappen).
 */
function serveRepoData(): Plugin {
  return {
    name: 'serve-repo-data',
    configureServer(server) {
      server.middlewares.use('/data', (req, res, next) => {
        const name = decodeURIComponent((req.url ?? '').split('?')[0]).replace(/^\//, '')
        const file = resolve(dataDir, name)
        if (!file.startsWith(dataDir + '/')) return next()

        let stats
        try {
          stats = statSync(file)
        } catch {
          return next()
        }
        if (!stats.isFile()) return next()

        res.setHeader('Content-Type', 'application/octet-stream')
        res.setHeader('Content-Length', stats.size)
        createReadStream(file).pipe(res)
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), serveRepoData()],
  // web-ifc laddar sin WASM-binär i runtime; den ska inte bundlas om.
  optimizeDeps: { exclude: ['web-ifc'] },
  server: {
    // Backend körs separat, se ../backend/README.md. Håller frontendkoden fri från
    // http://localhost:8000 hårdkodat på fler ställen än här.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
    fs: {
      allow: [resolve(repoRoot, 'frontend'), dataDir],
    },
  },
})
