import { useCallback, useEffect, useRef, useState } from 'react'
import { JournalTile } from '@/components/content/JournalTile'
import { PageHero } from '@/components/content/PageHero'
import { PostView } from '@/components/content/PostView'
import { EmptyState, ErrorState, LoadingState } from '@/components/content/States'
import { Button, Modal, Section } from '@/components/ui'
import { api, type JournalPost } from '@/lib/api'
import { useAsync } from '@/lib/useAsync'
import { usePageContent } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

type LoadState = 'loading' | 'idle' | 'error' | 'done'

/** Every post as square tiles with rounded corners (design: Home, "From the Journal", as a grid). */
export function JournalGrid({ posts, onOpen }: { posts: JournalPost[]; onOpen: (post: JournalPost) => void }) {
  return (
    <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6 lg:gap-4">
      {posts.map((post) => (
        <li key={post.slug}>
          <JournalTile post={post} onOpen={onOpen} />
        </li>
      ))}
    </ul>
  )
}

interface MorePosts {
  posts: JournalPost[]
  /** undefined until the first "load more"; then the cursor for the page after. */
  cursor: string | null | undefined
  status: 'idle' | 'loading' | 'error'
}

export function JournalPage() {
  useDocumentMeta({ title: 'Journal', description: 'Notes and pictures from life at the club.' })
  const copy = usePageContent('journal')
  const first = useAsync(() => api.journal(), 'journal-first')
  const [more, setMore] = useState<MorePosts>({ posts: [], cursor: undefined, status: 'idle' })
  const [open, setOpen] = useState<JournalPost | null>(null)
  const loadingRef = useRef(false)
  const sentinel = useRef<HTMLDivElement>(null)

  const posts = first.status === 'success' ? [...first.data.posts, ...more.posts] : []
  const cursor = more.cursor !== undefined ? more.cursor : first.status === 'success' ? first.data.nextCursor : null
  const loadState: LoadState =
    first.status === 'loading' || more.status === 'loading'
      ? 'loading'
      : first.status === 'error' || more.status === 'error'
        ? 'error'
        : cursor
          ? 'idle'
          : 'done'

  const loadMore = useCallback(async (from: string) => {
    if (loadingRef.current) return
    loadingRef.current = true
    setMore((current) => ({ ...current, status: 'loading' }))
    try {
      const page = await api.journal(from)
      setMore((current) => ({ posts: [...current.posts, ...page.posts], cursor: page.nextCursor, status: 'idle' }))
    } catch {
      setMore((current) => ({ ...current, status: 'error' }))
    } finally {
      loadingRef.current = false
    }
  }, [])

  useEffect(() => {
    const element = sentinel.current
    if (!element || loadState !== 'idle' || !cursor || !('IntersectionObserver' in window)) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) void loadMore(cursor)
      },
      { rootMargin: '600px 0px' },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [cursor, loadState, loadMore])

  function retry() {
    if (first.status === 'error') first.retry()
    else if (cursor) void loadMore(cursor)
  }

  return (
    <>
      <PageHero copy={copy} />
      <Section spacing="none" aria-label="Journal posts" className="pb-10 pt-4 lg:pb-16 lg:pt-6">
        {posts.length > 0 && <JournalGrid posts={posts} onOpen={setOpen} />}
        <div ref={sentinel} className="mt-10 flex flex-col items-center gap-4" aria-live="polite">
          {loadState === 'loading' && <LoadingState label="Loading posts" />}
          {loadState === 'error' && <ErrorState title="Posts did not load" onRetry={retry} />}
          {loadState === 'idle' && cursor && (
            <Button variant="secondary" size="lg" onClick={() => void loadMore(cursor)}>
              Load more
            </Button>
          )}
          {loadState === 'done' && posts.length === 0 && (
            <EmptyState title="Nothing here yet" message="The first posts are on their way." />
          )}
          {loadState === 'done' && posts.length > 0 && (
            <p className="text-sm text-fg-muted">You are all caught up.</p>
          )}
        </div>
      </Section>
      <Modal open={open !== null} onClose={() => setOpen(null)} title="Journal post" hideTitle size="wide">
        {open && <PostView post={open} showPermalink />}
      </Modal>
    </>
  )
}
