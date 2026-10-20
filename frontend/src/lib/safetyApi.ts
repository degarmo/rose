import { post, postForBlob, request } from './api'

export type Role = 'moderator' | 'staff' | 'admin'

/** On the signed-in person's own session: their team role and whether this session passed
 * the staff two-step login. */
export interface StaffSession {
  /** Null for a door volunteer: the door desk without a team role. */
  role: Role | null
  /** May use the door desk (the admin's and /members/staff/door). */
  door_desk: boolean
  verified: boolean
  /** Where to complete the two-step login when not yet verified. */
  verify_url: string | null
  /** No authenticator yet: the two-step login starts by setting one up. */
  needs_enrollment: boolean
  /** The Django admin's home, and the door desk for those who may use it. */
  admin_url: string
  door_desk_url: string | null
}

export const ROLE_LABELS: Record<Role, string> = { moderator: 'Moderator', staff: 'Staff', admin: 'Admin' }
const RANK: Record<Role, number> = { moderator: 1, staff: 2, admin: 3 }

export function atLeast(role: Role | null | undefined, minimum: Role) {
  return Boolean(role && RANK[role] >= RANK[minimum])
}

/** A count withheld below five: value null with fewer_than set. */
export interface Count {
  value: number | null
  fewer_than?: number
}

export interface Money {
  cents: number | null
  fewer_than?: number
}

export type MetricsRange = '30d' | '90d' | '12m'

export interface Metrics {
  range: MetricsRange
  generated_at: string
  small: number
  members: {
    month: string
    total_active: Count
    tiers: Array<{ tier: string; active: Count; new: Count; renewing: Count; lapsing: Count; expired: Count }>
  }
  revenue: Record<'this_month' | 'last_month', { month: string; rows: Array<{ label: string } & Money>; total: Money }>
  events: Array<{ title: string; starts_at: string; rsvps: Count; check_ins: Count | null }>
  feed: { posts: Count; comments: Count; active_posters_week: Count; open_reports: Count }
  email_list: Count
  series: Array<{ label: string; payments: Count; revenue: Money; rsvps: Count; posts: Count }>
}

export interface Overview {
  role: Role
  open_reports: number
  open_appeals: number
  can_see_metrics: boolean
  can_manage_team: boolean
}

export type ReportStatus = 'open' | 'in_review' | 'resolved' | 'dismissed'
export type ReportKind = 'post' | 'comment' | 'profile' | 'event'

export interface Person {
  display_name: string
}

export interface ReportSummary {
  id: number
  kind: ReportKind
  kind_label: string
  reason: string
  reason_label: string
  status: ReportStatus
  status_label: string
  created_at: string
  assigned_to: Person | null
  /** The reported member, or the name a concern gives. */
  subject: string | null
  subject_is_member: boolean
  preview: string
  from_website: boolean
}

export type ActionKind = 'warning' | 'remove_content' | 'feed_suspension' | 'event_suspension' | 'ban'

export interface AppealState {
  id: number
  status: 'open' | 'upheld' | 'reversed'
  status_label: string
  created_at: string
  decided_at: string | null
}

export interface MemberActionData {
  id: number
  kind: ActionKind
  kind_label: string
  rule: string
  reason: string
  created_at: string
  ends_at: string | null
  in_force: boolean
  reversed_at: string | null
  reversal_reason: string
  appeal: AppealState | null
  created_by?: Person | null
  reversed_by?: Person | null
  member?: Person | null
  report_id?: number | null
}

export interface ReportContent {
  caption?: string
  status?: string
  is_sensitive?: boolean
  images?: string[]
  body?: string
  post_caption?: string
  bio?: string
  has_avatar?: boolean
  event?: string | null
  event_starts_at?: string | null
  event_date?: string | null
  reported_name?: string
  removed?: boolean
}

export interface ReportDetail extends ReportSummary {
  details: string
  content: ReportContent
  reporter: { hidden: true; can_reveal: boolean }
  member: { display_name: string; prior_reports: number; actions: MemberActionData[] } | null
  notes: Array<{ author: Person | null; body: string; created_at: string }>
  actions: MemberActionData[]
  team: Person[]
}

export interface Appeal {
  id: number
  status: 'open' | 'upheld' | 'reversed'
  status_label: string
  text: string
  created_at: string
  assigned_to: Person | null
  decided_by: Person | null
  decided_at: string | null
  decision_note: string
  action: MemberActionData
  may_decide: boolean
}

export interface StaffMember {
  display_name: string
  membership: { tier: string; status: string } | null
  flags: { feed_suspended_until: string | null; events_suspended_until: string | null; banned: boolean }
  reports_about: number
  actions: MemberActionData[]
}

export interface TeamMember {
  display_name: string
  role: Role | null
  is_superuser: boolean
  is_self: boolean
}

