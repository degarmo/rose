import type { Account } from './api'

/** Where the member app starts for this person: the feed, or joining it first. */
export function memberAppPath(user: Pick<Account, 'member_app'>) {
  return user.member_app === 'open' ? '/members/feed' : '/members/join-feed'
}

/**
 * Where to go after logging in. A page the person was on wins; with none (or the home
 * page, where the header's Log in starts), members whose app is open land in it.
 */
export function landingAfterLogin(user: Pick<Account, 'member_app'> | null, asked: string | null, next: string) {
  const defaulted = !asked || asked === '/'
  if (defaulted && user?.member_app === 'open') return '/members/feed'
  return next
}
