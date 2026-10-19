import { Layers } from 'lucide-react'
import type { JournalPost } from '@/lib/api'
import { ImageFrame } from '../ui'

interface JournalTileProps {
  post: JournalPost
  onOpen: (post: JournalPost) => void
}

function plainCaption(html: string) {
  return new DOMParser().parseFromString(html.replace(/<br>/g, ' '), 'text/html').body.textContent ?? ''
}

export function JournalTile({ post, onOpen }: JournalTileProps) {
  const cover = post.images[0] ?? null
  const caption = plainCaption(post.caption_html)
  return (
    <button
      type="button"
      onClick={() => onOpen(post)}
      className="group relative block w-full overflow-hidden bg-surface-raised focus-visible:z-10"
      aria-label={`Open post: ${caption.slice(0, 80)}`}
    >
      <ImageFrame remote={cover} alt="" ratio="1/1" placeholder="velvet" reveal={false} sizes="33vw" />
      {post.images.length > 1 && (
        <Layers aria-hidden="true" className="absolute right-2 top-2 size-5 text-white drop-shadow sm:right-3 sm:top-3" />
      )}
      <span
        aria-hidden="true"
        className="absolute inset-0 bg-ink-950/0 transition-colors duration-500 group-hover:bg-ink-950/30"
      />
    </button>
  )
}
