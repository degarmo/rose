const dateFormatter = new Intl.DateTimeFormat('en-US', {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
  timeZone: 'America/Chicago',
})

const timeFormatter = new Intl.DateTimeFormat('en-US', {
  hour: 'numeric',
  minute: '2-digit',
  timeZone: 'America/Chicago',
})

export function formatEventDate(iso: string): string {
  const date = new Date(iso)
  return `${dateFormatter.format(date)}, ${timeFormatter.format(date)}`
}

export function paragraphs(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean)
}

export function isExternalUrl(url: string): boolean {
  return /^(https?:|mailto:)/i.test(url)
}

const CHICAGO = 'America/Chicago'

const partsFormatter = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  timeZone: CHICAGO,
})

const keyFormatter = new Intl.DateTimeFormat('en-CA', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  timeZone: CHICAGO,
})

const longDateFormatter = new Intl.DateTimeFormat('en-US', {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
  timeZone: CHICAGO,
})

/** Calendar-card pieces in Chicago time: { weekday: 'Thu', month: 'Oct', day: '29' }. */
export function dateParts(iso: string) {
  const parts = Object.fromEntries(
    partsFormatter.formatToParts(new Date(iso)).map((part) => [part.type, part.value]),
  )
  return { weekday: parts.weekday ?? '', month: parts.month ?? '', day: parts.day ?? '' }
}

/** YYYY-MM-DD of the moment in Chicago, for grouping events by day. */
export function chicagoDateKey(iso: string | Date): string {
  return keyFormatter.format(typeof iso === 'string' ? new Date(iso) : iso)
}

/** "7:00–9:00 PM", or "9:00 PM–1:00 AM" when the evening crosses noon or midnight. */
export function formatTimeRange(startIso: string, endIso: string): string {
  const start = timeFormatter.format(new Date(startIso))
  const end = timeFormatter.format(new Date(endIso))
  const [startTime, startHalf] = start.split(' ')
  const endHalf = end.split(' ')[1]
  return startHalf === endHalf ? `${startTime}\u2013${end}` : `${start}\u2013${end}`
}

export function formatLongDate(iso: string): string {
  return longDateFormatter.format(new Date(iso))
}

const shortDateFormatter = new Intl.DateTimeFormat('en-US', {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  timeZone: CHICAGO,
})

/** "Thu, Oct 22" in Chicago time, as on cards. */
export function formatShortDate(iso: string): string {
  return shortDateFormatter.format(new Date(iso))
}

const relativeFormatter = new Intl.RelativeTimeFormat('en-US', { numeric: 'auto' })

const RELATIVE_STEPS: Array<[Intl.RelativeTimeFormatUnit, number]> = [
  ['year', 365 * 24 * 3600],
  ['month', 30 * 24 * 3600],
  ['week', 7 * 24 * 3600],
  ['day', 24 * 3600],
  ['hour', 3600],
  ['minute', 60],
]

export function relativeDate(iso: string, now: Date = new Date()): string {
  const seconds = (new Date(iso).getTime() - now.getTime()) / 1000
  for (const [unit, size] of RELATIVE_STEPS) {
    if (Math.abs(seconds) >= size) return relativeFormatter.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}

/** Only same-site paths are allowed as a post-login destination. */
export function safeNextPath(value: string | null | undefined, fallback = '/members/home'): string {
  if (!value || !value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) {
    return fallback
  }
  return value
}

/** Read `key=value` pairs from the URL fragment, where emailed tokens are kept. */
export function fragmentParams(hash: string): URLSearchParams {
  return new URLSearchParams(hash.replace(/^#/, ''))
}

const dayFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'long',
  day: 'numeric',
  year: 'numeric',
  timeZone: CHICAGO,
})

/** "October 18, 2026" in Chicago time. */
export function formatDay(iso: string): string {
  return dayFormatter.format(new Date(iso))
}

/** "$25" for whole amounts, "$25.50" otherwise. */
export function formatMoney(cents: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: cents % 100 === 0 ? 0 : 2,
  }).format(cents / 100)
}
