import { CircleCheck } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useAuth } from '@/components/layout/authContext'
import { ButtonLink } from '@/components/ui'
import { api } from '@/lib/api'
import { fragmentParams } from '@/lib/format'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
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
      {status === 'working' && <p role="status" className="text-fg-muted">Confirming your address</p>}
      {status === 'done' && (
        <div role="status">
          <CircleCheck aria-hidden="true" className="size-8 text-success" />
          <p className="mt-4 text-fg-muted">Your email is confirmed. You can RSVP to events now.</p>
          <ButtonLink to={auth.user ? '/events' : '/account/login?next=/events'} size="lg" className="mt-8 w-full">
            {auth.user ? 'See events' : 'Log in'}
          </ButtonLink>
        </div>
      )}
      {status === 'error' && (
        <div role="alert">
          <p className="text-fg-muted">{message}</p>
          <ButtonLink to="/account" variant="ghost" className="mt-8 w-full">
            Go to my account
          </ButtonLink>
        </div>
      )}
    </AccountShell>
  )
}
