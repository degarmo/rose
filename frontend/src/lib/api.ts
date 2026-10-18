import { config } from './config'

export interface SocialLink {
  label: string
  url: string
}

export interface SiteSettings {
  tagline: string
  hours_text: string
  address_text: string
  directions_text: string
  contact_email: string
  quick_exit_url: string
  social_links: SocialLink[]
}

export interface FAQItem {
  id: number
  question: string
  answer: string
}

export type OpportunityCategory = 'class' | 'workshop' | 'mentorship' | 'volunteer' | 'other'
export type OpportunityLevel = 'beginner' | 'intermediate' | 'advanced' | 'all'

export interface RemoteImage {
  url: string
  alt: string
}

export interface Opportunity {
  id: number
  title: string
  slug: string
  summary: string
  category: OpportunityCategory
  category_label: string
  level: OpportunityLevel
  level_label: string
  starts_at: string | null
  location_label: string
  cta_label: string
  cta_url: string
  hero_image: RemoteImage | null
}

export interface OpportunityDetail extends Opportunity {
  body: string
}

export interface OpportunityFilters {
  category?: OpportunityCategory | ''
  level?: OpportunityLevel | ''
}

export type ContactTopic = 'general' | 'membership' | 'events' | 'volunteer' | 'concern'

export interface ContactPayload {
  name: string
  email: string
  phone: string
  topic: ContactTopic
  message: string
  website: string
}

export type FieldErrors = Partial<Record<string, string>>

export class ApiError extends Error {
  readonly status: number
  readonly fieldErrors: FieldErrors

  constructor(status: number, message: string, fieldErrors: FieldErrors = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }

  get isNotFound() {
    return this.status === 404
  }

  get isRateLimited() {
    return this.status === 429
  }
}

function parseErrorBody(body: unknown): { message: string; fieldErrors: FieldErrors } {
  const fieldErrors: FieldErrors = {}
  let message = 'Something went wrong. Please try again.'
  if (body && typeof body === 'object') {
    for (const [key, value] of Object.entries(body as Record<string, unknown>)) {
      const text = Array.isArray(value) ? String(value[0]) : String(value)
      if (key === 'detail' || key === 'non_field_errors') message = text
      else fieldErrors[key] = text
    }
  }
  return { message, fieldErrors }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      credentials: 'same-origin',
      referrerPolicy: 'no-referrer',
      ...init,
      headers: { Accept: 'application/json', ...init.headers },
    })
  } catch {
    throw new ApiError(0, 'We could not reach the server. Check your connection and try again.')
  }

  const text = await response.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      throw new ApiError(response.status, 'The server sent an unexpected response.')
    }
  }
  if (!response.ok) {
    const { message, fieldErrors } = parseErrorBody(body)
    throw new ApiError(response.status, message, fieldErrors)
  }
  return body as T
}

let csrfToken: string | null = null

async function getCsrfToken(): Promise<string> {
  if (!csrfToken) {
    const data = await request<{ csrfToken: string }>('/csrf/')
    csrfToken = data.csrfToken
  }
  return csrfToken
}

async function post<T>(path: string, payload: unknown): Promise<T> {
  const send = async () =>
    request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': await getCsrfToken() },
      body: JSON.stringify(payload),
    })
  try {
    return await send()
  } catch (error) {
    // A stale token (for example after the cookie expired) gets one retry.
    if (error instanceof ApiError && error.status === 403) {
      csrfToken = null
      return send()
    }
    throw error
  }
}

function query(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value)
  }
  const result = search.toString()
  return result ? `?${result}` : ''
}

let siteSettingsPromise: Promise<SiteSettings> | null = null

export const api = {
  siteSettings(): Promise<SiteSettings> {
    siteSettingsPromise ??= request<SiteSettings>('/site-settings/').catch((error: unknown) => {
      siteSettingsPromise = null
      throw error
    })
    return siteSettingsPromise
  },
  faqs: () => request<FAQItem[]>('/faqs/'),
  opportunities: (filters: OpportunityFilters = {}) =>
    request<Opportunity[]>(
      `/education/opportunities/${query({ category: filters.category, level: filters.level })}`,
    ),
  opportunity: (slug: string) =>
    request<OpportunityDetail>(`/education/opportunities/${encodeURIComponent(slug)}/`),
  sendContactMessage: (payload: ContactPayload) => post<{ ok: true }>('/contact/', payload),
}
