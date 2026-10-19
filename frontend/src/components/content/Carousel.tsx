import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useRef, useState, type KeyboardEvent, type TouchEvent } from 'react'
import type { RemoteImage } from '@/lib/api'
import { cn } from '@/lib/cn'
import { ImageFrame } from '../ui'

const SWIPE_THRESHOLD = 40

interface CarouselProps {
  images: RemoteImage[]
  label: string
  protect?: boolean
}

/** A journal post's pictures, one at a time: swipe on touch, arrow keys when focused, or the buttons. */
export function Carousel({ images, label, protect = false }: CarouselProps) {
  const [index, setIndex] = useState(0)
  const touchStart = useRef<number | null>(null)
  const count = Math.max(images.length, 1)
  const go = (next: number) => setIndex(Math.min(Math.max(next, 0), count - 1))

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      go(index + 1)
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      go(index - 1)
    }
  }

  function onTouchStart(event: TouchEvent<HTMLDivElement>) {
    touchStart.current = event.touches[0]?.clientX ?? null
  }

  function onTouchEnd(event: TouchEvent<HTMLDivElement>) {
    const start = touchStart.current
    const end = event.changedTouches[0]?.clientX
    touchStart.current = null
    if (start === null || end === undefined) return
    const delta = end - start
    if (delta <= -SWIPE_THRESHOLD) go(index + 1)
    else if (delta >= SWIPE_THRESHOLD) go(index - 1)
  }

  return (
    <div
      role="region"
      aria-roledescription="carousel"
      aria-label={label}
      tabIndex={0}
      onKeyDown={onKeyDown}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
      className="group relative overflow-hidden rounded-card bg-canvas"
    >
      <div
        className="flex transition-transform duration-500 ease-out"
        style={{ transform: `translateX(-${index * 100}%)` }}
      >
        {(images.length ? images : [null]).map((image, i) => (
          <div
            key={image?.url ?? 'placeholder'}
            role="group"
            aria-roledescription="slide"
            aria-label={`${i + 1} of ${count}`}
            aria-hidden={i !== index}
            className="w-full shrink-0"
          >
            <ImageFrame
              remote={image}
              alt={image?.alt ?? ''}
              ratio="1/1"
              placeholder="rose"
              sizes="(min-width: 1024px) 60vw, 100vw"
              protect={protect}
            />
          </div>
        ))}
      </div>

      {count > 1 && (
        <>
          <button
            type="button"
            onClick={() => go(index - 1)}
            disabled={index === 0}
            className="absolute left-3 top-1/2 inline-flex size-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-black shadow-sheet transition-opacity hover:bg-white disabled:opacity-0"
          >
            <ChevronLeft aria-hidden="true" className="size-5" />
            <span className="sr-only">Previous image</span>
          </button>
          <button
            type="button"
            onClick={() => go(index + 1)}
            disabled={index === count - 1}
            className="absolute right-3 top-1/2 inline-flex size-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-black shadow-sheet transition-opacity hover:bg-white disabled:opacity-0"
          >
            <ChevronRight aria-hidden="true" className="size-5" />
            <span className="sr-only">Next image</span>
          </button>
          <div aria-hidden="true" className="absolute inset-x-0 bottom-3 flex justify-center gap-1.5">
            {images.map((image, i) => (
              <span
                key={image.url}
                className={cn('size-1.5 rounded-full ring-1 ring-black/10 transition-colors', i === index ? 'bg-white' : 'bg-white/50')}
              />
            ))}
          </div>
          <p className="sr-only" aria-live="polite">
            Image {index + 1} of {count}
          </p>
        </>
      )}
    </div>
  )
}
