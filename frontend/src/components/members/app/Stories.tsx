import { BookOpen, CalendarDays, ChevronLeft, ChevronRight, Megaphone, X, type LucideIcon } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/cn'
import { formatEventDate } from '@/lib/format'
import { members, type StoryGroup, type StoryItem } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { SiteLink } from './PostCard'
import { LeaveIcon, RoseMark } from './primitives'
import { igButtonClasses } from './ui'

const STORY_MS = 5000
// 8px padding, the circle (64px on phones, 66px wider), 4px gap, a 16px label, 8px padding:
// the tabs below sit 8px under the labels, and the loading placeholder is the same height.
const TRAY_HEIGHT = 'h-[100px] md:h-[102px]'

const GROUP_ICONS: Record<string, LucideIcon> = {
  tonight: CalendarDays,
  'this-week': CalendarDays,
  journal: BookOpen,
  news: Megaphone,
}

function reducedMotion() {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function Circle({ group }: { group: StoryGroup }) {
  const Icon = GROUP_ICONS[group.id] ?? CalendarDays
  const image = group.items.find((item) => item.image)?.image
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-flex size-16 items-center justify-center rounded-full p-[3px] md:size-[66px]',
        group.seen ? 'bg-border' : 'bg-primary',
      )}
    >
      <span className="inline-flex size-full items-center justify-center rounded-full bg-canvas p-[2px]">
        <span className="relative inline-flex size-full items-center justify-center overflow-hidden rounded-full bg-surface text-fg">
          {image ? <img src={image.url} alt="" className="size-full object-cover" loading="lazy" /> : <Icon className="size-6" strokeWidth={1.75} />}
        </span>
      </span>
    </span>
  )
}

