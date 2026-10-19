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
  { to: '/journal', label: 'Journal' },
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
  { to: '/join', label: 'Join' },
]

/** Every link, flattened, for the footer. */
export const ALL_LINKS: NavLinkItem[] = NAV.flatMap((entry) => (isGroup(entry) ? entry.items : [entry]))
