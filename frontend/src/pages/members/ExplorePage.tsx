import { Search } from 'lucide-react'
import { Link } from 'react-router'
import { PhoneBar } from '@/components/members/app/Nav'
import { PostGrid } from '@/components/members/app/PostGrid'
import { useMembers } from '@/components/members/membersContext'
import { members } from '@/lib/membersApi'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** Explore (design: "Explore"): everyone's posts as square tiles, newest first. */
export function ExplorePage() {
  useDocumentMeta({ title: 'Explore', noindex: true })
  const { postsVersion } = useMembers()
  return (
    <>
      <PhoneBar
        title={
          <Link to="/members/search" className="flex h-9 items-center gap-2 rounded-app bg-field px-3 text-sm font-normal text-fg-muted-tint">
            <Search aria-hidden="true" size={16} strokeWidth={1.8} />
            Search
          </Link>
        }
      />
      <div className="mx-auto w-full max-w-[975px] pt-1 md:px-5 md:pt-6">
        <h1 className="sr-only">Explore</h1>
        <PostGrid
          loader={(cursor) => members.feed('everyone', cursor)}
          listKey={`explore|${postsVersion}`}
          shape="square"
          empty={<p className="py-10 text-center text-fg-muted">Nothing shared yet.</p>}
        />
      </div>
    </>
  )
}
