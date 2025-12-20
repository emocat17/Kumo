import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const port = 6677 // Changed from 6666 (unsafe port) to 6677
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
      open: true,
      proxy: apiBase
        ? {
            '/api': {
              target: apiBase,
              changeOrigin: true,
              secure: false
            }
          }
        : undefined
    },
    test: {
      environment: 'jsdom'
    }
  }
})
