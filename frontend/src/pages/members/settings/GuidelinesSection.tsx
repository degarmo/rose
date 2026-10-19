import { BadgeCheck, Flag, Inbox, ScrollText, Send } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { GuidelinesText } from '@/components/members/GuidelinesText'
import { AppButton } from '@/components/members/app/primitives'
import { appButtonClasses } from '@/components/members/app/ui'
import { Card, EmptyNote, FeedOnlyNote, LinkRow, LoadError, Skeleton, StatusChip } from '@/components/members/settings/ui'
import { useFeedAccount } from '@/components/members/settings/useFeedAccount'
import { FormField, Textarea, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { formatDay } from '@/lib/format'
import { safetyApi, type MemberActionData } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'

/** The current version, and the date you accepted it. */
function CurrentGuidelines() {
  const feed = useFeedAccount()
  if (!feed.controls) {
    return (
      <FeedOnlyNote icon={ScrollText} title="Community guidelines">
        You read and accept the community guidelines when you join the member feed. At events, the house rules apply.
      </FeedOnlyNote>
    )
  }
  if (feed.state.status === 'error') return <LoadError title="The guidelines did not load" onRetry={feed.state.retry} />
  const account = feed.account
  if (!account) return <Skeleton lines={3} />
  const guidelines = account.guidelines
  if (!guidelines) return <p className="text-fg-muted">The guidelines are being written. They will show here.</p>
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-fg">{guidelines.title}</p>
          <p className="text-meta text-fg-muted">
            Version {guidelines.version} · published {formatDay(guidelines.published_at)}
          </p>
        </div>
        {account.accepted_current_guidelines ? <StatusChip tone="ok">Accepted</StatusChip> : <StatusChip tone="wait">Not accepted yet</StatusChip>}
      </div>
      {account.accepted_current_guidelines && account.guidelines_accepted_at ? (
        <p className="flex items-center gap-2 text-fg">
          <BadgeCheck aria-hidden="true" className="size-5 text-link" />
          You accepted this version on {formatDay(account.guidelines_accepted_at)}.
        </p>
      ) : (
        account.participating && (
          <Link to="/members/join-feed?guidelines=1" className={appButtonClasses('primary', 'self-start')}>
            Read and accept
          </Link>
        )
      )}
      <details className="group rounded-app border border-border">
        <summary className="flex min-h-11 cursor-pointer items-center px-3 font-semibold text-fg">Read the guidelines</summary>
        <div className="border-t border-border p-4">
          <GuidelinesText body={guidelines.body} />
        </div>
      </details>
    </div>
  )
}

