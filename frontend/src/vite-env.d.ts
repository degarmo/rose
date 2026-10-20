/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_QUICK_EXIT_URL?: string
  readonly VITE_SITE_DISPLAY_NAME?: string
  readonly VITE_SITE_SHORT_NAME?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
