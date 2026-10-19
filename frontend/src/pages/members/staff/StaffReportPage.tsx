import { Eye, EyeOff } from 'lucide-react'
import { useId, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { AppButton } from '@/components/members/app/primitives'
import { ActionDialog } from '@/components/members/staff/ActionDialog'
import { ActionList } from '@/components/members/staff/ActionList'
import { StaffFrame } from '@/components/members/staff/StaffFrame'
import { Select, Textarea, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { formatDay, formatEventDate } from '@/lib/format'
import { staffApi, type ReportDetail, type ReportStatus } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'
import { NotFoundPage } from '@/pages/NotFoundPage'

function Block({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section aria-label={title} className="flex flex-col gap-2 rounded-app border border-border p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-fg">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

/** The reported content, blurred until someone chooses to look. */
function Reported({ report }: { report: ReportDetail }) {
  const [shown, setShown] = useState(false)
  const content = report.content
  const body = (
    <div className="flex flex-col gap-3 text-fg">
      {report.kind === 'post' && (
        <>
          {content.images && content.images.length > 0 && (
            <div className="grid grid-cols-2 gap-1 sm:grid-cols-3">
              {content.images.map((src) => (
                <img key={src} src={src} alt="Reported picture" className="aspect-square w-full object-cover" draggable={false} onContextMenu={(e) => e.preventDefault()} />
              ))}
            </div>
          )}
          <p className="whitespace-pre-line">{content.caption || 'No caption.'}</p>
          <p className="text-sm text-fg-muted">Post status: {content.status?.replaceAll('_', ' ')}</p>
        </>
      )}
      {report.kind === 'comment' && (
        <>
          <p className="whitespace-pre-line">{content.body}</p>
          <p className="text-sm text-fg-muted">On a post: {content.post_caption || 'no caption'}</p>
        </>
      )}
      {report.kind === 'profile' && <p className="whitespace-pre-line">{content.bio || 'No bio.'}</p>}
      {report.kind === 'event' && (
        <dl className="grid gap-1 text-sm sm:grid-cols-[140px_1fr]">
          <dt className="text-fg-muted">Event</dt>
          <dd>{content.event ? `${content.event}${content.event_starts_at ? `, ${formatEventDate(content.event_starts_at)}` : ''}` : 'Not given'}</dd>
          <dt className="text-fg-muted">Date</dt>
          <dd>{content.event_date ? formatDay(content.event_date) : 'Not given'}</dd>
          <dt className="text-fg-muted">Who, if known</dt>
          <dd>{content.reported_name || 'Not given'}</dd>
        </dl>
      )}
      {report.details && (
        <div>
          <p className="text-sm font-semibold">What the reporter said</p>
          <p className="whitespace-pre-line">{report.details}</p>
        </div>
      )}
    </div>
  )
  return (
    <Block
      title="Reported content"
      aside={
        shown && (
          <AppButton variant="plain" onClick={() => setShown(false)}>
            <EyeOff aria-hidden="true" className="size-4" /> Hide
          </AppButton>
        )
      }
    >
      {shown ? (
        body
      ) : (
        <div className="relative overflow-hidden rounded-app">
          <div className="pointer-events-none select-none blur-[14px]" inert>
            {body}
          </div>
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-canvas/60 text-center">
            <p className="font-semibold text-fg">Hidden until you choose to look</p>
            <AppButton variant="outline" onClick={() => setShown(true)}>
              <Eye aria-hidden="true" className="size-4" /> View reported content
            </AppButton>
          </div>
        </div>
      )}
    </Block>
  )
}

function Reporter({ report }: { report: ReportDetail }) {
  const toast = useToast()
  const [revealed, setRevealed] = useState<{ display_name: string | null; contact_email: string } | null>(null)
  async function reveal() {
    try {
      setRevealed(await staffApi.revealReporter(report.id))
    } catch {
      toast.show({ tone: 'error', title: 'That did not work' })
    }
  }
  return (
    <Block title="Reporter">
      {revealed ? (
        <p className="text-fg">
          {revealed.display_name ?? (revealed.contact_email ? `From the website, ${revealed.contact_email}` : 'From the website, no email given')}
          <span className="block text-sm text-fg-muted">You looked at this; it is in the log.</span>
        </p>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-fg-muted">Hidden. The reported member is never told who reported them.</p>
          {report.reporter.can_reveal && (
            <AppButton variant="secondary" onClick={() => void reveal()}>
              Reveal (logged)
            </AppButton>
          )}
        </div>
      )}
    </Block>
  )
}

const STATUS_OPTIONS: Array<{ value: ReportStatus; label: string }> = [
  { value: 'open', label: 'Open' },
  { value: 'in_review', label: 'In review' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'dismissed', label: 'Dismissed' },
]

function Casework({ report, onChange }: { report: ReportDetail; onChange: (next: ReportDetail) => void }) {
  const toast = useToast()
  const noteId = useId()
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  async function run(task: () => Promise<ReportDetail>, done?: string) {
    setBusy(true)
    try {
      onChange(await task())
      if (done) toast.show({ tone: 'success', title: done })
    } catch (error) {
      toast.show({ tone: 'error', title: 'That did not work', message: error instanceof ApiError ? error.message : undefined })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Block title="Casework">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm font-semibold text-fg">
          Status
          <Select
            value={report.status}
            disabled={busy}
            options={STATUS_OPTIONS}
            onChange={(e) => void run(() => staffApi.setStatus(report.id, e.target.value as ReportStatus), 'Status updated')}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-semibold text-fg">
          Assigned to
          <Select
            value={report.assigned_to?.display_name ?? ''}
            disabled={busy}
            options={[{ value: '', label: 'Nobody' }, ...report.team.map((person) => ({ value: person.display_name, label: person.display_name }))]}
            onChange={(e) => void run(() => staffApi.assign(report.id, e.target.value || null), 'Assignment updated')}
          />
        </label>
      </div>
      <div className="mt-2">
        <h3 className="text-sm font-semibold text-fg">Internal notes</h3>
        {report.notes.length === 0 ? (
          <p className="text-sm text-fg-muted">No notes yet. Only the team sees them.</p>
        ) : (
          <ul className="mt-1 flex flex-col gap-2">
            {report.notes.map((n, index) => (
              <li key={index} className="rounded-app bg-surface p-3 text-sm">
                <p className="whitespace-pre-line text-fg">{n.body}</p>
                <p className="mt-1 text-fg-muted">
                  {n.author?.display_name ?? 'Former team member'} · {formatDay(n.created_at)}
                </p>
              </li>
            ))}
          </ul>
        )}
        <form
          className="mt-2 flex flex-col gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            if (!note.trim()) return
            void run(() => staffApi.addNote(report.id, note.trim()), 'Note added').then(() => setNote(''))
          }}
        >
          <label htmlFor={noteId} className="sr-only">
            Add a note
          </label>
          <Textarea id={noteId} rows={2} maxLength={2000} placeholder="Add a note for the team" value={note} onChange={(e) => setNote(e.target.value)} />
          <AppButton type="submit" variant="secondary" className="self-start" disabled={busy || !note.trim()}>
            Add note
          </AppButton>
        </form>
      </div>
    </Block>
  )
}

/** One report: what was reported (hidden until opened), the member's history, notes and actions. */
export function StaffReportPage() {
  const { id = '' } = useParams()
  const reportId = Number(id)
  const state = useAsync(() => staffApi.report(reportId), `report:${reportId}`)
  const [current, setCurrent] = useState<ReportDetail | null>(null)
  const [acting, setActing] = useState(false)
  const report = current?.id === reportId ? current : state.status === 'success' ? state.data : null

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return <NotFoundPage />

  return (
    <StaffFrame title={report ? `Report ${report.id}` : 'Report'}>
      <Link to="/members/staff/reports" className="text-sm font-semibold text-link">
        Back to the inbox
      </Link>
      {state.status === 'loading' && <LoadingState label="Loading the report" />}
      {state.status === 'error' && <ErrorState title="The report did not load" onRetry={state.retry} />}
      {report && (
        <div className="mt-3 grid gap-4 lg:grid-cols-[1fr_300px]">
          <div className="flex flex-col gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">{report.kind_label}</p>
              <p className="text-lg font-semibold text-fg">
                {report.kind === 'event' ? 'Concern' : report.reason_label} · <span className={cn(report.status === 'open' && 'text-link')}>{report.status_label}</span>
              </p>
              <p className="text-sm text-fg-muted">Received {formatDay(report.created_at)}</p>
            </div>
            <Reported report={report} />
            <Reporter report={report} />
            <Casework report={report} onChange={setCurrent} />
          </div>
          <div className="flex flex-col gap-4">
            <Block title="Reported member">
              {report.member ? (
                <>
                  <Link to={`/members/staff/members/${encodeURIComponent(report.member.display_name)}`} className="font-semibold text-link">
                    {report.member.display_name}
                  </Link>
                  <p className="text-sm text-fg-muted">
                    {report.member.prior_reports === 0 ? 'No earlier reports.' : `${report.member.prior_reports} earlier ${report.member.prior_reports === 1 ? 'report' : 'reports'}.`}{' '}
                    {report.member.actions.length === 0 ? 'No earlier actions.' : `${report.member.actions.length} ${report.member.actions.length === 1 ? 'action' : 'actions'}.`}
                  </p>
                  <AppButton className="mt-1 self-start" onClick={() => setActing(true)}>
                    Take action
                  </AppButton>
                </>
              ) : (
                <p className="text-sm text-fg-muted">
                  {report.kind === 'event' ? 'A concern names no account. Find the member under Members to act.' : 'This content is gone.'}
                </p>
              )}
            </Block>
            {report.member && (
              <Block title="Their actions">
                <ActionList
                  actions={report.member.actions}
                  onChange={() => {
                    void staffApi.report(reportId).then(setCurrent)
                  }}
                />
              </Block>
            )}
          </div>
        </div>
      )}
      {report?.member && (
        <ActionDialog
          open={acting}
          onClose={() => setActing(false)}
          handle={report.member.display_name}
          reportId={report.id}
          canRemoveContent={report.kind === 'post' || report.kind === 'comment'}
          onDone={() => {
            void staffApi.report(reportId).then(setCurrent)
          }}
        />
      )}
    </StaffFrame>
  )
}
