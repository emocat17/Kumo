import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const port = Number(process.env.VITE_DEV_PORT || env.VITE_DEV_PORT || 18080)
  // Prioritize system environment variables (e.g. from Docker Compose)
  const apiBase = process.env.VITE_API_BASE_URL || env.VITE_API_BASE_URL

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      host: '0.0.0.0',
      port,
      watch: {
        usePolling: true,
        ignored: ['**/node_modules/**', '**/.git/**', '**/*.log', '**/*.swp', '**/*~']
      },
      hmr: {
        host: 'localhost',
        clientPort: port
      },
      open: false,
      proxy: apiBase
        ? {
            '/api': {
              target: apiBase,
              changeOrigin: true,
              secure: false,
              ws: true
            }
          }
        : undefined
    },
    test: {
      environment: 'jsdom'
    }
  }
})
