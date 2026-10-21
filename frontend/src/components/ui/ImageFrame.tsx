import { useState } from 'react'
import type { RemoteImage } from '@/lib/api'
import { cn } from '@/lib/cn'
import { IMAGE_BASE_PATH, resolveImage, srcSetFor } from '@/lib/images'

/** The striped wash under a picture: rose (people, rooms) or warm (classes, objects). */
export type PlaceholderTexture = 'rose' | 'warm'

export type AspectRatio = '1/1' | '4/5' | '5/4' | '4/3' | '3/2' | '2/1' | '16/9' | '21/9'

const ratios: Record<AspectRatio, string> = {
  '1/1': 'aspect-square',
  '4/5': 'aspect-[4/5]',
  '5/4': 'aspect-[5/4]',
  '4/3': 'aspect-[4/3]',
  '3/2': 'aspect-[3/2]',
  '2/1': 'aspect-[2/1]',
  '16/9': 'aspect-video',
  '21/9': 'aspect-[21/9]',
}

interface ImageFrameProps {
  /** A filename from docs/image-manifest.json. */
  image?: string
  /** An API image. The server withholds any image without face consent. */
  remote?: RemoteImage | null
  /** Empty falls back to the manifest's or the API image's own description. */
  alt: string
  ratio?: AspectRatio
  placeholder?: PlaceholderTexture
  sizes?: string
  priority?: boolean
  className?: string
  fill?: boolean
  /** Member images: no right-click save, no drag, no long-press callout. A deterrent only. */
  protect?: boolean
}

const PROTECTED_CLASSES = 'select-none [-webkit-touch-callout:none] [-webkit-user-drag:none]'

function blockSave(event: { preventDefault: () => void }) {
  event.preventDefault()
}

/**
 * The only way the site renders imagery. Local images must be in the
 * manifest, and any entry with faces_visible true and consent_confirmed
 * false is refused. Anything refused or missing shows the striped placeholder.
 */
export function ImageFrame({
  image,
  remote,
  alt,
  ratio = '4/3',
  placeholder = 'rose',
  sizes = '100vw',
  priority = false,
  className,
  fill = false,
  protect = false,
}: ImageFrameProps) {
  const [failed, setFailed] = useState(false)
  const local = image ? resolveImage(image) : null

  let content = null
  if (!failed && local) {
    content = (
      <img
        src={`${IMAGE_BASE_PATH}/${local.filename}`}
        srcSet={srcSetFor(local)}
        sizes={sizes}
        width={local.width}
        height={local.height}
        alt={alt || local.alt || ''}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        onError={() => setFailed(true)}
        className="absolute inset-0 size-full object-cover"
      />
    )
  } else if (!failed && remote) {
    content = (
      <img
        src={remote.url}
        srcSet={remote.srcset ?? undefined}
        sizes={remote.srcset ? sizes : undefined}
        width={remote.width ?? undefined}
        height={remote.height ?? undefined}
        alt={remote.alt || alt}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
        draggable={protect ? false : undefined}
        onContextMenu={protect ? blockSave : undefined}
        onDragStart={protect ? blockSave : undefined}
        className={cn('absolute inset-0 size-full object-cover', protect && PROTECTED_CLASSES)}
      />
    )
  }

  return (
    <div
      onContextMenu={protect ? blockSave : undefined}
      className={cn('isolate overflow-hidden bg-canvas', fill ? 'absolute inset-0' : cn('relative', ratios[ratio]), className)}
    >
      {/* The wash stays underneath, so a frame whose image is still loading (or lazily
          waiting below the fold) is never a blank, page-coloured square. */}
      <div aria-hidden="true" className={cn('absolute inset-0', placeholder === 'warm' ? 'wash-warm' : 'wash-rose')} />
      {content}
    </div>
  )
}
