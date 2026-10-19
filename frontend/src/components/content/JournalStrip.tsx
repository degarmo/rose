import { useNavigate } from 'react-router'
import { api } from '@/lib/api'
import { useAsync } from '@/lib/useAsync'
import { JournalTile } from './JournalTile'
import { EmptyState, ErrorState } from './States'

export const JOURNAL_STRIP_COUNT = 6

const GRID = 'grid grid-cols-3 gap-2 lg:grid-cols-6 lg:gap-4'

/** The latest journal posts as six square tiles (design: Home, "From the Journal"; three across on phones). */
export function JournalStrip() {
  const navigate = useNavigate()
  const state = useAsync(() => api.journal(), 'home-journal')
  if (state.status === 'loading') {
    return (
      <div role="status" className={GRID}>
        <span className="sr-only">Loading the journal</span>
        {Array.from({ length: JOURNAL_STRIP_COUNT }, (_, index) => (
          <div key={index} aria-hidden="true" className="wash-rose aspect-square animate-pulse rounded-[10px] lg:rounded-sheet" />
        ))}
      </div>
    )
  }
  if (state.status === 'error') return <ErrorState title="The journal did not load" onRetry={state.retry} />
  const posts = state.data.posts.slice(0, JOURNAL_STRIP_COUNT)
  if (posts.length === 0) {
    return <EmptyState title="The first posts are on their way" message="Check back soon." />
  }
  return (
    <ul aria-label="Latest journal posts" className={GRID}>
      {posts.map((post) => (
        <li key={post.slug}>
          <JournalTile post={post} onOpen={(open) => navigate(`/journal/${open.slug}`)} />
        </li>
      ))}
    </ul>
  )
}
