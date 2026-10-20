import { Lock } from 'lucide-react'
import { Link } from 'react-router'
import { PostCard } from '@/components/members/app/PostCard'
import { appButtonClasses } from '@/components/members/app/ui'
import { Card, Skeleton } from '@/components/members/settings/ui'
import { feedAccount, type TeaserTile } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'

const SLOTS = 9

function Tile({ tile }: { tile: TeaserTile | undefined }) {
  if (!tile) return <li className="aspect-square bg-surface" />
  if (tile.kind === 'note') {
    return (
      <li className="flex aspect-square items-center justify-center bg-oxblood p-2 text-center font-serif text-sm leading-snug text-on-oxblood">
        <span className="line-clamp-4">{tile.title}</span>
      </li>
    )
  }
  return (
    <li className="aspect-square overflow-hidden bg-surface">
      <img src={tile.image.url} srcSet={tile.image.srcset ?? undefined} sizes="160px" alt="" loading="lazy" className="size-full object-cover" />
    </li>
  )
}

/**
 * For accounts without the feed: what the member community looks like, built only from the
 * club's own posts (journal photos, announcement titles and its latest journal post). The
 * server never sends a member's post, profile, avatar, name or any count for it.
 */
export function CommunityTeaser({ showPlans }: { showPlans: boolean }) {
  const teaser = useAsync(() => feedAccount.teaser(), 'feed-teaser')
  return (
    <Card title="The member community" icon={Lock}>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:items-start">
        <div className="flex min-w-0 flex-col gap-3">
          {/* A light blur: a glimpse of the club's own posts, not something to read. */}
          <div className="overflow-hidden rounded-app">
            <ul aria-hidden="true" className="grid grid-cols-3 gap-0.5 blur-[3px]">
              {Array.from({ length: SLOTS }, (_, index) => (
                <Tile key={index} tile={teaser.status === 'success' ? teaser.data.tiles[index] : undefined} />
              ))}
            </ul>
          </div>
          <p className="text-fg">Members share photos, plans and conversation here</p>
          {showPlans && (
            <Link to="/membership" className={appButtonClasses('primary', 'self-start px-4')}>
              See plans
            </Link>
          )}
        </div>
        {teaser.status === 'loading' && <Skeleton lines={4} />}
        {teaser.status === 'success' && teaser.data.post && (
          <div className="min-w-0 overflow-hidden rounded-app border border-border [&>article]:border-b-0">
            <PostCard post={teaser.data.post} />
          </div>
        )}
      </div>
    </Card>
  )
}
