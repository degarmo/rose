import { cn } from '@/lib/cn'
import type { MemberCard } from '@/lib/membersApi'

const sizes = {
  xs: 'size-6',
  sm: 'size-8',
  md: 'size-11',
  profile: 'size-[77px] md:size-[150px]',
}

/**
 * Soft washes for members without a picture (design: the avatar gradients). The same
 * handle always gets the same one; they darken in the dark appearance.
 */
const WASHES = [
  'from-[#F1D9DF] to-[#D9B5BE] dark:from-[#6B4B55] dark:to-[#4A343B]',
  'from-[#E8C9D2] to-[#C9A3AE] dark:from-[#5E4650] dark:to-[#433139]',
  'from-[#D9C9E8] to-[#B3A3C9] dark:from-[#4E4560] dark:to-[#372F45]',
  'from-[#E2D8C9] to-[#C9BBA3] dark:from-[#5A5145] dark:to-[#3F3830]',
  'from-[#C9D9D2] to-[#A3BDB3] dark:from-[#45564F] dark:to-[#303D38]',
]

function washFor(handle: string) {
  let hash = 0
  for (const char of handle) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  return WASHES[hash % WASHES.length]
}

/** Member avatar: their picture, or a soft wash. Pictures come only from the private, access-checked view. */
export function Avatar({ member, size = 'sm', className }: { member: MemberCard; size?: keyof typeof sizes; className?: string }) {
  return (
    <span
      className={cn('relative inline-flex shrink-0 overflow-hidden rounded-full bg-linear-to-br', washFor(member.handle), sizes[size], className)}
      onContextMenu={(event) => event.preventDefault()}
    >
      {member.avatar && <img src={member.avatar} alt="" draggable={false} className="size-full select-none object-cover [-webkit-touch-callout:none]" />}
    </span>
  )
}
