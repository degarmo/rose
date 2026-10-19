import { ShieldCheck } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { PhoneBar } from '@/components/members/app/Nav'
import { appButtonClasses } from '@/components/members/app/ui'
import { cn } from '@/lib/cn'
import { atLeast, ROLE_LABELS, type Role } from '@/lib/safetyApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '@/pages/NotFoundPage'

const TABS: Array<{ to: string; label: string; minimum: Role; end?: boolean }> = [
  { to: '/members/staff', label: 'Dashboard', minimum: 'staff', end: true },
  { to: '/members/staff/reports', label: 'Reports', minimum: 'moderator' },
  { to: '/members/staff/members', label: 'Members', minimum: 'moderator' },
  { to: '/members/staff/team', label: 'Team', minimum: 'admin' },
]

/** The two-step check, in the app's own look: the admin's login does the work and returns here. */
function VerifyFirst({ url }: { url: string }) {
  return (
    <div className="mx-auto flex max-w-[420px] flex-col items-center gap-3 px-6 py-16 text-center">
      <ShieldCheck aria-hidden="true" className="size-10 text-fg" strokeWidth={1.5} />
      <h1 className="text-xl font-semibold text-fg">Confirm it is you</h1>
      <p className="text-fg-muted">The staff section needs the code from your authenticator app, once per session.</p>
      <a href={url} className={appButtonClasses('primary', 'mt-2')}>
        Continue
      </a>
    </div>
  )
}

/**
 * Every staff page sits in this frame: the team-only gate, the two-step check, and the
 * section's tabs. Anyone without a role gets the same 404 as an unknown address.
 */
export function StaffFrame({ title, minimum = 'moderator', actions, children }: { title: string; minimum?: Role; actions?: ReactNode; children: ReactNode }) {
  useDocumentMeta({ title: `Staff: ${title}`, noindex: true })
  const auth = useAuth()
  const staff = auth.user?.staff
  if (!staff || !atLeast(staff.role, minimum)) return <NotFoundPage />
  if (!staff.verified && staff.verify_url) {
    return (
      <>
        <PhoneBar title="Staff" />
        <VerifyFirst url={staff.verify_url} />
      </>
    )
  }
  return (
    <>
      <PhoneBar title={title} back />
      <div className="mx-auto w-full max-w-[935px] px-4 pb-12 md:px-8 md:pt-8">
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 md:pt-0">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">Staff · {ROLE_LABELS[staff.role]}</p>
            <h1 className="hidden text-xl font-semibold text-fg md:block">{title}</h1>
          </div>
          {actions}
        </div>
        <nav aria-label="Staff" className="mt-4 border-b border-border">
          <ul className="-mb-px flex gap-6 overflow-x-auto [scrollbar-width:none]">
            {TABS.filter((tab) => atLeast(staff.role, tab.minimum)).map((tab) => (
              <li key={tab.to}>
                <NavLink
                  to={tab.to}
                  end={tab.end}
                  className={({ isActive }) =>
                    cn('inline-flex h-11 items-center whitespace-nowrap border-b text-xs font-semibold uppercase tracking-[0.06em]', isActive ? 'border-fg text-fg' : 'border-transparent text-fg-muted hover:text-fg')
                  }
                >
                  {tab.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="pt-5">{children}</div>
      </div>
    </>
  )
}
