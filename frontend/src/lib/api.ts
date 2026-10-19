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
  nonprofit_status_text: string
  social_links: SocialLink[]
}

export interface StaffProfile {
  slug: string
  display_name: string
  role_title: string
  bio: string
  photo: RemoteImage | null
}

export type RentalType = 'private_session' | 'workshop' | 'photoshoot' | 'group_event' | 'other'

export interface RentalInquiryPayload {
  contact_name: string
  contact_email: string
  contact_phone: string
  type: RentalType | ''
  preferred_date: string
  alternate_date: string | null
  start_time: string
  duration_hours: number | null
  party_size: number | null
  notes: string
  photoshoot_acknowledged: boolean
  website: string
}

export interface Choice {
  value: string
  label: string
}

export interface VolunteerOptions {
  interests: Choice[]
  availability: Choice[]
}

export interface VolunteerPayload {
  contact_name: string
  contact_email: string
  interests: string[]
  availability: string[]
  experience_note: string
  website: string
}

export interface DonationOptions {
  online: boolean
  presets_cents: number[]
  minimum_cents: number
  maximum_cents: number
  nonprofit_status: string
  check_payable_to: string
  mailing_address: string
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
  /** Set for public images: the original's size and narrower copies for srcset. */
  width?: number | null
  height?: number | null
  srcset?: string | null
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
  members_only: boolean
  /** True when the class is members-only and this visitor is not entitled. */
  locked: boolean
  paywall: { tiers: string[]; benefit: string } | null
}

export interface OpportunityDetail extends Opportunity {
  /** Withheld by the server when the class is locked. */
  body: string | null
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

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      credentials: 'same-origin',
      referrerPolicy: 'same-origin',
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

/** Login and logout rotate the token; responses that carry one replace ours. */
function rememberCsrf(body: unknown) {
  if (body && typeof body === 'object' && 'csrfToken' in body) {
    csrfToken = String((body as { csrfToken: string }).csrfToken)
  }
}

async function getCsrfToken(): Promise<string> {
  if (!csrfToken) {
    const data = await request<{ csrfToken: string }>('/csrf/')
    csrfToken = data.csrfToken
  }
  return csrfToken
}

export async function send<T>(method: 'POST' | 'PATCH' | 'DELETE', path: string, payload?: unknown): Promise<T> {
  const attempt = async () => {
    const body = await request<T>(path, {
      method,
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': await getCsrfToken() },
      body: payload === undefined ? undefined : JSON.stringify(payload),
    })
    rememberCsrf(body)
    return body
  }
  try {
    return await attempt()
  } catch (error) {
    // A stale token (for example after the cookie expired) gets one retry.
    if (error instanceof ApiError && error.status === 403 && /CSRF/i.test(error.message)) {
      csrfToken = null
      return attempt()
    }
    throw error
  }
}

export const post = <T,>(path: string, payload: unknown = {}) => send<T>('POST', path, payload)

/** Multipart upload with the CSRF header. The browser sets the boundary. */
export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const attempt = async () =>
    request<T>(path, {
      method: 'POST',
      headers: { 'X-CSRFToken': await getCsrfToken() },
      body: form,
    })
  try {
    return await attempt()
  } catch (error) {
    if (error instanceof ApiError && error.status === 403 && /CSRF/i.test(error.message)) {
      csrfToken = null
      return attempt()
    }
    throw error
  }
}

/** POST that returns a file, for single-use downloads. */
export async function postForBlob(path: string, payload: unknown): Promise<Blob> {
  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    method: 'POST',
    credentials: 'same-origin',
    referrerPolicy: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': await getCsrfToken() },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    let message = 'This download link has expired or was already used.'
    try {
      message = ((await response.json()) as { detail?: string }).detail ?? message
    } catch {
      // Not JSON: keep the default message.
    }
    throw new ApiError(response.status, message)
  }
  return response.blob()
}

function query(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value)
  }
  const result = search.toString()
  return result ? `?${result}` : ''
}

export interface Account {
  display_name: string
  email: string
  email_verified: boolean
  /** Any membership, current or past. Only ever the signed-in person's own. */
  has_membership: boolean
  /** Set for staff only: where the staff guide lives in the admin. */
  staff_guide_url: string | null
  /** The member app opens for them (entitled and joined): the header shows "My feed". */
  feed_access: boolean
  /** The account page has feed controls for them (entitled, or with feed history). */
  feed_controls: boolean
  appearance: Appearance
}

export type Appearance = 'light' | 'dark'

export interface Session {
  user: Account | null
  csrfToken: string
}

export interface Detail {
  detail: string
}

export type EventCategory = 'education' | 'social' | 'workshop' | 'member_night' | 'special'
export type EventAudience = 'public' | 'account' | 'members'

export type RSVPStateName =
  | 'open'
  | 'waitlist'
  | 'full'
  | 'closed'
  | 'members_only'
  | 'not_open_yet'
  | 'unavailable'
  | 'going'
  | 'waitlisted'

export type RSVPReason =
  | 'ok'
  | 'login_required'
  | 'unverified'
  | 'closed'
  | 'members_only'
  | 'not_open_yet'
  | 'unavailable'

export interface MyRSVP {
  status: 'going' | 'waitlist'
  party_size: number
  note_to_hosts: string
}

export interface RSVPState {
  state: RSVPStateName
  can_rsvp: boolean
  reason: RSVPReason
  opens_at: string | null
  closes_at: string
  max_party_size: number
  mine: MyRSVP | null
}

