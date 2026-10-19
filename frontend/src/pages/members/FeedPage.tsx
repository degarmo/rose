import { Link, useSearchParams } from 'react-router'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { PostCard } from '@/components/members/app/PostCard'
import { isClub } from '@/components/members/app/postUtils'
import { RightRail } from '@/components/members/app/RightRail'
import { StoriesTray } from '@/components/members/app/Stories'
import { IgButton } from '@/components/members/app/primitives'
import { useMembers } from '@/components/members/membersContext'
import { cn } from '@/lib/cn'
import { firstHomePage, members } from '@/lib/membersApi'
import { useCursorList } from '@/lib/useCursorList'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

type Tab = 'following' | 'everyone'

function HomeFeed({ tab }: { tab: Tab }) {
  const { postsVersion } = useMembers()
  const { base, status, loadMore, retry, bindSentinel } = useCursorList((cursor) => (cursor ? members.home(tab, cursor) : firstHomePage(tab)), `home|${tab}|${postsVersion}`)
  const ids = base.filter((item) => !isClub(item)).map((item) => item.id)

  // The first page gets its own indicator, so nothing below the list moves when it arrives.
  if (base.length === 0 && status === 'loading') return <LoadingState label="Loading posts" />

  return (
    <div>
      <ul className="flex flex-col gap-4">
        {base.map((item, index) => (
          <li key={item.id}>
            <PostCard post={item} listIds={ids} priority={index === 0} />
          </li>
        ))}
      </ul>
      <div ref={bindSentinel} className="mt-8 flex flex-col items-center gap-4" aria-live="polite">
        {status === 'loading' && <LoadingState label="Loading posts" />}
        {status === 'error' && <ErrorState title="Posts did not load" onRetry={retry} />}
        {status === 'idle' && (
          <IgButton variant="secondary" onClick={() => void loadMore()}>
            Load more
          </IgButton>
        )}
        {status === 'done' && base.length === 0 && (
          <div className="w-full">
            <EmptyState
              title={tab === 'following' ? 'Nobody followed yet' : 'Quiet in here'}
              message={tab === 'following' ? 'Follow people from their profiles to see them here.' : 'Be the first to share something.'}
            />
            <p className="mt-4 text-center text-fg-muted">
              New here? Read the{' '}
              <Link to="/members/join-feed?guidelines=1" className="font-semibold text-accent">
                community guidelines
              </Link>{' '}
              or use{' '}
              <Link to="/members/search" className="font-semibold text-accent">
                search
              </Link>
              .
            </p>
          </div>
        )}
        {status === 'done' && base.length > 0 && <p className="text-fg-muted">You are all caught up.</p>}
      </div>
    </div>
  )
}

/** Home: stories, then Following and Everyone, with the club's journal posts among them. */
export function FeedPage() {
  useDocumentMeta({ title: 'Feed', noindex: true })
  const { me } = useMembers()
  const [params, setParams] = useSearchParams()
  const tab: Tab = params.get('tab') === 'following' ? 'following' : 'everyone'

  return (
    <div className="flex justify-center px-0 md:px-6 md:pt-6">
      <div className="w-full min-w-0 max-w-[630px]">
        <h1 className="sr-only">Member feed</h1>
        <StoriesTray />
        <div className="mx-auto max-w-[470px] px-3 sm:px-0">
          {me.post_block_reason === 'guidelines' && (
            <p className="mb-4 rounded-lg border border-border p-4 text-fg">
              The guidelines have changed.{' '}
              <Link to="/members/join-feed?guidelines=1" className="font-semibold text-accent">
                Read and accept them
              </Link>{' '}
              to post again.
            </p>
          )}
          {me.post_block_reason === 'cooldown' && (
            <p className="mb-4 rounded-lg border border-border p-4 text-fg">Posting is paused on your account for a little while. You can still read and like.</p>
          )}
          <div role="tablist" aria-label="Feed" className="mb-2 flex justify-center gap-12 border-b border-border">
            {(['following', 'everyone'] as const).map((value) => (
              <button
                key={value}
                role="tab"
                type="button"
                aria-selected={tab === value}
                onClick={() => setParams(value === 'everyone' ? {} : { tab: value }, { replace: true })}
                className={cn(
                  '-mb-px h-11 border-b px-1 font-semibold transition-colors duration-150',
                  tab === value ? 'border-fg text-fg' : 'border-transparent text-fg-muted hover:text-fg',
                )}
              >
                {value === 'following' ? 'Following' : 'Everyone'}
              </button>
            ))}
          </div>
          <HomeFeed tab={tab} />
        </div>
      </div>
      <RightRail />
    </div>
  )
}
