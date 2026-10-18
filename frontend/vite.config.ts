import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const manifestPath = fileURLToPath(new URL('../docs/image-manifest.json', import.meta.url))

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
      '/api': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  },
  build: {
    sourcemap: false,
  },
})
