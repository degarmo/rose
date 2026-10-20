import { TriangleAlert } from 'lucide-react'
import type { StaffSession } from '@/lib/safetyApi'

/**
 * On every staff page while the member feed's age check is switched off. Admins can open it:
 * the setting is changed on its admin page, with a reason and a fresh two-step code.
 */
export function AgeCheckOffBanner({ staff }: { staff: StaffSession }) {
  const text = 'Age verification for the member feed is off'
  const classes = 'flex w-full items-center justify-center gap-2 rounded-app border border-wait bg-wait px-4 py-3 text-center font-semibold text-wait-fg'
  if (!staff.can_change_age_check) {
    return (
      <p role="status" className={classes}>
        <TriangleAlert aria-hidden="true" className="size-5 shrink-0" />
        {text}
      </p>
    )
  }
  return (
    <a href={staff.age_check_url} className={`${classes} hover:brightness-95`}>
      <TriangleAlert aria-hidden="true" className="size-5 shrink-0" />
      {text}
      <span className="underline underline-offset-4">Change</span>
    </a>
  )
}
