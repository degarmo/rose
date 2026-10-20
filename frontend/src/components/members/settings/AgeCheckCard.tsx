import { IdCard, Lock } from 'lucide-react'
import { Link } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { appButtonClasses, ICON } from '@/components/members/app/ui'
import { isOpen, type MyMembership } from '@/lib/membershipApi'
import { DoorCode } from './MembershipCard'

/**
 * The in-person age check in Settings > Membership (Home has it as a step of "What's
 * missing"): what to bring, the door code to show, and that nothing is copied. Shown while
 * `age_check.needed` is true: staff record the check at the door desk, and the feed opens
 * without logging out (the session is read again).
 */
export function AgeCheckCard({ membership }: { membership: MyMembership | null }) {
  const auth = useAuth()
  const user = auth.user
  if (!user?.age_check.needed) return null
  const code = isOpen(membership) ? membership.reference_code : null
  return (
    <section aria-labelledby="age-check-title" className="flex flex-col gap-4 rounded-app border-2 border-primary bg-canvas p-4">
      <header className="flex items-start gap-3">
        <IdCard aria-hidden="true" size={24} strokeWidth={ICON.stroke} className="mt-0.5 shrink-0 text-link" />
        <div className="min-w-0">
          <h2 id="age-check-title" className="text-lg font-semibold text-fg">
            Verify your age at your next visit.
          </h2>
          <p className="mt-1 text-fg-muted">
            {user.age_check.notice
              ? 'The member feed now needs a quick check in person, for everyone. Nothing you shared is lost: it opens again as soon as staff note the check.'
              : membership?.status === 'pending_payment'
                ? 'Your membership starts once staff have seen your ID in person.'
                : 'The member feed opens once staff have seen your ID in person.'}
          </p>
        </div>
      </header>
      <div className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase tracking-[0.06em] text-fg-muted">What to bring</p>
        <p className="text-fg">A valid photo ID showing you are 18 or older. Staff look at it and hand it straight back.</p>
      </div>
      {code ? (
        <DoorCode code={code} />
      ) : (
        <p className="rounded-app bg-surface p-3 text-fg">
          At the door, give your display name: <strong className="font-semibold">{user.display_name}</strong>
        </p>
      )}
      <p className="flex items-start gap-2 text-meta text-fg-muted">
        <Lock aria-hidden="true" size={16} strokeWidth={ICON.stroke} className="mt-0.5 shrink-0" />
        We never copy or store your ID. Staff only note that they saw it.
      </p>
      {user.member_app === 'verify' && (
        <Link to="/members/join-feed" className={appButtonClasses('secondary', 'self-start')}>
          Read the community guidelines now
        </Link>
      )}
    </section>
  )
}