/** Staff-made circles only: Tonight, This week, the journal and news. Unseen ones get a rose ring. */
export function StoriesTray() {
  const [version, setVersion] = useState(0)
  const state = useAsync(() => members.stories(), `stories|${version}`)
  const [open, setOpen] = useState<number | null>(null)

  if (state.status !== 'success' || state.data.results.length === 0) {
    // Keep the tray's height while it loads, so the feed below does not jump.
    return state.status === 'loading' ? <div aria-hidden="true" className={TRAY_HEIGHT} /> : null
  }
  const groups = state.data.results

  return (
    <section aria-label="Stories" className={TRAY_HEIGHT}>
      <ul className="flex gap-4 overflow-x-auto px-2 py-2 [scrollbar-width:none]">
        {groups.map((group, index) => (
          <li key={group.id} className="shrink-0">
            <button type="button" onClick={() => setOpen(index)} className="flex w-16 flex-col items-center gap-1 md:w-[66px]">
              <Circle group={group} />
              <span className="w-full truncate text-center text-xs text-fg">
                {group.title}
                <span className="sr-only">{group.seen ? ', seen' : ', new'}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {open !== null && (
        <StoryViewer
          groups={groups}
          start={open}
          onClose={() => {
            setOpen(null)
            setVersion((n) => n + 1)
          }}
        />
      )}
    </section>
  )
}

function itemMeta(item: StoryItem) {
  if (item.kind === 'event' && item.starts_at) return formatEventDate(item.starts_at)
  if (item.kind === 'journal') return 'Journal'
  return 'From the club'
}

/**
 * Full screen, with a progress bar per item. Tap the left or right of the screen, or use
 * the arrow keys, to move; Esc closes. Each item is marked seen as it opens. With reduced
 * motion the bars stand still and nothing advances on its own.
 */
export function StoryViewer({ groups, start, onClose }: { groups: StoryGroup[]; start: number; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [position, setPosition] = useState({ group: start, item: 0 })
  const [still] = useState(reducedMotion)
  const group = groups[position.group]
  const item = group.items[position.item]

  const step = useCallback(
    (delta: 1 | -1) => {
      const { group: g, item: i } = position
      const nextItem = i + delta
      if (nextItem >= 0 && nextItem < groups[g].items.length) return setPosition({ group: g, item: nextItem })
      const nextGroup = g + delta
      if (nextGroup < 0) return setPosition({ group: g, item: 0 })
      if (nextGroup >= groups.length) return onClose()
      setPosition({ group: nextGroup, item: delta === 1 ? 0 : groups[nextGroup].items.length - 1 })
    },
    [position, groups, onClose],
  )

  useEffect(() => {
    const element = dialog.current
    if (element && !element.open) element.showModal()
  }, [])

  useEffect(() => {
    if (!item.seen) void members.markStoriesSeen([item.key])
  }, [item])

  useEffect(() => {
    if (still) return
    const timer = window.setTimeout(() => step(1), STORY_MS)
    return () => window.clearTimeout(timer)
  }, [position, step, still])

  return (
    <dialog
      ref={dialog}
      aria-label={`${group.title} stories`}
      onClose={onClose}
      onKeyDown={(event) => {
        if (event.key === 'ArrowRight') {
          event.preventDefault()
          step(1)
        } else if (event.key === 'ArrowLeft') {
          event.preventDefault()
          step(-1)
        }
      }}
      className="m-0 h-dvh max-h-none w-screen max-w-none bg-[#1a1a1a] p-0 text-white open:flex open:items-center open:justify-center"
    >
      <div className="relative flex h-full w-full max-w-[min(100vw,calc(100dvh*9/16))] flex-col bg-[#262626] md:my-6 md:h-[calc(100dvh-3rem)] md:rounded-lg">
        <ol className="absolute inset-x-2 top-2 z-10 flex gap-1" aria-hidden="true">
          {group.items.map((entry, index) => (
            <li key={entry.key} className="h-0.5 flex-1 overflow-hidden rounded-full bg-white/35">
              <span
                key={`${position.group}-${position.item}`}
                className={cn(
                  'block h-full origin-left bg-white',
                  index < position.item && 'scale-x-100',
                  index > position.item && 'scale-x-0',
                  index === position.item && (still ? 'scale-x-100' : 'animate-story-progress'),
                )}
                style={index === position.item ? ({ '--story-duration': `${STORY_MS}ms` } as React.CSSProperties) : undefined}
              />
            </li>
          ))}
        </ol>
        <header className="absolute inset-x-0 top-4 z-10 flex items-center gap-2 px-4 pt-2">
          <span className="inline-flex size-8 items-center justify-center rounded-full bg-white">
            <RoseMark className="size-7 text-sm" />
          </span>
          <span className="text-sm font-semibold">{group.title}</span>
          <span className="text-sm text-white/80">{itemMeta(item)}</span>
          <LeaveIcon className="ml-auto text-white" />
          <button type="button" onClick={onClose} className="inline-flex size-10 items-center justify-center">
            <X aria-hidden="true" className="size-6" />
            <span className="sr-only">Close stories</span>
          </button>
        </header>

        <div className="relative flex min-h-0 flex-1 flex-col justify-end overflow-hidden">
          {item.image && <img src={item.image.url} alt={item.image.alt} className="absolute inset-0 size-full object-cover" />}
          <div className="relative bg-gradient-to-t from-black/85 via-black/60 to-transparent px-6 pb-24 pt-24">
            <h2 className="text-2xl font-semibold leading-tight">{item.title}</h2>
            {item.text && <p className="mt-2 text-[0.9375rem] leading-relaxed text-white/90">{item.text}</p>}
          </div>
          {/* Tap zones: the left third goes back, the rest goes forward. */}
          <button type="button" onClick={() => step(-1)} className="absolute inset-y-16 left-0 w-1/3" tabIndex={-1} aria-hidden="true" />
          <button type="button" onClick={() => step(1)} className="absolute inset-y-16 right-0 w-2/3" tabIndex={-1} aria-hidden="true" />
        </div>

        {item.link && (
          <div className="absolute inset-x-0 bottom-6 z-10 flex justify-center px-6">
            <SiteLink to={item.link.url} className={igButtonClasses('primary', 'w-full max-w-xs')}>
              {item.link.label}
            </SiteLink>
          </div>
        )}

        <button
          type="button"
          onClick={() => step(-1)}
          className="absolute -left-12 top-1/2 hidden size-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-[#262626] md:inline-flex"
        >
          <ChevronLeft aria-hidden="true" className="size-5" />
          <span className="sr-only">Previous story</span>
        </button>
        <button
          type="button"
          onClick={() => step(1)}
          className="absolute -right-12 top-1/2 hidden size-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-[#262626] md:inline-flex"
        >
          <ChevronRight aria-hidden="true" className="size-5" />
          <span className="sr-only">Next story</span>
        </button>
      </div>
    </dialog>
  )
}
