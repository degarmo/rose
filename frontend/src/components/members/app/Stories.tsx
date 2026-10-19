import { X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/cn'
import { formatEventDate } from '@/lib/format'
import { members, type StoryGroup, type StoryItem } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { SiteLink } from './PostCard'
import { LeaveIcon, RoseMark } from './primitives'

const STORY_MS = 5000
// The circle (64px), a 6px gap and an 18px label, with 8px above and 12px below on phones
// and 8px below wider; the loading placeholder takes the same height.
const TRAY_HEIGHT = 'h-[108px] md:h-24'

/** What fills a circle without a picture (design: Tonight oxblood, This week rose, Journal warm, News grey). */
const GROUP_FILLS: Record<string, string> = {
  tonight: 'bg-oxblood',
  'this-week': 'wash-rose',
  journal: 'wash-warm',
  news: 'bg-control',
}

function reducedMotion() {
  return typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Design: 64px with a 2px ring (rose unseen, grey seen) and 3px of page colour inside it. */
function Circle({ group }: { group: StoryGroup }) {
  const image = group.items.find((item) => item.image)?.image
  return (
    <span aria-hidden="true" className={cn('inline-flex size-16 rounded-full border-2 p-[3px]', group.seen ? 'border-border' : 'border-primary')}>
      <span className={cn('relative inline-flex size-full overflow-hidden rounded-full', GROUP_FILLS[group.id] ?? 'bg-control')}>
        {image && <img src={image.url} alt="" className="size-full object-cover" loading="lazy" />}
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
      <ul className="flex gap-3 overflow-x-auto px-4 pb-3 pt-2 [scrollbar-width:none] md:gap-3.5 md:px-0 md:pb-2 md:pt-0">
        {groups.map((group, index) => (
          <li key={group.id} className="shrink-0">
            <button type="button" onClick={() => setOpen(index)} className="flex w-[72px] flex-col items-center gap-1.5">
              <Circle group={group} />
              <span className="w-full truncate text-center text-meta text-fg">
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
  return ''
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
      className="m-0 h-dvh max-h-none w-screen max-w-none bg-story p-0 text-white open:flex open:items-center open:justify-center"
    >
      <span aria-hidden="true" className="absolute left-6 top-5 hidden font-serif text-[1.625rem] leading-none md:block">
        Rose
      </span>
      <div className="absolute right-4 top-4 hidden items-center gap-1 md:flex">
        <LeaveIcon className="text-white" />
        <button type="button" onClick={onClose} className="inline-flex size-10 items-center justify-center">
          <X aria-hidden="true" className="size-6" strokeWidth={1.8} />
          <span className="sr-only">Close stories</span>
        </button>
      </div>
      <div className="relative flex h-full w-full flex-col overflow-hidden bg-[repeating-linear-gradient(135deg,#3a2a2f_0_12px,#2e2226_12px_24px)] px-3 pb-9 pt-14 md:h-[min(782px,calc(100dvh-48px))] md:w-[440px] md:rounded-sheet md:pb-5 md:pt-3">
        {item.image && <img src={item.image.url} alt={item.image.alt} className="absolute inset-0 size-full object-cover" />}
        {item.image && <div aria-hidden="true" className="absolute inset-0 bg-linear-to-t from-black/80 via-black/30 to-black/40" />}
        <ol className="relative z-10 flex gap-1" aria-hidden="true">
          {group.items.map((entry, index) => (
            <li key={entry.key} className="h-0.5 flex-1 overflow-hidden rounded-[1px] bg-white/35">
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
        <header className="relative z-10 flex items-center gap-2.5 pt-3">
          <RoseMark className="size-8 border border-white/50 text-sm" />
          <span className="min-w-0 flex-1 truncate text-[0.8125rem]">
            <span className="font-semibold">Rose</span> <span className="opacity-70">{[group.title, itemMeta(item)].filter(Boolean).join(' · ')}</span>
          </span>
          <span className="flex items-center md:hidden">
            <LeaveIcon className="text-white" />
            <button type="button" onClick={onClose} className="inline-flex size-10 items-center justify-center">
              <X aria-hidden="true" className="size-6" strokeWidth={1.8} />
              <span className="sr-only">Close stories</span>
            </button>
          </span>
        </header>

        {/* Tap zones: the left third goes back, the rest goes forward. */}
        <button type="button" onClick={() => step(-1)} className="absolute inset-y-24 left-0 z-0 w-1/3" tabIndex={-1} aria-hidden="true" />
        <button type="button" onClick={() => step(1)} className="absolute inset-y-24 right-0 z-0 w-2/3" tabIndex={-1} aria-hidden="true" />

        <div className="pointer-events-none relative z-10 mt-auto flex flex-col">
          <h2 className="mb-2 font-serif text-[2rem] font-normal leading-[1.1]">{item.title}</h2>
          {item.text && <p className="mb-5 text-sm opacity-85">{item.text}</p>}
          {item.link && (
            <SiteLink to={item.link.url} className="pointer-events-auto flex h-11 items-center justify-center rounded-app bg-white font-semibold text-[#262626]">
              {item.link.label}
            </SiteLink>
          )}
        </div>
      </div>
    </dialog>
  )
}
