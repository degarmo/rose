import { Download } from 'lucide-react'
import { useState } from 'react'
import { Navigate } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { AppButton } from '@/components/members/app/primitives'
import { BarChart } from '@/components/members/staff/BarChart'
import { countText, moneyText } from '@/components/members/staff/format'
import { StaffFrame } from '@/components/members/staff/StaffFrame'
import { useToast } from '@/components/ui'
import { cn } from '@/lib/cn'
import { formatDay } from '@/lib/format'
import { atLeast, staffApi, type Count, type Metrics, type MetricsRange } from '@/lib/safetyApi'
import { useAsync } from '@/lib/useAsync'

const RANGES: Array<{ value: MetricsRange; label: string }> = [
  { value: '30d', label: '30 days' },
  { value: '90d', label: '90 days' },
  { value: '12m', label: '12 months' },
]

const TH = 'py-2 pr-3 text-left text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted'
const TD = 'py-2 pr-3 text-left text-fg'

function Tile({ label, count }: { label: string; count: Count }) {
  return (
    <div className="rounded-app border border-border p-4">
      <p className="text-sm text-fg-muted">{label}</p>
      <p className={cn('mt-1 font-semibold text-fg', count.value === null ? 'text-base' : 'text-2xl')}>{countText(count)}</p>
    </div>
  )
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section aria-label={title} className="flex flex-col gap-3">
      <h2 className="text-base font-semibold text-fg">{title}</h2>
      {children}
    </section>
  )
}

function Dashboard({ data }: { data: Metrics }) {
  const members = data.members
  return (
    <div className="flex flex-col gap-8">
      <p className="text-sm text-fg-muted">Counts below {data.small} show as &ldquo;fewer than {data.small}&rdquo;. Nothing here names a person.</p>

      <Panel title={`Members · ${members.month}`}>
        <div className="grid gap-3 sm:grid-cols-3">
          <Tile label="Active members" count={members.total_active} />
          <Tile label="Email list" count={data.email_list} />
          <Tile label="Open reports" count={data.feed.open_reports} />
        </div>
        <div className="overflow-x-auto rounded-app border border-border px-3">
          <table className="w-full min-w-[520px] text-sm">
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className={TH}>
                  Tier
                </th>
                {['Active', 'New', 'Renewing', 'Lapsing', 'Expired'].map((label) => (
                  <th key={label} scope="col" className={TH}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {members.tiers.map((row) => (
                <tr key={row.tier} className="border-b border-border last:border-0">
                  <th scope="row" className={cn(TD, 'font-semibold')}>
                    {row.tier}
                  </th>
                  {[row.active, row.new, row.renewing, row.lapsing, row.expired].map((count, index) => (
                    <td key={index} className={cn(TD, count.value === null && 'text-fg-muted')}>
                      {countText(count)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Revenue">
        <div className="grid gap-3 md:grid-cols-2">
          {(['this_month', 'last_month'] as const).map((key) => {
            const block = data.revenue[key]
            return (
              <div key={key} className="rounded-app border border-border px-3">
                <table className="w-full text-sm">
                  <caption className="py-2 text-left text-sm font-semibold text-fg">{block.month}</caption>
                  <tbody>
                    {block.rows.map((row) => (
                      <tr key={row.label} className="border-t border-border">
                        <th scope="row" className={cn(TD, 'font-normal')}>
                          {row.label}
                        </th>
                        <td className={cn(TD, 'text-right', row.cents === null && 'text-fg-muted')}>{moneyText(row)}</td>
                      </tr>
                    ))}
                    <tr className="border-t border-border">
                      <th scope="row" className={cn(TD, 'font-semibold')}>
                        Total
                      </th>
                      <td className={cn(TD, 'text-right font-semibold')}>{moneyText(block.total)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )
          })}
        </div>
      </Panel>

      <Panel title="Over time">
        <div className="grid gap-3 md:grid-cols-2">
          <BarChart title="Revenue" points={data.series.map((p) => ({ label: p.label, metric: p.revenue }))} />
          <BarChart title="Payments" points={data.series.map((p) => ({ label: p.label, metric: p.payments }))} />
          <BarChart title="RSVPs" points={data.series.map((p) => ({ label: p.label, metric: p.rsvps }))} />
          <BarChart title="Feed posts" points={data.series.map((p) => ({ label: p.label, metric: p.posts }))} />
        </div>
      </Panel>

      <Panel title="Feed">
        <div className="grid gap-3 sm:grid-cols-3">
          <Tile label="Posts" count={data.feed.posts} />
          <Tile label="Comments" count={data.feed.comments} />
          <Tile label="Active posters this week" count={data.feed.active_posters_week} />
        </div>
      </Panel>

      <Panel title="Events">
        {data.events.length === 0 ? (
          <p className="text-sm text-fg-muted">No events in this period.</p>
        ) : (
          <div className="overflow-x-auto rounded-app border border-border px-3">
            <table className="w-full min-w-[460px] text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th scope="col" className={TH}>
                    Event
                  </th>
                  <th scope="col" className={TH}>
                    Date
                  </th>
                  <th scope="col" className={TH}>
                    RSVPs
                  </th>
                  <th scope="col" className={TH}>
                    Check-ins
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.events.map((event) => (
                  <tr key={`${event.title}-${event.starts_at}`} className="border-b border-border last:border-0">
                    <th scope="row" className={cn(TD, 'font-normal')}>
                      {event.title}
                    </th>
                    <td className={cn(TD, 'whitespace-nowrap text-fg-muted')}>{formatDay(event.starts_at)}</td>
                    <td className={TD}>{countText(event.rsvps)}</td>
                    <td className={TD}>{event.check_ins ? countText(event.check_ins) : 'Not yet'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}

/** /members/staff: the metrics for staff and admins; moderators start at the reports. */
export function StaffDashboardPage() {
  const auth = useAuth()
  const toast = useToast()
  const [range, setRange] = useState<MetricsRange>('30d')
  const allowed = atLeast(auth.user?.staff?.role, 'staff') && Boolean(auth.user?.staff?.verified)
  const state = useAsync(() => (allowed ? staffApi.metrics(range) : Promise.resolve(null)), `metrics:${range}:${allowed}`)

  if (auth.user?.staff?.role === 'moderator' && auth.user.staff.verified) return <Navigate to="/members/staff/reports" replace />

  async function exportCsv() {
    try {
      const blob = await staffApi.exportMetrics(range)
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `metrics-${range}.csv`
      link.click()
      URL.revokeObjectURL(link.href)
    } catch {
      toast.show({ tone: 'error', title: 'The export did not download' })
    }
  }

  return (
    <StaffFrame
      title="Dashboard"
      minimum="staff"
      actions={
        <div className="flex items-center gap-2">
          <div role="group" aria-label="Period" className="flex rounded-app border border-border p-0.5">
            {RANGES.map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={range === option.value}
                onClick={() => setRange(option.value)}
                className={cn('h-7 rounded-[6px] px-3 text-sm font-semibold', range === option.value ? 'bg-fg text-canvas' : 'text-fg-muted hover:text-fg')}
              >
                {option.label}
              </button>
            ))}
          </div>
          <AppButton variant="secondary" onClick={() => void exportCsv()}>
            <Download aria-hidden="true" className="size-4" />
            Export
          </AppButton>
        </div>
      }
    >
      {state.status === 'loading' && <LoadingState label="Loading the numbers" />}
      {state.status === 'error' && <ErrorState title="The numbers did not load" onRetry={state.retry} />}
      {state.status === 'success' && state.data && <Dashboard data={state.data} />}
    </StaffFrame>
  )
}
