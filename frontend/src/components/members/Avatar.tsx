import { cn } from '@/lib/cn'
import type { MemberCard } from '@/lib/membersApi'

const sizes = { xs: 'size-6 text-xs', sm: 'size-8 text-sm', md: 'size-11 text-base', lg: 'size-20 text-3xl sm:size-36 sm:text-5xl' }

/** Member avatar, or a monogram. Images come only from the private, access-checked view. */
export function Avatar({ member, size = 'sm', className }: { member: MemberCard; size?: keyof typeof sizes; className?: string }) {
  return (
    <span
      className={cn(
        'relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary-deep font-semibold text-fg ring-1 ring-border',
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
