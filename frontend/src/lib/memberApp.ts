import type { Account } from './api'

/** Where the member app starts for this person: the feed, joining it, or Home. */
export function memberAppPath(user: Pick<Account, 'member_app'>) {
  if (user.member_app === 'open') return '/members/feed'
  if (user.member_app === 'join') return '/members/join-feed'
  return '/members/home'
}

/**
 * Where to go after logging in. A page the person was on wins; with none (or the home
 * page, where the header's Log in starts), the team and superusers land on the staff
 * dashboard, members whose feed is open land in it, and everyone else lands on Home.
 */
export function landingAfterLogin(user: Pick<Account, 'member_app' | 'staff'> | null, asked: string | null, next: string) {
  const defaulted = !asked || asked === '/'
  if (!defaulted) return next
  if (user?.staff) return '/members/staff'
  if (user?.member_app === 'open') return '/members/feed'
  return '/members/home'
}
