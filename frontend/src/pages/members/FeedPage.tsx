import { Link, useSearchParams } from 'react-router'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { PostCard } from '@/components/members/app/PostCard'
import { isClub } from '@/components/members/app/postUtils'
import { HomeBar } from '@/components/members/app/Nav'
import { RightRail } from '@/components/members/app/RightRail'
import { StoriesTray } from '@/components/members/app/Stories'
import { AppButton } from '@/components/members/app/primitives'
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
      <ul className="flex flex-col gap-3">
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
          <AppButton variant="secondary" onClick={() => void loadMore()}>
            Load more
          </AppButton>
        )}
        {status === 'done' && base.length === 0 && (
          <div className="w-full px-4 md:px-0">
            <EmptyState
              title={tab === 'following' ? 'Nobody followed yet' : 'Quiet in here'}
              message={tab === 'following' ? 'Follow people from their profiles to see them here.' : 'Be the first to share something.'}
            />
            <p className="mt-4 text-center text-fg-muted">
              New here? Read the{' '}
              <Link to="/members/join-feed?guidelines=1" className="font-semibold text-link">
                community guidelines
              </Link>{' '}
              or use{' '}
              <Link to="/members/search" className="font-semibold text-link">
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

/**
 * Home (design: "Home"): stories, then Following and Everyone, with the club's journal
 * posts among them. From 1160px the 470px column sits 64px from the right rail.
 */
export function FeedPage() {
  useDocumentMeta({ title: 'Feed', noindex: true })
  const { me } = useMembers()
  const [params, setParams] = useSearchParams()
  const tab: Tab = params.get('tab') === 'following' ? 'following' : 'everyone'
  const notice = 'mx-4 mb-3 rounded-app bg-surface px-4 py-3 text-fg md:mx-0'

  return (
    <>
      <HomeBar me={me} />
      <div className="flex justify-center gap-16 md:px-6 md:pt-6">
        <div className="w-full min-w-0 max-w-[470px]">
          <h1 className="sr-only">Member feed</h1>
          <StoriesTray />
          {me.post_block_reason === 'guidelines' && (
            <p className={notice}>
              The guidelines have changed.{' '}
              <Link to="/members/join-feed?guidelines=1" className="font-semibold text-link">
                Read and accept them
              </Link>{' '}
              to post again.
            </p>
          )}
          {me.post_block_reason === 'cooldown' && <p className={notice}>Posting is paused on your account for a little while. You can still read and like.</p>}
          <div role="tablist" aria-label="Feed" className="flex border-b border-border md:mb-3 md:mt-3">
            {(['following', 'everyone'] as const).map((value) => (
              <button
                key={value}
                role="tab"
                type="button"
                aria-selected={tab === value}
                onClick={() => setParams(value === 'everyone' ? {} : { tab: value }, { replace: true })}
                className={cn(
                  '-mb-px flex-1 border-b py-2.5 transition-colors duration-150 md:flex-none md:px-4 md:py-3',
                  tab === value ? 'border-fg font-semibold text-fg' : 'border-transparent text-fg-muted hover:text-fg',
                )}
              >
                {value === 'following' ? 'Following' : 'Everyone'}
              </button>
            ))}
          </div>
          <HomeFeed tab={tab} />
        </div>
        <RightRail />
      </div>
    </>
  )
}
