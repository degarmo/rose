/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const manifestPath = fileURLToPath(new URL('../docs/image-manifest.json', import.meta.url))
// Where the dev server forwards /api and /media. Docker Compose points it at the api service.
const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@image-manifest': manifestPath,
    },
  },
  server: {
    port: 5173,
    fs: { allow: ['.', manifestPath] },
    proxy: {
      '/api': proxyTarget,
      '/media': proxyTarget,
    },
  },
  build: {
    sourcemap: false,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