function AppealForm({ action, onDone }: { action: MemberActionData; onDone: (next: MemberActionData) => void }) {
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  if (!open) {
    return (
      <AppButton variant="secondary" className="self-start" onClick={() => setOpen(true)}>
        Appeal this decision
      </AppButton>
    )
  }

  async function submit() {
    if (!text.trim()) return setError('Tell us why you think this was wrong.')
    setBusy(true)
    try {
      onDone(await safetyApi.appeal(action.id, text.trim()))
      toast.show({
        tone: 'success',
        title: 'Your appeal is with the team',
        message: 'Someone who did not make the decision will review it.',
      })
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
      <div className="flex gap-2">
        <AppButton onClick={() => void submit()} disabled={busy}>
          {busy ? 'Sending' : 'Send appeal'}
        </AppButton>
        <AppButton variant="secondary" onClick={() => setOpen(false)} disabled={busy}>
          Cancel
        </AppButton>
      </div>
    </div>
  )
}

function Notice({ action, onChange }: { action: MemberActionData; onChange: (next: MemberActionData) => void }) {
  const ended = Boolean(action.reversed_at) || !action.in_force
  const status = action.reversed_at ? 'Reversed' : action.in_force ? (action.ends_at ? `Until ${formatDay(action.ends_at)}` : 'In force') : 'Ended'
  return (
    <li className="flex flex-col gap-2 border-b border-border py-4 first:pt-0 last:border-b-0 last:pb-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-fg">{action.kind_label}</p>
          <p className="text-meta text-fg-muted">
            {formatDay(action.created_at)} · {action.rule}
          </p>
        </div>
        <StatusChip tone={ended ? 'off' : 'wait'}>{status}</StatusChip>
      </div>
      <p className="text-fg">{action.reason}</p>
      {action.reversed_at && <p className="text-meta text-fg-muted">Reversed on {formatDay(action.reversed_at)}.</p>}
      {action.appeal ? (
        <p className="text-meta text-fg-muted">
          Appeal sent {formatDay(action.appeal.created_at)}: {action.appeal.status === 'open' ? 'waiting for review' : action.appeal.status_label.toLowerCase()}
          .
        </p>
      ) : (
        !action.reversed_at && <AppealForm action={action} onDone={onChange} />
      )}
    </li>
  )
}

/** Decisions our team made about your account, each with one appeal. Emails only point here. */
function Notices() {
  const notices = useAsync(() => safetyApi.notices(), 'notices')
  const [updated, setUpdated] = useState<Record<number, MemberActionData>>({})
  if (notices.status === 'loading') return <Skeleton lines={3} />
  if (notices.status === 'error') return <LoadError title="Notices did not load" onRetry={notices.retry} />
  if (notices.data.length === 0) {
    return (
      <EmptyNote icon={Inbox} title="No notices">
        There are no decisions about your account. If our team ever makes one, it shows here with the reason and a way to appeal.
      </EmptyNote>
    )
  }
  return (
    <ul>
      {notices.data.map((action) => (
        <Notice key={action.id} action={updated[action.id] ?? action} onChange={(next) => setUpdated((all) => ({ ...all, [next.id]: next }))} />
      ))}
    </ul>
  )
}

/** Reports you sent: only that each arrived, then that it was reviewed. */
function SentReports() {
  const reports = useAsync(() => safetyApi.myReports(), 'my-reports')
  if (reports.status === 'loading') return <Skeleton lines={2} />
  if (reports.status === 'error') return <LoadError title="Your reports did not load" onRetry={reports.retry} />
  if (reports.data.length === 0) {
    return (
      <EmptyNote
        icon={Send}
        title="You have not sent any reports"
        action={
          <Link to="/members/report" className={appButtonClasses('secondary')}>
            Report a concern
          </Link>
        }
      >
        If something at an evening or online did not feel right, tell us.
      </EmptyNote>
    )
  }
  return (
    <>
      <ul>
        {reports.data.map((report) => (
          <li key={report.id} className="flex min-h-12 items-center justify-between gap-3 border-b border-border py-2 last:border-b-0">
            <span className="min-w-0 text-fg">
              {report.kind_label} <span className="text-fg-muted">· {formatDay(report.created_at)}</span>
            </span>
            <StatusChip tone={report.status === 'reviewed' ? 'ok' : 'wait'}>{report.status === 'reviewed' ? 'Reviewed' : 'Received'}</StatusChip>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-meta text-fg-muted">For privacy we never share what was decided, only that it was reviewed.</p>
    </>
  )
}

/** Settings · Community guidelines: the current version and your acceptance, notices and appeals, reports you sent. */
export function GuidelinesSection() {
  return (
    <div className="flex flex-col gap-4">
      <Card title="The guidelines">
        <CurrentGuidelines />
      </Card>
      <Card title="Notices about your account">
        <Notices />
      </Card>
      <Card title="Reports you sent">
        <SentReports />
      </Card>
      <Card>
        <ul>
          <LinkRow icon={Flag} label="Report a concern" sub="Something that happened at an event or the club" to="/members/report" />
          <LinkRow icon={ScrollText} label="House rules" sub="How evenings work, for everyone" to="/house-rules" />
        </ul>
      </Card>
    </div>
  )
}
