import { Bell, Flag, IdCard, Inbox, KeyRound, Lock, LogOut, ScrollText, ShieldCheck, Trash2, User, type LucideIcon } from 'lucide-react'
import type { ComponentType } from 'react'
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { PhoneBar } from '@/components/members/app/Nav'
import { ICON } from '@/components/members/app/ui'
import { ButtonRow, CHEVRON, LinkRow, RowIcon, RowText, ROW, VerifyEmailBanner } from '@/components/members/settings/ui'
import { cn } from '@/lib/cn'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { GuidelinesSection } from './GuidelinesSection'
import { LeaveSection } from './LeaveSection'
import { MembershipSection } from './MembershipSection'
import { NoticesSection } from './NoticesSection'
import { NotificationsSection } from './NotificationsSection'
import { PrivacySection } from './PrivacySection'
import { ProfileSection } from './ProfileSection'
import { SecuritySection } from './SecuritySection'

interface SettingsSection {
  key: string
  label: string
  sub: string
  icon: LucideIcon
  danger?: boolean
  Component: ComponentType
}

const SECTIONS: SettingsSection[] = [
  {
    key: 'membership',
    label: 'Membership',
    sub: 'Your plan, door code and payments',
    icon: IdCard,
    Component: MembershipSection,
  },
  {
    key: 'profile',
    label: 'Profile',
    sub: 'Name, picture, bio and pronouns',
    icon: User,
    Component: ProfileSection,
  },
  {
    key: 'privacy',
    label: 'Privacy',
    sub: 'Who sees you, blocks, calendar files, your data',
    icon: Lock,
    Component: PrivacySection,
  },
  {
    key: 'notifications',
    label: 'Notifications',
    sub: 'Emails and in-app alerts',
    icon: Bell,
    Component: NotificationsSection,
  },
  {
    key: 'security',
    label: 'Security',
    sub: 'Password, two-step login and devices',
    icon: KeyRound,
    Component: SecuritySection,
  },
  {
    key: 'notices',
    label: 'Notices',
    sub: 'Decisions about your account, appeals, reports you sent',
    icon: Inbox,
    Component: NoticesSection,
  },
  {
    key: 'guidelines',
    label: 'Community guidelines',
    sub: 'The rules, and when you accepted them',
    icon: ScrollText,
    Component: GuidelinesSection,
  },
  {
    key: 'leave',
    label: 'Leave the community',
    sub: 'Erase what you shared or delete your account',
    icon: Trash2,
    danger: true,
    Component: LeaveSection,
  },
]

/** The old account page's anchors, so bookmarks such as /account#password still land in the right place. */
const OLD_ANCHORS: Record<string, string> = {
  membership: 'membership',
  rsvps: 'membership',
  profile: 'profile',
  appearance: 'profile',
  password: 'security',
  sessions: 'security',
  safety: 'notices',
  delete: 'leave',
}

/** The count of unseen notices on the Notices row (as the app's other unread badges). */
function UnreadCount({ count }: { count: number }) {
  if (!count) return null
  return (
    <span className="min-w-5 shrink-0 rounded-full bg-primary px-1.5 text-center text-xs font-semibold leading-5 text-on-primary">
      <span aria-hidden="true">{count > 9 ? '9+' : count}</span>
      <span className="sr-only">{count === 1 ? '1 unread' : `${count} unread`}</span>
    </span>
  )
}

function SectionList({ active, current }: { active: string; current: string | null }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const unread = auth.user?.unread_notices ?? 0
  return (
    <>
      <ul>
        {SECTIONS.map((section) => (
          <li key={section.key}>
            <Link
              to={`/members/settings/${section.key}`}
              aria-current={current === section.key ? 'page' : undefined}
              className={cn(ROW, 'px-1 hover:bg-surface md:rounded-app md:border-b-0 md:px-3', active === section.key && 'md:bg-surface')}
            >
              <RowIcon icon={section.icon} danger={section.danger} />
              <RowText label={section.label} sub={section.sub} danger={section.danger} />
              {section.key === 'notices' && <UnreadCount count={unread} />}
              <span className="md:hidden">{CHEVRON}</span>
            </Link>
          </li>
        ))}
      </ul>
      <ul className="mt-4 border-t border-border pt-2">
        <LinkRow icon={Flag} label="Report a concern" to="/members/report" />
        {auth.user?.staff && <LinkRow icon={ShieldCheck} label="Staff" sub="Reports, members and the team" to="/members/staff" />}
        <ButtonRow
          icon={LogOut}
          label="Log out"
          onClick={() => {
            // Leave first: signed out, this screen would ask to log in again.
            navigate('/', { replace: true })
            void auth.logout()
          }}
        />
      </ul>
    </>
  )
}

/**
 * Settings (design: "Settings"): every account setting in the member app. Phones show the
 * list, then one section per screen; wider screens keep the list on the left beside the
 * open section (Membership first).
 */
export function SettingsPage() {
  const auth = useAuth()
  const { section: key } = useParams()
  const { hash } = useLocation()
  const section = SECTIONS.find((item) => item.key === key) ?? null
  useDocumentMeta({
    title: section ? `Settings: ${section.label}` : 'Settings',
    noindex: true,
  })

  if (key && !section) return <NotFoundPage />
  const moved = !key && OLD_ANCHORS[hash.slice(1)]
  if (moved) return <Navigate to={`/members/settings/${moved}`} replace />
  const shown = section ?? SECTIONS[0]
  const user = auth.user

  return (
    <>
      <PhoneBar back={section ? '/members/settings' : true} title={<h1 className="truncate">{section ? section.label : 'Settings'}</h1>} />
      <div className="mx-auto w-full max-w-[1000px] px-4 pb-12 md:px-8 md:pt-10">
        {user && !user.email_verified && (
          <div className="mb-4 pt-2 md:pt-0">
            <VerifyEmailBanner />
          </div>
        )}
        <div className="md:flex md:gap-8">
          <nav aria-label="Settings" className={cn('md:block md:w-[280px] md:shrink-0', section && 'hidden')}>
            <h1 className="hidden px-3 pb-4 text-xl font-semibold text-fg md:block">Settings</h1>
            <SectionList active={shown.key} current={section ? section.key : null} />
          </nav>
          <section aria-labelledby="settings-section" className={cn('min-w-0 flex-1 pt-2 md:pt-0', !section && 'hidden md:block')}>
            <h2 id="settings-section" className="flex items-center gap-2 pb-4 text-xl font-semibold text-fg max-md:sr-only">
              <shown.icon aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
              {shown.label}
            </h2>
            <shown.Component />
          </section>
        </div>
      </div>
    </>
  )
}
