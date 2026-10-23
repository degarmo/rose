import { ArrowUpRight, ShieldCheck } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router'
import { AgeCheckOffBanner } from '@/components/members/staff/AgeCheckBanner'
import { useAuth } from '@/components/layout/authContext'
import { PhoneBar } from '@/components/members/app/Nav'
import { appButtonClasses } from '@/components/members/app/ui'
import { cn } from '@/lib/cn'
import { atLeast, ROLE_LABELS, type Role, type StaffSession } from '@/lib/safetyApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '@/pages/NotFoundPage'

const TABS: Array<{ to: string; label: string; minimum: Role | 'door' }> = [
  // First for door volunteers (their only tab); the team see it where they have the permission.
  { to: '/members/staff/door', label: 'Door desk', minimum: 'door' },
  { to: '/members/staff/reports', label: 'Reports', minimum: 'moderator' },
  { to: '/members/staff/members', label: 'Members', minimum: 'moderator' },
  { to: '/members/staff/team', label: 'Team', minimum: 'admin' },
]

function allowed(staff: StaffSession, minimum: Role | 'door') {
  return minimum === 'door' ? staff.door_desk : atLeast(staff.role, minimum)
}

/**
 * The two-step check, in the app's own look: the admin's login does the work and returns
 * here. Without an authenticator yet, it says so and starts by setting one up.
 */
function VerifyFirst({ url, enrol }: { url: string; enrol: boolean }) {
  return (
    <div className="mx-auto flex max-w-[460px] flex-col items-center gap-3 px-6 py-16 text-center">
      <ShieldCheck aria-hidden="true" className="size-10 text-fg" strokeWidth={1.5} />
      <h1 className="text-xl font-semibold text-fg">{enrol ? 'Set up your two-step login' : 'Confirm it is you'}</h1>
      {enrol ? (
        <ol className="flex list-decimal flex-col gap-1 pl-5 text-left text-fg-muted">
          <li>Install an authenticator app on your phone, if you do not have one.</li>
          <li>Enter your password again, then scan the code the next page shows.</li>
          <li>Type the six-digit code, and keep the ten backup codes somewhere safe.</li>
        </ol>
      ) : (
        <p className="text-fg-muted">The staff section needs the code from your authenticator app, once per session.</p>
      )}
      <a href={url} className={appButtonClasses('primary', 'mt-2')}>
        {enrol ? 'Set it up' : 'Continue'}
      </a>
    </div>
  )
}

/**
 * Every staff page sits in this frame: the gate (a team role, or the door desk permission
 * for the door), the two-step check, and the section's tabs. Anyone without access gets
 * the same 404 as an unknown address.
 */
export function StaffFrame({
  title,
  minimum = 'moderator',
  actions,
  wide = false,
  children,
}: {
  title: string
  minimum?: Role | 'door'
  actions?: ReactNode
  /** The door desk uses the full width of a tablet. */
  wide?: boolean
  children: ReactNode
}) {
  useDocumentMeta({ title: `Staff: ${title}`, noindex: true })
  const auth = useAuth()
  const staff = auth.user?.staff
  if (!staff || !allowed(staff, minimum)) return <NotFoundPage />
  if (!staff.verified && staff.verify_url) {
    return (
      <>
        <PhoneBar title="Staff" />
        <VerifyFirst url={staff.verify_url} enrol={staff.needs_enrollment} />
      </>
    )
  }
  return (
    <>
      <PhoneBar title={title} back />
      {staff.preview_mode && (
        <p role="status" className="border-b border-wait bg-wait px-4 py-1 text-center text-xs font-semibold text-wait-fg">
          Preview mode: uploads are temporary, emails are not sent.
        </p>
      )}
      <div className={cn('mx-auto w-full px-4 pb-12 md:px-8 md:pt-8', wide ? 'max-w-[1100px]' : 'max-w-[935px]')}>
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 md:pt-0">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Staff · {staff.role ? ROLE_LABELS[staff.role] : 'Door desk'}</p>
            <h1 className="hidden text-xl font-semibold text-fg md:block">{title}</h1>
          </div>
          {actions}
        </div>
        <nav aria-label="Staff" className="mt-4 border-b border-border">
          {/* Wraps on a phone rather than scrolling, so no tab hides past the edge. */}
          <ul className="-mb-px flex flex-wrap gap-x-5 md:gap-x-6">
            {TABS.filter((tab) => allowed(staff, tab.minimum)).map((tab) => (
              <li key={tab.to}>
                <NavLink
                  to={tab.to}
                  // The door desk loads afresh, so its camera permission applies.
                  reloadDocument={tab.minimum === 'door'}
                  className={({ isActive }) =>
                    cn('inline-flex h-11 items-center whitespace-nowrap border-b text-xs font-semibold uppercase tracking-[0.06em]', isActive ? 'border-fg text-fg' : 'border-transparent text-fg-muted hover:text-fg')
                  }
                >
                  {tab.label}
                </NavLink>
              </li>
            ))}
            {staff.role && (
              // The dashboard is the admin's (the only one); figures never appear here.
              <li>
                <a href={staff.admin_url} className="inline-flex h-11 items-center gap-1 whitespace-nowrap border-b border-transparent text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted hover:text-fg">
                  Dashboard
                  <ArrowUpRight aria-hidden="true" className="size-3.5" />
                  <span className="sr-only">(opens the admin)</span>
                </a>
              </li>
            )}
          </ul>
        </nav>
        {!staff.age_check_required && (
          <div className="pt-4">
            <AgeCheckOffBanner staff={staff} />
          </div>
        )}
        <div className="pt-5">{children}</div>
      </div>
    </>
  )
}
