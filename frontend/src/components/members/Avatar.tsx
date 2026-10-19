import { cn } from '@/lib/cn'
import type { MemberCard } from '@/lib/membersApi'

const sizes = {
  xs: 'size-6 text-xs',
  sm: 'size-8 text-sm',
  md: 'size-11 text-base',
  story: 'size-14 text-xl',
  profile: 'size-[77px] text-3xl md:size-[150px] md:text-6xl',
}

/** Member avatar, or a monogram. Images come only from the private, access-checked view. */
export function Avatar({ member, size = 'sm', className }: { member: MemberCard; size?: keyof typeof sizes; className?: string }) {
  return (
    <span
      className={cn(
        'relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-hover font-semibold text-fg ring-1 ring-border',
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
