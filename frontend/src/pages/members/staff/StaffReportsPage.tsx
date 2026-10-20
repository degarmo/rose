import { Link, useSearchParams } from 'react-router'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { StaffFrame } from '@/components/members/staff/StaffFrame'
import { cn } from '@/lib/cn'
import { formatDay } from '@/lib/format'
import { staffApi, type Appeal, type ReportStatus, type ReportSummary } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'
import { AgeCheckSettingCard } from '@/components/members/staff/AgeCheckSetting'

type Tab = ReportStatus | 'appeals'

const TABS: Array<{ value: Tab; label: string }> = [
  { value: 'open', label: 'Open' },
  { value: 'in_review', label: 'In review' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: 'appeals', label: 'Appeals' },
]

function isTab(value: string | null): value is Tab {
  return TABS.some((tab) => tab.value === value)
}

function ReportRow({ report }: { report: ReportSummary }) {
  return (
    <li>
      <Link to={`/members/staff/reports/${report.id}`} className="flex flex-col gap-1 p-3 hover:bg-surface sm:flex-row sm:items-center sm:gap-4">
        <span className="w-28 shrink-0 text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">{report.kind_label}</span>
        <span className="min-w-0 flex-1">
          <span className="block font-semibold text-fg">
            {report.kind === 'event' ? 'Concern' : report.reason_label}
            {report.subject && <span className="font-normal text-fg-muted"> · {report.subject}</span>}
            {report.from_website && <span className="font-normal text-fg-muted"> · from the website</span>}
          </span>
          {report.preview && <span className="block truncate text-sm text-fg-muted">Content hidden until opened</span>}
        </span>
        <span className="shrink-0 text-sm text-fg-muted">
          {formatDay(report.created_at)}
          {report.assigned_to && ` · ${report.assigned_to.display_name}`}
        </span>
      </Link>
    </li>
  )
}

function AppealRow({ appeal }: { appeal: Appeal }) {
  return (
    <li>
      <Link to={`/members/staff/appeals/${appeal.id}`} className="flex flex-col gap-1 p-3 hover:bg-surface sm:flex-row sm:items-center sm:gap-4">
        <span className="w-28 shrink-0 text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Appeal</span>
        <span className="min-w-0 flex-1">
          <span className="block font-semibold text-fg">
            {appeal.action.kind_label}
            {appeal.action.member && <span className="font-normal text-fg-muted"> · {appeal.action.member.display_name}</span>}
          </span>
          <span className="block text-sm text-fg-muted">
            {appeal.status_label}
            {appeal.action.created_by && ` · action by ${appeal.action.created_by.display_name}`}
          </span>
        </span>
        <span className="shrink-0 text-sm text-fg-muted">
          {formatDay(appeal.created_at)}
          {appeal.assigned_to && ` · ${appeal.assigned_to.display_name}`}
        </span>
      </Link>
    </li>
  )
}

/** The inbox: reports by status, and appeals. Content stays hidden until a report is opened. */
export function StaffReportsPage() {
  const [params, setParams] = useSearchParams()
  const requested = params.get('tab')
  const tab: Tab = isTab(requested) ? requested : 'open'
  const reports = useAsync(() => (tab === 'appeals' ? Promise.resolve([]) : staffApi.reports(tab)), `reports:${tab}`)
  const appeals = useAsync(() => (tab === 'appeals' ? staffApi.appeals('open') : Promise.resolve([])), `appeals:${tab}`)
  const state = tab === 'appeals' ? appeals : reports

  return (
    <StaffFrame title="Reports">
      <div role="tablist" aria-label="Show" className="flex flex-wrap gap-2">
        {TABS.map((option) => (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={tab === option.value}
            onClick={() => setParams({ tab: option.value }, { replace: true })}
            className={cn('h-8 rounded-full border px-3.5 text-sm font-semibold', tab === option.value ? 'border-fg bg-fg text-canvas' : 'border-border text-fg hover:border-fg-muted')}
          >
            {option.label}
          </button>
        ))}
      </div>
      <div className="mt-4">
        {state.status === 'loading' && <LoadingState label="Loading" />}
        {state.status === 'error' && <ErrorState title="The inbox did not load" onRetry={state.retry} />}
        {state.status === 'success' &&
          (state.data.length === 0 ? (
            <EmptyState
              title={tab === 'appeals' ? 'No appeals waiting' : tab === 'open' ? 'No reports yet' : 'Nothing here'}
              message={
                tab === 'appeals'
                  ? 'Appeals members send about a decision appear here.'
                  : tab === 'open'
                    ? 'New reports from members and the website appear here.'
                    : 'No reports have this status.'
              }
            />
          ) : (
            <ul className="divide-y divide-border rounded-app border border-border">
              {tab === 'appeals'
                ? (appeals.status === 'success' ? appeals.data : []).map((appeal) => <AppealRow key={appeal.id} appeal={appeal} />)
                : (reports.status === 'success' ? reports.data : []).map((report) => <ReportRow key={report.id} report={report} />)}
            </ul>
          ))}
        <AgeCheckSettingCard />
      </div>
    </StaffFrame>
  )
}
