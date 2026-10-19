import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { LoadingState } from '@/components/content/States'
import { Button } from '@/components/ui'
import { api } from '@/lib/api'
import { fragmentParams } from '@/lib/format'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { AccountShell } from './account/AccountShell'
import { SENT_ACTION, SentPanel } from './SentPanel'

/** The token arrives in the URL fragment, which browsers never send to the server. */
function useFragmentToken() {
  const [token] = useState(() => fragmentParams(window.location.hash).get('token') ?? '')
  return token
}

function forgetToken() {
  window.history.replaceState(null, '', window.location.pathname)
}

export function ConfirmSubscriptionPage() {
  useDocumentMeta({ title: 'Confirm your email', noindex: true })
  const token = useFragmentToken()
  const [status, setStatus] = useState<'working' | 'done' | 'error'>(token ? 'working' : 'error')
  const [message, setMessage] = useState(token ? '' : 'This link is incomplete. Open it again from your email.')
  const started = useRef(false)

  useEffect(() => {
    if (!token || started.current) return
    started.current = true
    api.confirmSubscription(token).then(
      (result) => {
        setStatus('done')
        setMessage(result.detail)
        forgetToken()
      },
      (error: unknown) => {
        setStatus('error')
        setMessage(error instanceof Error ? error.message : 'Please try again.')
      },
    )
  }, [token])

  return (
    <AccountShell title="Email updates">
      {status === 'working' && <LoadingState label="Confirming your address" className="py-0" />}
      {status === 'done' && (
        <SentPanel
          actions={
            <Link to="/" className={SENT_ACTION}>
              Back to the site
            </Link>
          }
        >
          {message}
        </SentPanel>
      )}
      {status === 'error' && (
        <p role="alert" className="rounded-card bg-blush p-4 text-fg-muted-tint">
          {message}
        </p>
      )}
    </AccountShell>
  )
}

export function UnsubscribePage() {
  useDocumentMeta({ title: 'Unsubscribe', noindex: true })
  const token = useFragmentToken()
  const [status, setStatus] = useState<'ready' | 'working' | 'done' | 'error'>(token ? 'ready' : 'error')
  const [message, setMessage] = useState(token ? '' : 'This link is incomplete. Open it again from the email.')

  async function leave() {
    setStatus('working')
    try {
      const result = await api.unsubscribe(token)
      setStatus('done')
      setMessage(result.detail)
      forgetToken()
    } catch (error) {
      setStatus('error')
      setMessage(error instanceof Error ? error.message : 'Please try again.')
    }
  }

  return (
    <AccountShell title="Unsubscribe">
      {(status === 'ready' || status === 'working') && (
        <div className="flex flex-col items-start gap-6">
          <p className="text-fg-muted">Stop all email updates to this address. No login needed.</p>
          <Button size="lg" onClick={() => void leave()} disabled={status === 'working'} aria-busy={status === 'working'}>
            {status === 'working' ? 'Unsubscribing' : 'Unsubscribe'}
          </Button>
        </div>
      )}
      {status === 'done' && <SentPanel>{message}</SentPanel>}
      {status === 'error' && (
        <p role="alert" className="rounded-card bg-blush p-4 text-fg-muted-tint">
          {message}
        </p>
      )}
    </AccountShell>
  )
}
