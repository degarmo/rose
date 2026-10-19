import type { StaffProfile } from '@/lib/api'
import { Card, ImageFrame } from '../ui'

/**
 * A volunteer's display name, role and (on the staff page) a few words, in the site's
 * bordered card (laid out like the Education cards). Never an email.
 */
export function StaffCard({ person, compact = false }: { person: StaffProfile; compact?: boolean }) {
  const Name = compact ? 'p' : 'h3'
  return (
    <Card className="h-full items-start p-5 lg:p-6">
      {person.photo ? (
        <ImageFrame remote={person.photo} alt={person.photo.alt} ratio="1/1" sizes="56px" placeholder="rose" className="w-14 rounded-full" />
      ) : (
        <span aria-hidden="true" className="inline-flex size-14 items-center justify-center rounded-full bg-tint font-display text-2xl text-tint-fg">
          {person.display_name[0]}
        </span>
      )}
      <Name className="mt-4 font-display text-xl leading-[1.2] text-fg lg:text-card-title">{person.display_name}</Name>
      <p className="mt-1 text-[0.8125rem] text-fg-muted lg:text-sm">{person.role_title}</p>
      {!compact && person.bio && <p className="mt-3 whitespace-pre-line text-sm text-fg-muted">{person.bio}</p>}
    </Card>
  )
}