export interface ActionRequest {
  kind: ActionKind
  rule: string
  reason: string
  report_id?: number
  days?: number
  until?: string
  block_email?: boolean
}

const s = (path: string) => `/staff/${path}`

export const staffApi = {
  overview: () => request<Overview>(s('overview/')),
  metrics: (range: MetricsRange) => request<Metrics>(s(`metrics/?range=${range}`)),
  exportMetrics: (range: MetricsRange) => postForBlob(s('metrics/export/'), { range }),
  reports: (status: ReportStatus) => request<ReportSummary[]>(s(`reports/?status=${status}`)),
  report: (id: number) => request<ReportDetail>(s(`reports/${id}/`)),
  setStatus: (id: number, status: ReportStatus) => post<ReportDetail>(s(`reports/${id}/status/`), { status }),
  assign: (id: number, assignee: string | null) => post<ReportDetail>(s(`reports/${id}/assign/`), { assignee }),
  addNote: (id: number, body: string) => post<ReportDetail>(s(`reports/${id}/notes/`), { body }),
  revealReporter: (id: number) => post<{ display_name: string | null; contact_email: string }>(s(`reports/${id}/reveal/`)),
  rules: () => request<string[]>(s('rules/')),
  searchMembers: (q: string) => request<Person[]>(s(`members/?q=${encodeURIComponent(q)}`)),
  member: (handle: string) => request<StaffMember>(s(`members/${encodeURIComponent(handle)}/`)),
  act: (handle: string, payload: ActionRequest) => post<MemberActionData>(s(`members/${encodeURIComponent(handle)}/actions/`), payload),
  reverse: (id: number, reason: string) => post<MemberActionData>(s(`actions/${id}/reverse/`), { reason }),
  appeals: (status: Appeal['status']) => request<Appeal[]>(s(`appeals/?status=${status}`)),
  appeal: (id: number) => request<Appeal>(s(`appeals/${id}/`)),
  decide: (id: number, decision: 'uphold' | 'reverse', note: string) => post<Appeal>(s(`appeals/${id}/decide/`), { decision, note }),
  team: () => request<TeamMember[]>(s('team/')),
  setRole: (person: string, role: Role | null) => post<TeamMember[]>(s('team/'), { person, role }),
}

/** One membership as the door sees it (apps.memberships.door_api.card_payload). */
export interface DoorCard {
  id: number
  reference_code: string
  display_name: string
  tier: { name: string; price: string; currency: string; interval: string; guests_included: number; guest_discount: boolean; is_free: boolean }
  status: 'pending_payment' | 'active' | 'grace' | 'expired' | 'cancelled' | 'suspended'
  status_label: string
  source_label: string
  is_guest_pass: boolean
  id_checked: boolean
  paid_awaiting_id_check: boolean
  period_end: string | null
  /** Members-only events left this month; null is unlimited (or a guest pass). */
  events_remaining: number | null
  do_not_admit: boolean
  events_suspended_until: string | null
  default_amount: string
  actions: DoorAction[]
  payments: Array<{ id: number; date: string; status: string; status_label: string; method_label: string; amount: string; refundable: boolean }>
}

export type DoorAction = 'activate_paid' | 'activate' | 'guest_visit' | 'walk_in' | 'renew' | 'comp' | 'suspend' | 'reinstate'

export interface DoorSearch {
  query: string
  results: DoorCard[]
  tonight_events: Array<{ id: number; title: string; starts_at: string }>
  donation_methods: Array<{ value: string; label: string }>
  join_url: string | null
  join_qr: string | null
}

/** Everything the door can send: the action and the fields it needs. */
export interface DoorRequest {
  action: DoorAction | 'show_signature' | 'refund' | 'record_donation'
  membership?: number
  payment?: number
  method?: string
  amount?: string
  note?: string
  reason?: string
  id_checked?: boolean
  event?: number
  party_size?: number
  donor_display?: string
  acknowledgement_email?: string
}

export const doorApi = {
  search: (q: string) => request<DoorSearch>(`/staff/door/?q=${encodeURIComponent(q)}`),
  act: (payload: DoorRequest) => post<{ message?: string; signature?: { membership: number; name: string } }>('/staff/door/', payload),
}

export interface MyReport {
  id: number
  kind_label: string
  created_at: string
  status: 'received' | 'reviewed'
}

export interface ConcernPayload {
  details: string
  event?: string
  event_date?: string
  reported_name?: string
  contact_email?: string
  website?: string
}

export const safetyApi = {
  notices: () => request<MemberActionData[]>('/account/notices/'),
  markNoticesSeen: () => post<{ unread_notices: 0 }>('/account/notices/seen/'),
  appeal: (id: number, text: string) => post<MemberActionData>(`/account/notices/${id}/appeal/`, { text }),
  myReports: () => request<MyReport[]>('/account/reports/'),
  concern: (payload: ConcernPayload) => post<{ ok: true }>('/concerns/', payload),
}
