import type { Count, Money } from '@/lib/safetyApi'
import { countText, moneyText } from './format'

type Point = { label: string; metric: Count | Money }

function amount(metric: Count | Money) {
  return 'cents' in metric ? metric.cents : metric.value
}

/**
 * A plain bar chart, one bar per period. A withheld period (fewer than 5) is a short
 * hatched bar, so the chart never implies a small number it does not show.
 */
export function BarChart({ title, points }: { title: string; points: Point[] }) {
  const known = points.map((p) => amount(p.metric)).filter((v): v is number => v !== null)
  const max = Math.max(1, ...known)
  return (
    <figure className="flex flex-col gap-3 rounded-app border border-border p-4">
      <figcaption className="text-sm font-semibold text-fg">{title}</figcaption>
      <div className="flex h-32 items-end gap-1" role="img" aria-label={`${title}: ${points.map((p) => `${p.label} ${'cents' in p.metric ? moneyText(p.metric) : countText(p.metric)}`).join('; ')}`}>
        {points.map((point) => {
          const value = amount(point.metric)
          const withheld = value === null
          const height = withheld ? 8 : Math.max(2, Math.round((value / max) * 100))
          return (
            <div key={point.label} className="flex h-full min-w-0 flex-1 flex-col justify-end" title={`${point.label}: ${'cents' in point.metric ? moneyText(point.metric) : countText(point.metric)}`}>
              <div
                className={withheld ? 'rounded-t-[2px] bg-[repeating-linear-gradient(135deg,var(--color-border)_0_3px,transparent_3px_6px)]' : 'rounded-t-[2px] bg-primary'}
                style={{ height: `${height}%` }}
              />
            </div>
          )
        })}
      </div>
      <div className="flex justify-between text-[0.6875rem] text-fg-muted">
        <span>{points[0]?.label}</span>
        <span>{points.at(-1)?.label}</span>
      </div>
    </figure>
  )
}
