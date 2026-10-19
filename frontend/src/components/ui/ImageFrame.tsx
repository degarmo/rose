import { useState } from 'react'
import type { RemoteImage } from '@/lib/api'
import { cn } from '@/lib/cn'
import { IMAGE_BASE_PATH, resolveImage, srcSetFor } from '@/lib/images'
import { useReveal } from '@/lib/useReveal'

export type PlaceholderTexture = 'velvet' | 'candle' | 'silk' | 'leather' | 'shadow' | 'architecture' | 'rose'

export type AspectRatio = '1/1' | '4/5' | '4/3' | '3/2' | '16/9' | '21/9'

const ratios: Record<AspectRatio, string> = {
  '1/1': 'aspect-square',
  '4/5': 'aspect-[4/5]',
  '4/3': 'aspect-[4/3]',
  '3/2': 'aspect-[3/2]',
  '16/9': 'aspect-video',
  '21/9': 'aspect-[21/9]',
}

interface ImageFrameProps {
  /** A filename from docs/image-manifest.json. */
  image?: string
  /** An API image. The server withholds any image without face consent. */
  remote?: RemoteImage | null
  alt: string
  ratio?: AspectRatio
  placeholder?: PlaceholderTexture
  sizes?: string
  priority?: boolean
  reveal?: boolean
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
 * false is refused. Anything refused or missing shows a texture placeholder.
 */
export function ImageFrame({
  image,
  remote,
  alt,
  ratio = '4/3',
  placeholder = 'velvet',
  sizes = '100vw',
  priority = false,
  reveal = true,
  className,
  fill = false,
  protect = false,
}: ImageFrameProps) {
  const ref = useReveal<HTMLDivElement>()
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
        alt={alt}
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
      ref={ref}
      onContextMenu={protect ? blockSave : undefined}
      className={cn(
        'grain isolate overflow-hidden bg-surface-raised',
        fill ? 'absolute inset-0' : cn('relative', ratios[ratio]),
        reveal && 'reveal-image',
        className,
      )}
    >
      {content ?? <div aria-hidden="true" className={cn('absolute inset-0', `texture-${placeholder}`)} />}
    </div>
  )
}
