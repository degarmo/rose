import { Layers } from 'lucide-react'
import type { JournalPost } from '@/lib/api'
import { ImageFrame } from '../ui'

interface JournalTileProps {
  post: JournalPost
  onOpen: (post: JournalPost) => void
  sizes?: string
}

function plainCaption(html: string) {
  return new DOMParser().parseFromString(html.replace(/<br>/g, ' '), 'text/html').body.textContent ?? ''
}

/** A square journal picture with rounded corners (design: Home, "From the Journal"). */
export function JournalTile({ post, onOpen, sizes = '(min-width: 1024px) 16vw, 33vw' }: JournalTileProps) {
  const cover = post.images[0] ?? null
  const caption = plainCaption(post.caption_html)
  return (
    <button
      type="button"
      onClick={() => onOpen(post)}
      className="group relative block w-full overflow-hidden rounded-[10px] lg:rounded-sheet"
      aria-label={`Open post: ${caption.slice(0, 80)}`}
    >
      <ImageFrame remote={cover} alt="" ratio="1/1" placeholder="rose" sizes={sizes} />
      {post.images.length > 1 && (
        <Layers aria-hidden="true" className="absolute right-2 top-2 size-5 text-white drop-shadow lg:right-3 lg:top-3" />
      )}
      <span aria-hidden="true" className="absolute inset-0 bg-black/0 transition-colors duration-200 group-hover:bg-black/15" />
    </button>
  )
}
