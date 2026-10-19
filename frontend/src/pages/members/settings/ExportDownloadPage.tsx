import { Download, PackageCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { QuickExit } from '@/components/layout/QuickExit'
import { AppButton, Wordmark } from '@/components/members/app/primitives'
import { api } from '@/lib/api'
import { fragmentParams } from '@/lib/format'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/**
 * The emailed export link lands here. The single-use token stays in the URL fragment and is
 * the only credential, so it works signed in or out, on its own page in the app's look.
 */
export function ExportDownloadPage() {
  useDocumentMeta({ title: 'Your data', noindex: true })
  const [token] = useState(() => fragmentParams(window.location.hash).get('token') ?? '')
  const [status, setStatus] = useState<'idle' | 'working' | 'done' | 'error'>(token ? 'idle' : 'error')
  const [message, setMessage] = useState(token ? '' : 'This link is incomplete. Open it again from your email.')

  async function download() {
    setStatus('working')
    try {
      const blob = await api.downloadDataExport(token)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'my-data.zip'
      link.click()
      URL.revokeObjectURL(url)
      window.history.replaceState(null, '', window.location.pathname)
      setStatus('done')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Please request a new copy.')
      setStatus('error')
    }
  }

  return (
    <div className="member-app flex min-h-dvh flex-col items-center px-4 py-16">
      <Wordmark />
      <main className="mt-8 flex w-full max-w-[400px] flex-col gap-4 rounded-app border border-border bg-canvas p-6">
        <PackageCheck aria-hidden="true" className="size-8 text-fg" strokeWidth={1.5} />
        <h1 className="text-xl font-semibold text-fg">Your data</h1>
        <p className="text-fg-muted">A zip with your account settings, RSVPs, membership and anything you shared in the member feed.</p>
        {status === 'done' && (
          <p role="status" className="rounded-app bg-tint p-3 text-sm text-tint-fg">
            Your download has started. The link has now been used up.
          </p>
        )}
        {status === 'error' && (
          <p role="alert" className="rounded-app bg-tint p-3 text-sm text-tint-fg">
            {message} You can ask for a new copy in{' '}
            <Link to="/members/settings/privacy" className="font-semibold underline">
              Settings
            </Link>
            .
          </p>
        )}
        {(status === 'idle' || status === 'working') && (
          <>
            <p className="text-meta text-fg-muted">This link works once. Download on a device you trust.</p>
            <AppButton className="h-11 w-full" onClick={() => void download()} disabled={status === 'working'}>
              <Download aria-hidden="true" className="size-4" />
              {status === 'working' ? 'Preparing' : 'Download my data'}
            </AppButton>
          </>
        )}
      </main>
      <QuickExit variant="floating" />
    </div>
  )
}
