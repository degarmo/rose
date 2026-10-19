import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { ButtonLink } from '@/components/ui'
import { api } from '@/lib/api'
import { fragmentParams } from '@/lib/format'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { SENT_ACTION, SentPanel } from '../SentPanel'
import { AccountShell } from './AccountShell'

export function VerifyEmailPage() {
  useDocumentMeta({ title: 'Confirm your email', noindex: true })
  const auth = useAuth()
  const token = fragmentParams(window.location.hash).get('token') ?? ''
  const [status, setStatus] = useState<'working' | 'done' | 'error'>(token ? 'working' : 'error')
  const [message, setMessage] = useState(token ? '' : 'This link is incomplete. Open it again from your email.')
  const started = useRef(false)

  useEffect(() => {
    if (!token || started.current) return
    started.current = true
    api.verifyEmail(token).then(
      () => {
        setStatus('done')
        // Drop the token from the address bar and history.
        window.history.replaceState(null, '', window.location.pathname)
        void auth.refresh()
      },
      (error: unknown) => {
        setStatus('error')
        setMessage(error instanceof Error ? error.message : 'Please try again.')
      },
    )
  }, [token, auth])

  return (
    <AccountShell title="Confirm your email">
      {status === 'working' && <LoadingState label="Confirming your address" className="py-0" />}
      {status === 'done' && (
        <SentPanel
          actions={
            <Link to={auth.user ? '/events' : '/account/login?next=/events'} className={SENT_ACTION}>
              {auth.user ? 'See events' : 'Log in'}
            </Link>
          }
        >
          Your email is confirmed. You can RSVP to events now.
        </SentPanel>
      )}
      {status === 'error' && (
        <div role="alert" className="flex flex-col items-start gap-6">
          <p className="w-full rounded-card bg-blush p-4 text-fg-muted-tint">{message}</p>
          <ButtonLink to="/members/settings" variant="secondary" size="lg">
            Go to Settings
          </ButtonLink>
        </div>
      )}
    </AccountShell>
  )
}
