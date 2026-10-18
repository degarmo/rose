import { chicagoDateKey } from './format'

export interface MonthRef {
  year: number
  month: number
}

function pad(value: number) {
  return String(value).padStart(2, '0')
}

export function monthKey({ year, month }: MonthRef) {
  return `${year}-${pad(month + 1)}`
}

export function parseMonth(value: string | null, today: Date = new Date()): MonthRef {
  const match = value?.match(/^(\d{4})-(\d{2})$/)
  if (match) {
    const month = Number(match[2]) - 1
    if (month >= 0 && month <= 11) return { year: Number(match[1]), month }
  }
  const [year, month] = chicagoDateKey(today).split('-').map(Number)
  return { year, month: month - 1 }
}

export function shiftMonth({ year, month }: MonthRef, delta: number): MonthRef {
  const index = year * 12 + month + delta
  return { year: Math.floor(index / 12), month: index % 12 }
}

/** The six-week grid (Sunday first) that covers the month, as YYYY-MM-DD keys. */
export function monthGrid({ year, month }: MonthRef): string[] {
  const first = new Date(Date.UTC(year, month, 1))
  const start = new Date(first)
  start.setUTCDate(1 - first.getUTCDay())
  return Array.from({ length: 42 }, (_, index) => {
    const day = new Date(start)
    day.setUTCDate(start.getUTCDate() + index)
    return `${day.getUTCFullYear()}-${pad(day.getUTCMonth() + 1)}-${pad(day.getUTCDate())}`
  })
}
