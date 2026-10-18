import { cn } from '@/lib/cn'
import type { MemberCard } from '@/lib/membersApi'

const sizes = { sm: 'size-9 text-sm', md: 'size-12 text-lg', lg: 'size-24 text-4xl' }

/** Member avatar, or a monogram. Images come only from the private, access-checked view. */
export function Avatar({ member, size = 'sm', className }: { member: MemberCard; size?: keyof typeof sizes; className?: string }) {
  return (
    <span
      className={cn(
        'relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-highlight/40 bg-primary-deep font-display text-fg',
        sizes[size],
        className,
      )}
      onContextMenu={(event) => event.preventDefault()}
    >
      {member.avatar ? (
        <img
          src={member.avatar}
          alt=""
          draggable={false}
          className="size-full select-none object-cover [-webkit-touch-callout:none]"
        />
      ) : (
        <span aria-hidden="true">{member.handle.slice(0, 1).toUpperCase()}</span>
      )}
    </span>
  )
}
