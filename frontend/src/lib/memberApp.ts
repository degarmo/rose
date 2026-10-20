import type { Account } from './api'

/** Where the member app starts for this person: the feed, joining it, or Home. */
export function memberAppPath(user: Pick<Account, 'member_app'>) {
  if (user.member_app === 'open') return '/members/feed'
  if (user.member_app === 'join') return '/members/join-feed'
  return '/members/home'
}

/**
 * Where to go after logging in. A page the person was on wins; with none (or the home
 * page, where the header's Log in starts): Admin and Staff (superusers included) land on
 * the admin dashboard, the only dashboard (an absolute address, outside this app);
 * moderators on the reports inbox; door volunteers on the door desk; members whose feed is
 * open in it; everyone else on Home.
 */
export function landingAfterLogin(user: Pick<Account, 'member_app' | 'staff'> | null, asked: string | null, next: string) {
  const defaulted = !asked || asked === '/'
  if (!defaulted) return next
  const staff = user?.staff
  if (staff?.role === 'admin' || staff?.role === 'staff') return staff.admin_url
  if (staff?.role === 'moderator') return '/members/staff/reports'
  // A door volunteer (no team role) works the door.
  if (staff) return '/members/staff/door'
  if (user?.member_app === 'open') return '/members/feed'
  return '/members/home'
}