export interface EventSummary {
  id: number
  slug: string
  title: string
  summary: string
  category: EventCategory
  category_label: string
  audience: EventAudience
  starts_at: string
  ends_at: string
  location_label: string
  hero_image: RemoteImage | null
  rsvp: RSVPState
  attendee_count: number | null
}

export interface EventDetail extends EventSummary {
  body: string
  opportunity: { slug: string; title: string } | null
}

export interface MyRSVPItem extends MyRSVP {
  event: { slug: string; title: string; starts_at: string; ends_at: string; location_label: string }
}

export interface JournalPost {
  slug: string
  caption_html: string
  published_at: string
  author: string | null
  images: RemoteImage[]
  event: { slug: string; title: string; starts_at: string } | null
  cta: { label: string; url: string } | null
}

export interface Page<T> {
  next: string | null
  previous: string | null
  results: T[]
}

function cursorFrom(url: string | null): string | null {
  if (!url) return null
  return new URL(url, window.location.origin).searchParams.get('cursor')
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
  staff: () => request<StaffProfile[]>('/staff/'),
  sendRentalInquiry: (payload: RentalInquiryPayload) => post<Detail>('/rentals/inquiries/', payload),
  volunteerOptions: () => request<VolunteerOptions>('/volunteer/options/'),
  sendVolunteerSignup: (payload: VolunteerPayload) => post<Detail>('/volunteer/signup/', payload),
  donationOptions: () => request<DonationOptions>('/donations/options/'),
  startDonation: (payload: { amount_cents: number; email: string; show_name: boolean; website: string }) =>
    post<{ redirect_url: string }>('/donations/checkout/', payload),
  subscribe: (email: string, website: string) => post<Detail>('/newsletter/subscribe/', { email, website }),
  confirmSubscription: (token: string) => post<Detail>('/newsletter/confirm/', { token }),
  unsubscribe: (token: string) => post<Detail>('/newsletter/unsubscribe/', { token }),
  opportunities: (filters: OpportunityFilters = {}) =>
    request<Opportunity[]>(
      `/education/opportunities/${query({ category: filters.category, level: filters.level })}`,
    ),
  opportunity: (slug: string) =>
    request<OpportunityDetail>(`/education/opportunities/${encodeURIComponent(slug)}/`),
  sendContactMessage: (payload: ContactPayload) => post<{ ok: true }>('/contact/', payload),

  session: async () => {
    const body = await request<Session>('/account/session/')
    rememberCsrf(body)
    return body
  },
  register: (payload: { email: string; display_name: string; password: string }) =>
    post<Detail>('/account/register/', payload),
  verifyEmail: (token: string) => post<Detail>('/account/verify-email/', { token }),
  resendVerification: () => post<Detail>('/account/verify-email/resend/'),
  login: (email: string, password: string) => post<Session>('/account/login/', { email, password }),
  logout: () => post<Session>('/account/logout/'),
  requestPasswordReset: (email: string) => post<Detail>('/account/password-reset/', { email }),
  confirmPasswordReset: (uid: string, token: string, new_password: string) =>
    post<Detail>('/account/password-reset/confirm/', { uid, token, new_password }),
  changePassword: (current_password: string, new_password: string) =>
    post<Session>('/account/password/', { current_password, new_password }),
  changeDisplayName: (display_name: string) =>
    send<Session>('PATCH', '/account/session/', { display_name }),
  changeAppearance: (appearance: Appearance) => send<Session>('PATCH', '/account/session/', { appearance }),
  deleteAccount: (password: string) => post<Session>('/account/delete/', { password }),
  signOutEverywhere: () => post<Session>('/account/sign-out-everywhere/'),
  myRSVPs: () => request<MyRSVPItem[]>('/account/rsvps/'),

  events: (category: EventCategory | '' = '') =>
    request<EventSummary[]>(`/events/${query({ category })}`),
  eventCalendar: (start: string, end: string, category: EventCategory | '' = '') =>
    request<EventSummary[]>(`/events/calendar/${query({ start, end, category })}`),
  event: (slug: string) => request<EventDetail>(`/events/${encodeURIComponent(slug)}/`),
  rsvp: (slug: string, party_size: number, note_to_hosts: string) =>
    post<{ rsvp: RSVPState }>(`/events/${encodeURIComponent(slug)}/rsvp/`, {
      party_size,
      note_to_hosts,
    }),
  cancelRSVP: (slug: string) =>
    send<{ rsvp: RSVPState }>('DELETE', `/events/${encodeURIComponent(slug)}/rsvp/`),
  cancelByToken: (token: string) =>
    post<Detail & { event: { slug: string; title: string; starts_at: string } }>(
      '/events/rsvp/cancel/',
      { token },
    ),
  icsUrl: (slug: string, includeDetails: boolean) =>
    `${config.apiBaseUrl}/events/${encodeURIComponent(slug)}/calendar.ics${includeDetails ? '?details=1' : ''}`,

  journal: async (cursor: string | null = null) => {
    const page = await request<Page<JournalPost>>(`/journal/posts/${query({ cursor: cursor ?? undefined })}`)
    return { posts: page.results, nextCursor: cursorFrom(page.next) }
  },
  journalPost: (slug: string) => request<JournalPost>(`/journal/posts/${encodeURIComponent(slug)}/`),
}
