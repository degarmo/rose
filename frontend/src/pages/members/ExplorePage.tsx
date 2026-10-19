import { PostGrid } from '@/components/members/app/PostGrid'
import { useMembers } from '@/components/members/membersContext'
import { members } from '@/lib/membersApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** Everyone's posts as a grid, newest first. */
export function ExplorePage() {
  useDocumentMeta({ title: 'Explore', noindex: true })
  const { postsVersion } = useMembers()
  return (
    <div className="mx-auto w-full max-w-[935px] md:px-5 md:pt-6">
      <h1 className="sr-only">Explore</h1>
      <PostGrid
        loader={(cursor) => members.feed('everyone', cursor)}
        listKey={`explore|${postsVersion}`}
        empty={<p className="py-10 text-center text-fg-muted">Nothing shared yet.</p>}
      />
    </div>
  )
}
