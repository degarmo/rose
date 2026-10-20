/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_QUICK_EXIT_URL?: string
  readonly VITE_SITE_NAME?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
