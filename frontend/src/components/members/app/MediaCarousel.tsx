import { ChevronLeft, ChevronRight, Heart } from 'lucide-react'
import { useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'
import { cn } from '@/lib/cn'
import type { FeedImage } from '@/lib/membersApi'
import { mediaRatio } from './postUtils'

const SWIPE_THRESHOLD = 40
const DOUBLE_TAP_MS = 300
const BURST_MS = 600
function blockSave(event: { preventDefault: () => void }) {
  event.preventDefault()
}

interface MediaCarouselProps {
  images: FeedImage[]
  label: string
  /** Member images: no context menu, dragging or long-press saving. A deterrent only. */
  protect: boolean
  /** Double-tap or double-click likes the post; omitted for posts that cannot be liked. */
  onDoubleTap?: () => void
  /** Fill the parent's height instead of keeping the post's shape (the post modal). */
  fill?: boolean
  /** Fetch the first image at once and at high priority (the first post in a feed); others wait until near the screen. */
  priority?: boolean
  /** Rose dots under the picture (design: the post card) rather than white ones over it. */
  dotsBelow?: boolean
}

/**
 * One image at a time: swipe, arrow keys when focused, or the arrow buttons that appear
 * on hover with a mouse. Dots show the position. Double-tapping shows a heart burst.
 */
export function MediaCarousel({ images, label, protect, onDoubleTap, fill = false, priority = false, dotsBelow = false }: MediaCarouselProps) {
  const [index, setIndex] = useState(0)
  const [burst, setBurst] = useState(0)
  const touchStart = useRef<number | null>(null)
  const lastTap = useRef(0)
  const count = images.length
  const go = (next: number) => setIndex(Math.min(Math.max(next, 0), count - 1))

  function like() {
    if (!onDoubleTap) return
    onDoubleTap()
    const id = Date.now()
    setBurst(id)
    window.setTimeout(() => setBurst((current) => (current === id ? 0 : current)), BURST_MS)
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      event.stopPropagation()
      go(index + 1)
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      event.stopPropagation()
      go(index - 1)
    }
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (event.pointerType !== 'mouse') touchStart.current = event.clientX
  }

  function onPointerUp(event: PointerEvent<HTMLDivElement>) {
    if (event.pointerType === 'mouse') return
    const start = touchStart.current
    touchStart.current = null
    if (start !== null) {
      const delta = event.clientX - start
      if (delta <= -SWIPE_THRESHOLD) return go(index + 1)
      if (delta >= SWIPE_THRESHOLD) return go(index - 1)
    }
    const now = event.timeStamp
    if (now - lastTap.current < DOUBLE_TAP_MS) {
      lastTap.current = 0
      like()
    } else {
      lastTap.current = now
    }
  }

  const dots = (below: boolean) => (
    <ol aria-hidden="true" className={cn('pointer-events-none flex justify-center gap-1', below ? 'pt-3' : 'absolute inset-x-0 bottom-3')}>
      {images.map((image, position) => (
        <li
          key={image.id}
          className={cn('size-1.5 rounded-full', below ? (position === index ? 'bg-primary' : 'bg-dot') : position === index ? 'bg-white' : 'bg-white/50')}
        />
      ))}
    </ol>
  )

  const carousel = (
    <div
      role="region"
      aria-roledescription="carousel"
      aria-label={label}
      tabIndex={0}
      onKeyDown={onKeyDown}
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onDoubleClick={(event) => {
        event.preventDefault()
        like()
      }}
      onContextMenu={protect ? blockSave : undefined}
      className={cn('group relative select-none overflow-hidden outline-offset-[-2px]', fill ? 'h-full bg-black' : 'wash-rose')}
      style={fill ? undefined : { aspectRatio: String(mediaRatio(images)) }}
    >
      <div
        className="flex h-full transition-transform duration-200 ease-out"
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {images.map((image, position) => (
          <div
            key={image.id}
            className="h-full w-full shrink-0"
            aria-hidden={position !== index || undefined}
            aria-roledescription="slide"
            aria-label={`${position + 1} of ${count}`}
          >
            <img
              src={image.url}
              srcSet={image.srcset ?? undefined}
              sizes={image.srcset ? '(min-width: 768px) 470px, 100vw' : undefined}
              alt={image.alt}
              width={image.width ?? undefined}
              height={image.height ?? undefined}
              loading={position === 0 && (priority || fill) ? 'eager' : 'lazy'}
              fetchPriority={priority && position === 0 ? 'high' : undefined}
              decoding="async"
              referrerPolicy="no-referrer"
              draggable={protect ? false : undefined}
              onDragStart={protect ? blockSave : undefined}
              className={cn(
                'size-full',
                fill ? 'object-contain' : 'object-cover',
                protect && 'select-none [-webkit-touch-callout:none] [-webkit-user-drag:none]',
              )}
            />
          </div>
        ))}
      </div>

      {burst !== 0 && (
        <span aria-hidden="true" className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <Heart className="size-24 animate-heart-burst fill-white text-white drop-shadow-lg" strokeWidth={1.5} />
        </span>
      )}

      {count > 1 && (
        <>
          <button
            type="button"
            onClick={() => go(index - 1)}
            disabled={index === 0}
            className="absolute left-2 top-1/2 hidden size-7 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-[#262626] opacity-0 shadow transition-opacity duration-150 group-hover:opacity-100 focus-visible:opacity-100 disabled:invisible md:inline-flex"
          >
            <ChevronLeft aria-hidden="true" className="size-4" strokeWidth={2.5} />
            <span className="sr-only">Previous image</span>
          </button>
          <button
            type="button"
            onClick={() => go(index + 1)}
            disabled={index === count - 1}
            className="absolute right-2 top-1/2 hidden size-7 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-[#262626] opacity-0 shadow transition-opacity duration-150 group-hover:opacity-100 focus-visible:opacity-100 disabled:invisible md:inline-flex"
          >
            <ChevronRight aria-hidden="true" className="size-4" strokeWidth={2.5} />
            <span className="sr-only">Next image</span>
          </button>
          {!dotsBelow && dots(false)}
          <p className="sr-only" aria-live="polite">
            Image {index + 1} of {count}
          </p>
        </>
      )}
    </div>
  )

  if (!dotsBelow || count < 2) return carousel
  return (
    <div>
      {carousel}
      {dots(true)}
    </div>
  )
}
