import '@fontsource-variable/fraunces/opsz.css'
import '@fontsource-variable/fraunces/opsz-italic.css'
import '@fontsource-variable/manrope/wght.css'
import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { hasConfirmedAge } from './lib/ageGate'
import { applyAppearance, cookieAppearance } from './lib/appearance'
import { prefetchMemberApp } from './lib/membersApi'

const root = document.getElementById('root')
if (!root) throw new Error('Root element missing')

// Before the first paint, from this browser's cookie; no request is made for it.
applyAppearance(cookieAppearance())
// Past the age gate already: a direct visit to the member feed starts its requests now.
if (hasConfirmedAge()) prefetchMemberApp(window.location.pathname, window.location.search)

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
