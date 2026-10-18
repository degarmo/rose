import { useState } from 'react'
import { RouterProvider } from 'react-router'
import { AgeGate } from './components/layout/AgeGate'
import { AuthProvider } from './components/layout/AuthProvider'
import { SiteSettingsProvider } from './components/layout/SiteSettingsProvider'
import { ToastProvider } from './components/ui'
import { confirmAge, hasConfirmedAge } from './lib/ageGate'
import { useDoubleEscapeExit } from './lib/useDoubleEscapeExit'
import { ExitPage } from './pages/ExitPage'
import { router } from './router'

const EXIT_PATH = '/exit'

export function App() {
  const [confirmed, setConfirmed] = useState(hasConfirmedAge)
  const [declined, setDeclined] = useState(() => window.location.pathname === EXIT_PATH)
  useDoubleEscapeExit()

  if (declined) return <ExitPage />

  if (!confirmed) {
    return (
      <AgeGate
        onConfirm={() => {
          confirmAge()
          setConfirmed(true)
        }}
        onDecline={() => {
          window.history.replaceState(null, '', EXIT_PATH)
          setDeclined(true)
        }}
      />
    )
  }

  return (
    <SiteSettingsProvider>
      <AuthProvider>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </AuthProvider>
    </SiteSettingsProvider>
  )
}
