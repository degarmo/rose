import type { StaffProfile } from '@/lib/api'
import { Card, ImageFrame } from '../ui'

/** A volunteer's display name, role and (on the staff page) a few words. Never an email. */
export function StaffCard({ person, compact = false }: { person: StaffProfile; compact?: boolean }) {
  return (
    <Card className="h-full items-start p-6">
      {person.photo ? (
        <ImageFrame remote={person.photo} alt={person.photo.alt} ratio="1/1" sizes="80px" placeholder="velvet" className="w-20 rounded-full" />
      ) : (
        <span
          aria-hidden="true"
          className="inline-flex size-14 items-center justify-center rounded-full border border-highlight/50 bg-primary-deep font-display text-2xl text-fg"
        >
          {person.display_name[0]}
        </span>
      )}
      {compact ? (
        <p className="mt-5 font-display text-2xl text-fg">{person.display_name}</p>
      ) : (
        <h3 className="mt-5 font-display text-2xl text-fg">{person.display_name}</h3>
      )}
      <p className="mt-1 text-sm text-highlight">{person.role_title}</p>
      {!compact && person.bio && <p className="mt-4 whitespace-pre-line leading-relaxed text-fg-muted">{person.bio}</p>}
    </Card>
  )
}
