/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const manifestPath = fileURLToPath(new URL('../docs/image-manifest.json', import.meta.url))
// Where the dev server forwards /api and /media. Docker Compose points it at the api service.
const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

// The two faces every page uses straight away. Preloading them avoids a late
// swap of the hero text; every other face still loads on demand (font-display: swap).
const PRELOAD_FONTS = [/manrope-latin-wght-normal-[^/]+\.woff2$/, /fraunces-latin-opsz-normal-[^/]+\.woff2$/]

function preloadFonts(): Plugin {
  return {
    name: 'preload-fonts',
    apply: 'build',
    transformIndexHtml(_html, context) {
      const files = Object.keys(context.bundle ?? {}).filter((file) => PRELOAD_FONTS.some((pattern) => pattern.test(file)))
      return files.map((file) => ({
        tag: 'link',
        attrs: { rel: 'preload', href: `/${file}`, as: 'font', type: 'font/woff2', crossorigin: '' },
        injectTo: 'head' as const,
      }))
    },
  }
}

export default defineConfig({
  plugins: [react(), tailwindcss(), preloadFonts()],
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
    // Never inline files as data: URLs; the CSP (font-src 'self') would block them.
    assetsInlineLimit: 0,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
