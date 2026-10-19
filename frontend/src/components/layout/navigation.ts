export interface NavLinkItem {
  to: string
  label: string
}

export interface NavGroup {
  label: string
  items: NavLinkItem[]
}

export type NavEntry = NavLinkItem | NavGroup

export function isGroup(entry: NavEntry): entry is NavGroup {
  return 'items' in entry
}

/** The main navigation. Groups become dropdowns on large screens and sections in the phone menu. */
export const NAV: NavEntry[] = [
  { to: '/', label: 'Home' },
  { to: '/about', label: 'About' },
  { to: '/events', label: 'Events' },
  { to: '/education', label: 'Education' },
  { to: '/membership', label: 'Membership' },
  {
    label: 'Visit',
    items: [
      { to: '/visit', label: 'Plan Your Visit' },
      { to: '/guests', label: 'Guests' },
      { to: '/faq', label: 'FAQ' },
    ],
  },
  {
    label: 'Get Involved',
    items: [
      { to: '/get-involved/volunteer', label: 'Volunteer' },
      { to: '/get-involved/donate', label: 'Donate' },
      { to: '/rentals', label: 'Rentals' },
    ],
  },
  { to: '/contact', label: 'Contact' },
]

/** The "Join" button beside the navigation, for everyone: it opens the membership plans. */
export const JOIN_LINK: NavLinkItem = { to: '/membership', label: 'Join' }

/** The footer's links, beside Privacy. Journal lives here rather than in the header. */
export const FOOTER_LINKS: NavLinkItem[] = [
  { to: '/membership', label: 'Membership' },
  { to: '/journal', label: 'Journal' },
]
