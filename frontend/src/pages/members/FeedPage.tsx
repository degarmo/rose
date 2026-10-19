import { Link, useSearchParams } from 'react-router'
import { useMembers } from '@/components/members/membersContext'
import { PostList } from '@/components/members/PostList'
import { cn } from '@/lib/cn'
import { members } from '@/lib/membersApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

export function FeedPage() {
  useDocumentMeta({ title: 'Feed', noindex: true })
  const { postsVersion, me } = useMembers()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'following' ? 'following' : 'everyone'

  return (
    <div>
      <h1 className="sr-only">Member feed</h1>
      {me.post_block_reason === 'guidelines' && (
        <p className="mx-auto mb-4 max-w-[470px] rounded-lg bg-primary-deep p-4 text-sm text-fg">
          The guidelines have changed.{' '}
          <Link to="/members/join-feed?guidelines=1" className="underline underline-offset-4">
            Read and accept them
          </Link>{' '}
          to post again.
        </p>
      )}
      {me.post_block_reason === 'cooldown' && (
        <p className="mx-auto mb-4 max-w-[470px] rounded-lg bg-primary-deep p-4 text-sm text-fg-muted">Posting is paused on your account for a little while. You can still read and like.</p>
      )}
      <div role="tablist" aria-label="Feed" className="mx-auto mb-6 flex max-w-[470px] justify-center gap-10 border-b border-border">
        {(['following', 'everyone'] as const).map((value) => (
          <button
            key={value}
            role="tab"
            type="button"
            aria-selected={tab === value}
            onClick={() => setParams(value === 'everyone' ? {} : { tab: value }, { replace: true })}
            className={cn(
              '-mb-px min-h-11 border-b px-1 text-sm font-semibold transition-colors',
              tab === value ? 'border-fg text-fg' : 'border-transparent text-fg-muted hover:text-fg',
            )}
          >
            {value === 'following' ? 'Following' : 'Everyone'}
          </button>
        ))}
      </div>
      <PostList
        listKey={`feed|${tab}|${postsVersion}`}
        loader={(cursor) => members.feed(tab, cursor)}
        empty={
          tab === 'following'
            ? { title: 'Nobody followed yet', message: 'Follow people from their profiles to see them here.' }
            : { title: 'Quiet in here', message: 'Be the first to share something.' }
        }
      />
    </div>
  )
}
