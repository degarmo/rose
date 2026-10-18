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
        <p className="mb-4 rounded-xl border border-highlight/40 bg-primary-deep/40 p-4 text-sm text-fg">
          The guidelines have changed.{' '}
          <Link to="/members/join-feed?guidelines=1" className="underline underline-offset-4">
            Read and accept them
          </Link>{' '}
          to post again.
        </p>
      )}
      {me.post_block_reason === 'cooldown' && (
        <p className="mb-4 rounded-xl border border-border p-4 text-sm text-fg-muted">Posting is paused on your account for a little while. You can still read and like.</p>
      )}
      <div role="tablist" aria-label="Feed" className="mb-5 grid grid-cols-2 rounded-full border border-border p-1">
        {(['following', 'everyone'] as const).map((value) => (
          <button
            key={value}
            role="tab"
            type="button"
            aria-selected={tab === value}
            onClick={() => setParams(value === 'everyone' ? {} : { tab: value }, { replace: true })}
            className={cn(
              'min-h-10 rounded-full text-sm transition-colors',
              tab === value ? 'bg-primary text-on-primary' : 'text-fg-muted hover:text-fg',
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
