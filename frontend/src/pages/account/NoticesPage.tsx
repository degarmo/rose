import { useState } from 'react'
import { Link, Navigate } from 'react-router'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { Badge, Button, Card, FormField, Section, Textarea, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { formatDay } from '@/lib/format'
import { safetyApi, type MemberActionData } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

function AppealForm({ action, onDone }: { action: MemberActionData; onDone: (next: MemberActionData) => void }) {
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  if (!open) {
    return (
      <Button variant="outline" size="sm" className="self-start" onClick={() => setOpen(true)}>
        Appeal this decision
      </Button>
    )
  }

  async function submit() {
    if (!text.trim()) return setError('Tell us why you think this was wrong.')
    setBusy(true)
    try {
      onDone(await safetyApi.appeal(action.id, text.trim()))
      toast.show({ tone: 'success', title: 'Your appeal is with the team', message: 'Someone who did not make the decision will review it.' })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'It was not sent. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <FormField label="Your appeal" hint="You can appeal each decision once." required error={error}>
        {(field) => <Textarea {...field} rows={4} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} />}
      </FormField>
      <div className="flex gap-3">
        <Button onClick={() => void submit()} disabled={busy} aria-busy={busy}>
          {busy ? 'Sending' : 'Send appeal'}
        </Button>
        <Button variant="secondary" onClick={() => setOpen(false)} disabled={busy}>
          Cancel
        </Button>
      </div>
    </div>
  )
}

function Notice({ action, onChange }: { action: MemberActionData; onChange: (next: MemberActionData) => void }) {
  const status = action.reversed_at ? 'Reversed' : action.in_force ? (action.ends_at ? `Until ${formatDay(action.ends_at)}` : 'In force') : 'Ended'
  return (
    <Card as="article" className="flex flex-col gap-3 p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl text-fg">{action.kind_label}</h2>
        <Badge tone={action.reversed_at || !action.in_force ? 'full' : 'wait'}>{status}</Badge>
      </div>
      <p className="text-sm text-fg-muted">
        {formatDay(action.created_at)} · {action.rule}
      </p>
      <p className="text-fg">{action.reason}</p>
      {action.reversed_at && <p className="text-sm text-fg-muted">Reversed on {formatDay(action.reversed_at)}.</p>}
      {action.appeal ? (
        <p className="text-sm text-fg-muted">
          Appeal sent {formatDay(action.appeal.created_at)}: {action.appeal.status === 'open' ? 'waiting for review' : action.appeal.status_label.toLowerCase()}.
        </p>
      ) : (
        !action.reversed_at && <AppealForm action={action} onDone={onChange} />
      )}
    </Card>
  )
}

/**
 * Your account's notices: any decision our team made, with its reason and the rule, and
 * one appeal each. On the website rather than in the app, so it stays readable while the
 * app is paused. Reports you sent show only that they arrived, then that they were reviewed.
 */
export function NoticesPage() {
  useDocumentMeta({ title: 'Notices', noindex: true })
  const auth = useAuth()
  const signedIn = Boolean(auth.user)
  const notices = useAsync(() => (signedIn ? safetyApi.notices() : Promise.resolve([])), `notices:${signedIn}`)
  const reports = useAsync(() => (signedIn ? safetyApi.myReports() : Promise.resolve([])), `my-reports:${signedIn}`)
  const [updated, setUpdated] = useState<Record<number, MemberActionData>>({})

  if (auth.status === 'loading') {
    return (
      <Section width="narrow">
        <LoadingState label="Loading" />
      </Section>
    )
  }
  if (!auth.user) return <Navigate to="/account/login?next=%2Faccount%2Fnotices" replace />

  return (
    <Section width="narrow" spacing="none" className="pb-16 pt-7 lg:pb-24 lg:pt-16">
      <Link to="/account" className="text-sm font-semibold text-link">
        My account
      </Link>
      <h1 className="mt-3 text-[2.25rem] font-light leading-[1.05] text-fg lg:text-h1">Notices</h1>
      <p className="mt-3 text-fg-muted lg:text-lead">Decisions our team made about your account. Emails only point here; the details are on this page.</p>

      <div className="mt-8 flex flex-col gap-4">
        {notices.status === 'loading' && <LoadingState label="Loading notices" />}
        {notices.status === 'error' && <ErrorState title="Notices did not load" onRetry={notices.retry} />}
        {notices.status === 'success' &&
          (notices.data.length === 0 ? (
            <EmptyState title="No notices" message="There are no decisions about your account." />
          ) : (
            notices.data.map((action) => {
              const current = updated[action.id] ?? action
              return <Notice key={action.id} action={current} onChange={(next) => setUpdated((all) => ({ ...all, [next.id]: next }))} />
            })
          ))}
      </div>

      <section aria-labelledby="sent-reports" className="mt-12">
        <h2 id="sent-reports" className="text-[1.625rem] font-light text-fg">
          Reports you sent
        </h2>
        <p className="mt-1 text-sm text-fg-muted">For privacy we never share what was decided, only that it was reviewed.</p>
        <div className="mt-4">
          {reports.status === 'loading' && <LoadingState label="Loading your reports" />}
          {reports.status === 'error' && <ErrorState title="Your reports did not load" onRetry={reports.retry} />}
          {reports.status === 'success' &&
            (reports.data.length === 0 ? (
              <p className="text-fg-muted">You have not sent any reports.</p>
            ) : (
              <ul className="divide-y divide-border border-y border-border">
                {reports.data.map((report) => (
                  <li key={report.id} className="flex items-center justify-between gap-3 py-3">
                    <span className="text-fg">
                      {report.kind_label} <span className="text-fg-muted">· {formatDay(report.created_at)}</span>
                    </span>
                    <Badge tone={report.status === 'reviewed' ? 'open' : 'wait'}>{report.status === 'reviewed' ? 'Reviewed' : 'Received'}</Badge>
                  </li>
                ))}
              </ul>
            ))}
        </div>
      </section>
    </Section>
  )
}
