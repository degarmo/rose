import { Download } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui'
import { fragmentParams } from '@/lib/format'
import { feedAccount } from '@/lib/membersApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { AccountShell } from './AccountShell'

/** The emailed link lands here; the single-use token stays in the URL fragment. */
export function ExportDownloadPage() {
  useDocumentMeta({ title: 'Your data', noindex: true })
  const [token] = useState(() => fragmentParams(window.location.hash).get('token') ?? '')
  const [status, setStatus] = useState<'idle' | 'working' | 'done' | 'error'>(token ? 'idle' : 'error')
  const [message, setMessage] = useState(token ? '' : 'This link is incomplete. Open it again from your email.')

  async function download() {
    setStatus('working')
    try {
      const blob = await feedAccount.downloadExport(token)
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
    <AccountShell title="Your data" lede="A zip with your profile, posts, comments, likes and photos.">
      {status === 'done' && <p role="status" className="text-fg-muted">Your download has started. The link has now been used up.</p>}
      {status === 'error' && <p role="alert" className="text-fg-muted">{message}</p>}
      {(status === 'idle' || status === 'working') && (
        <div>
          <p className="text-sm text-fg-muted">This link works once. Download on a device you trust.</p>
          <Button className="mt-6" onClick={() => void download()} disabled={status === 'working'} aria-busy={status === 'working'}>
            <Download aria-hidden="true" className="size-4" />
            {status === 'working' ? 'Preparing' : 'Download my data'}
          </Button>
        </div>
      )}
    </AccountShell>
  )
}
