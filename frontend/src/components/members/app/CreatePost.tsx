import { ArrowDown, ArrowLeft, ArrowUp, Check, ChevronLeft, ChevronRight, Image as ImageIcon, Trash2, X } from 'lucide-react'
import { useEffect, useId, useRef, useState, type DragEvent, type ReactNode } from 'react'
import { CheckboxBox, Toggle } from '@/components/ui'
import { cn } from '@/lib/cn'
import { members, type FeedPost, type MemberCard } from '@/lib/membersApi'
import { exportRedacted, loadSource, NO_EDITS, type Edits, type Source } from '@/lib/redact'
import { Avatar } from '../Avatar'
import { RedactionEditor } from '../RedactionEditor'
import { LeaveButton } from './Nav'
import { LeaveIcon } from './primitives'
import { appButtonClasses, ICON } from './ui'

const MAX_IMAGES = 10
const CAPTION_LIMIT = 2200

export type CreateStep = 'select' | 'redact' | 'details' | 'share'

interface Item {
  key: string
  source: Source & CanvasImageSource
  edits: Edits
  alt: string
  /** Object URL of the rendered, redacted image; never of the original. */
  preview: string | null
  output: Blob | null
}

interface CreatePostProps {
  open: boolean
  /** Phones get a full-screen sheet; wider screens a centred modal. */
  fullScreen: boolean
  /** Shown beside the caption on the Details step. */
  author?: MemberCard
  onClose: () => void
  onPosted: (post: FeedPost) => void
}

/** The modal's size on each step (design: 560×600, 700×742, 860×600, 560×600). */
const MODAL_SIZE: Record<CreateStep, string> = {
  select: 'h-[600px] w-[560px]',
  redact: 'h-[742px] w-[700px]',
  details: 'h-[600px] w-[860px]',
  share: 'h-[600px] w-[560px]',
}

/** The rose text button in the header: Next or Share, grey while it cannot be used. */
function HeaderAction({ children, label, disabled, busy, onClick }: { children: ReactNode; label?: string; disabled?: boolean; busy?: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-busy={busy || undefined}
      disabled={disabled}
      onClick={onClick}
      className="inline-flex h-10 items-center px-1 font-semibold text-link hover:text-primary-hover disabled:cursor-not-allowed disabled:text-fg-faint"
    >
      {children}
    </button>
  )
}

function shareMessage(post: FeedPost) {
  if (post.in_review) return 'You can see it now. Everyone else will see it after a quick look from a host.'
  if (post.state === 'processing') return 'Your photos are being prepared. It will be in the feed in a moment.'
  return 'It is in the feed now.'
}

/**
 * Create (design: "Create"): Select, then Crop & redact, then Details, then Post shared.
 * Redaction runs on this device and only the rendered result is uploaded. Photos need the
 * consent attestation on the Details step; Share stays off until it is ticked.
 */
export function CreatePost({ open, fullScreen, author, onClose, onPosted }: CreatePostProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const titleId = useId()
  const attestId = useId()
  const captionId = useId()
  const [step, setStep] = useState<CreateStep>('select')
  const [items, setItems] = useState<Item[]>([])
  const [current, setCurrent] = useState(0)
  const [caption, setCaption] = useState('')
  const [sensitive, setSensitive] = useState(false)
  const [comments, setComments] = useState(true)
  const [attested, setAttested] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [shared, setShared] = useState<FeedPost | null>(null)
  const previews = useRef<string[]>([])

  useEffect(() => {
    const element = dialog.current
    if (!element) return
    if (open && !element.open) element.showModal()
    if (!open && element.open) element.close()
  }, [open])

  useEffect(
    () => () => {
      previews.current.forEach((url) => URL.revokeObjectURL(url))
    },
    [],
  )

  function reset() {
    previews.current.forEach((url) => URL.revokeObjectURL(url))
    previews.current = []
    setStep('select')
    setItems([])
    setCurrent(0)
    setCaption('')
    setSensitive(false)
    setComments(true)
    setAttested(false)
    setError('')
    setShared(null)
  }

  function close() {
    reset()
    onClose()
  }

  async function pick(files: FileList | null) {
    if (!files?.length) return
    const room = MAX_IMAGES - items.length
    const chosen = Array.from(files).slice(0, room)
    setBusy(true)
    setError('')
    try {
      const loaded = await Promise.all(
        chosen.map(async (file, index) => ({
          key: `${Date.now()}-${index}-${file.name}`,
          source: (await loadSource(file)) as unknown as Source & CanvasImageSource,
          edits: NO_EDITS,
          alt: '',
          preview: null,
          output: null,
        })),
      )
      setItems((existing) => [...existing, ...loaded])
      if (files.length > room) setError(`A post can have up to ${MAX_IMAGES} photos.`)
    } catch {
      setError('One of those files could not be opened as a photo.')
    } finally {
      setBusy(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    const files = event.dataTransfer.files
    if (Array.from(files).some((file) => !file.type.startsWith('image/'))) {
      setError('Only photos can be added.')
      return
    }
    void pick(files)
  }

  /** Render every image through the redaction pipeline; the results are what gets uploaded. */
  async function renderAll() {
    setBusy(true)
    try {
      const rendered = await Promise.all(
        items.map(async (item) => {
          const output = await exportRedacted(item.source, item.edits)
          const preview = URL.createObjectURL(output)
          previews.current.push(preview)
          return { ...item, output, preview }
        }),
      )
      setItems(rendered)
      setStep('details')
    } catch {
      setError('The photos could not be prepared. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  function move(index: number, delta: number) {
    setItems((list) => {
      const next = [...list]
      const [item] = next.splice(index, 1)
      next.splice(index + delta, 0, item)
      return next
    })
  }

  async function share() {
    if (items.length === 0 && !caption.trim()) {
      setError('Write something or add a photo.')
      return
    }
    if (items.length > 0 && !attested) {
      setError('Please confirm that everyone identifiable is 18 or older and agreed before you share.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const post = await members.createPost({
        caption,
        isSensitive: sensitive,
        commentsEnabled: comments,
        consentAttested: attested,
        images: items.map((item) => ({ blob: item.output as Blob, alt: item.alt.trim() })),
      })
      onPosted(post)
      setShared(post)
      setStep('share')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Your post was not shared. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  function back() {
    setError('')
    if (step === 'redact') setStep('select')
    else if (step === 'details') setStep(items.length ? 'redact' : 'select')
  }

  const item = items[current]
  const photos = items.length > 0
  const shareBlocked = busy || (photos && !attested)
  const title = step === 'select' ? (fullScreen ? 'New post' : 'Create new post') : step === 'redact' ? 'Crop & redact' : step === 'details' ? 'Details' : 'Post shared'

  const action =
    step === 'select' ? (
      photos || fullScreen ? (
        <HeaderAction disabled={busy || !photos} onClick={() => setStep('redact')}>
          Next
        </HeaderAction>
      ) : null
    ) : step === 'redact' ? (
      <HeaderAction disabled={busy} busy={busy} onClick={() => void renderAll()}>
        {busy ? 'Preparing' : 'Next'}
      </HeaderAction>
    ) : step === 'details' ? (
      <HeaderAction label="Share post" disabled={shareBlocked} busy={busy} onClick={() => void share()}>
        Share
      </HeaderAction>
    ) : fullScreen ? (
      <HeaderAction onClick={close}>Done</HeaderAction>
    ) : null

  const iconButton = 'inline-flex size-10 items-center justify-center text-fg'
  const leading =
    step === 'select' ? (
      fullScreen && (
        <button type="button" onClick={close} className={cn(iconButton, '-ml-2')}>
          <X aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
          <span className="sr-only">Close</span>
        </button>
      )
    ) : step === 'share' ? null : (
      <button type="button" onClick={back} className={cn(iconButton, '-ml-2')}>
        <ArrowLeft aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
        <span className="sr-only">Back</span>
      </button>
    )

  const fileField = (
    <input
      ref={fileInput}
      type="file"
      accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
      multiple
      className="peer sr-only"
      id="composer-files"
      onChange={(event) => void pick(event.target.files)}
    />
  )
  const chooseLabel = busy ? 'Opening photos' : photos ? 'Add more photos' : fullScreen ? 'Select photos' : 'Select from computer'

  const select = (
    <div
      className={cn('flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center transition-colors', dragging && 'bg-surface')}
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <ImageIcon aria-hidden="true" size={72} strokeWidth={1.2} className="text-fg" />
      <p className="text-xl text-fg">{fullScreen ? 'Choose photos to share' : 'Drag photos here'}</p>
      <p className="max-w-[300px] text-meta text-fg-muted">No faces without consent. You can blur or block parts of the photo in the next step.</p>
      {fileField}
      <label htmlFor="composer-files" className={appButtonClasses(photos ? 'secondary' : 'primary', cn('cursor-pointer peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-link', fullScreen && 'h-11 px-6'))}>
        {chooseLabel}
      </label>
      {photos ? (
        <p className="text-fg" aria-live="polite">
          {items.length} photo{items.length === 1 ? '' : 's'} chosen. Next, cover anything that could identify someone.
        </p>
      ) : (
        <button type="button" onClick={() => setStep('details')} className="min-h-6 font-semibold text-link hover:text-primary-hover">
          Write a text post
        </button>
      )}
    </div>
  )

  const photoArrows = items.length > 1 && (
    <>
      <p className="absolute left-1/2 top-3 -translate-x-1/2 rounded-full bg-black/60 px-2.5 py-0.5 text-meta font-semibold text-white" aria-live="polite">
        Photo {current + 1} of {items.length}
      </p>
      <button
        type="button"
        disabled={current === 0}
        onClick={() => setCurrent((i) => i - 1)}
        className="absolute left-3 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-[#262626] shadow disabled:hidden"
      >
        <ChevronLeft aria-hidden="true" className="size-5" />
        <span className="sr-only">Previous photo</span>
      </button>
      <button
        type="button"
        disabled={current === items.length - 1}
        onClick={() => setCurrent((i) => i + 1)}
        className="absolute right-3 top-1/2 inline-flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-[#262626] shadow disabled:hidden"
      >
        <ChevronRight aria-hidden="true" className="size-5" />
        <span className="sr-only">Next photo</span>
      </button>
    </>
  )

  const redact = item && (
    <div className={cn('flex min-h-0 flex-1 flex-col', fullScreen && 'overflow-y-auto pb-4')}>
      <RedactionEditor
        key={item.key}
        layout={fullScreen ? 'stacked' : 'overlay'}
        inset
        source={item.source}
        edits={item.edits}
        onChange={(edits) => setItems((list) => list.map((entry, i) => (i === current ? { ...entry, edits } : entry)))}
      >
        {photoArrows}
      </RedactionEditor>
    </div>
  )

  const iconSmall = 'inline-flex size-6 items-center justify-center rounded-app text-fg hover:bg-surface disabled:opacity-30'
  const photoList = photos && (
    <ul className="flex flex-col gap-3" aria-label="Photos in this post">
      {items.map((entry, index) => (
        <li key={entry.key} className="flex gap-3">
          {entry.preview && <img src={entry.preview} alt="" className="size-12 shrink-0 rounded-[4px] object-cover" draggable={false} />}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-0.5">
              <label htmlFor={`alt-${entry.key}`} className="flex-1 text-meta font-semibold text-fg">
                Describe photo {index + 1}
              </label>
              {items.length > 1 && (
                <>
                  <button type="button" className={iconSmall} disabled={index === 0} onClick={() => move(index, -1)}>
                    <ArrowUp aria-hidden="true" className="size-4" />
                    <span className="sr-only">Move photo {index + 1} earlier</span>
                  </button>
                  <button type="button" className={iconSmall} disabled={index === items.length - 1} onClick={() => move(index, 1)}>
                    <ArrowDown aria-hidden="true" className="size-4" />
                    <span className="sr-only">Move photo {index + 1} later</span>
                  </button>
                </>
              )}
              <button
                type="button"
                className={cn(iconSmall, 'hover:text-danger')}
                onClick={() => {
                  setItems((list) => list.filter((_, i) => i !== index))
                  setCurrent(0)
                }}
              >
                <Trash2 aria-hidden="true" className="size-4" />
                <span className="sr-only">Remove photo {index + 1}</span>
              </button>
            </div>
            <input
              id={`alt-${entry.key}`}
              maxLength={200}
              value={entry.alt}
              placeholder="Helps people using screen readers"
              onChange={(e) => setItems((list) => list.map((x, i) => (i === index ? { ...x, alt: e.target.value } : x)))}
              className="mt-1 h-8 w-full rounded-app bg-field px-2.5 text-sm text-fg placeholder:text-fg-muted-tint"
            />
          </div>
        </li>
      ))}
    </ul>
  )

  const captionField = (
    <div className="min-w-0 flex-1">
      <label htmlFor={captionId} className="sr-only">
        Caption{photos ? ' (optional)' : ''}
      </label>
      <textarea
        id={captionId}
        rows={fullScreen ? 4 : 5}
        maxLength={CAPTION_LIMIT}
        value={caption}
        onChange={(e) => {
          setCaption(e.target.value)
          setError('')
        }}
        placeholder="Write a caption…"
        className="block w-full resize-none bg-transparent text-fg placeholder:text-fg-muted focus:outline-none"
      />
      <p className="text-right text-meta text-fg-muted">
        {caption.length} / {CAPTION_LIMIT}
      </p>
    </div>
  )

  const toggles = (
    <>
      <Toggle label="Sensitive" hint="Blurred until a member taps View" checked={sensitive} onChange={setSensitive} className={fullScreen ? 'border-b border-border p-4' : 'border-t border-border pt-3'} />
      <Toggle label="Comments on" checked={comments} onChange={setComments} className={fullScreen ? 'border-b border-border p-4' : undefined} />
    </>
  )

  const consent = photos && (
    <div className={cn('flex gap-3', fullScreen ? 'p-4' : 'border-t border-border pt-3')}>
      <CheckboxBox
        id={attestId}
        checked={attested}
        onChange={(event) => {
          setAttested(event.target.checked)
          setError('')
        }}
        aria-required="true"
        tone="required"
      />
      <label htmlFor={attestId} className="text-fg">
        Everyone identifiable in these photos is 18 or older and agreed to them being posted here. <span className="text-link">Required</span>
      </label>
    </div>
  )

  const shareButton = (
    <button type="button" disabled={shareBlocked} aria-busy={busy || undefined} onClick={() => void share()} className={appButtonClasses('primary', cn('w-full', fullScreen && 'h-11'))}>
      {busy ? 'Sharing' : 'Share'}
    </button>
  )

  const errorLine = error && (
    <p role="alert" className={cn('text-danger', fullScreen ? 'px-4 pb-2' : '')}>
      {error}
    </p>
  )

  const details = fullScreen ? (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="flex gap-3 border-b border-border px-4 py-3">
        {items[0]?.preview && <img src={items[0].preview} alt="" className="h-20 w-16 shrink-0 object-cover" draggable={false} />}
        {captionField}
      </div>
      {photos && <div className="border-b border-border px-4 py-3">{photoList}</div>}
      {toggles}
      {consent}
      <div className="flex-1" />
      {errorLine}
      <div className="p-4">{shareButton}</div>
    </div>
  ) : (
    <div className="flex min-h-0 flex-1">
      {photos && (
        <div className="relative min-w-0 flex-1 bg-surface">
          {items[0]?.preview && <img src={items[0].preview} alt="" className="size-full object-contain" draggable={false} />}
          {items.length > 1 && <span className="absolute right-3 top-3 rounded-full bg-black/60 px-2 py-0.5 text-meta font-semibold text-white">1 of {items.length}</span>}
        </div>
      )}
      <div className={cn('flex min-w-0 flex-col', photos ? 'w-[335px] shrink-0 border-l border-border' : 'flex-1')}>
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
          {author && (
            <div className="flex items-center gap-3">
              <Avatar member={author} size="sm" />
              <span className="truncate font-semibold text-fg">{author.handle}</span>
            </div>
          )}
          {photoList}
          {captionField}
          {toggles}
        </div>
        <div className="flex shrink-0 flex-col gap-3 px-4 pb-4">
          {consent}
          {errorLine}
          {shareButton}
        </div>
      </div>
    </div>
  )

  const done = shared && (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <span className="inline-flex size-[72px] items-center justify-center rounded-full border-2 border-primary text-link">
        <Check aria-hidden="true" size={36} strokeWidth={2} />
      </span>
      <p className="text-xl text-fg">Your post has been shared.</p>
      <p className="max-w-[320px] text-fg-muted">{shareMessage(shared)}</p>
    </div>
  )

  return (
    <dialog
      ref={dialog}
      aria-labelledby={titleId}
      onClose={close}
      onClick={(event) => {
        if (event.target === dialog.current) close()
      }}
      className={cn(
        'm-0 h-dvh max-h-none w-screen max-w-none bg-transparent p-0 text-fg open:flex',
        !fullScreen && 'items-center justify-center p-6',
      )}
    >
      {!fullScreen && (
        <div className="fixed right-4 top-4 flex items-center gap-1 text-white">
          <LeaveIcon />
          <button type="button" onClick={close} className="inline-flex size-10 items-center justify-center">
            <X aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
            <span className="sr-only">Close</span>
          </button>
        </div>
      )}
      <div
        className={cn(
          'flex flex-col overflow-hidden bg-canvas',
          fullScreen ? 'size-full' : cn('max-h-[calc(100dvh-48px)] max-w-[calc(100vw-112px)] rounded-sheet shadow-modal', MODAL_SIZE[step], step === 'details' && !photos && 'w-[560px]'),
        )}
      >
        <header className={cn('grid shrink-0 grid-cols-[1fr_auto_1fr] items-center px-4', fullScreen ? 'h-11' : 'h-[42px] border-b border-border')}>
          <span className="flex justify-self-start">{leading}</span>
          <span className="min-w-0">
            <h2 id={titleId} className={cn('truncate text-base font-semibold text-fg', fullScreen && step === 'share' && 'sr-only')}>
              {title}
            </h2>
          </span>
          <span className="-mr-1 flex items-center justify-self-end gap-1">
            {action}
            {fullScreen && <LeaveButton className="-mr-2" />}
          </span>
        </header>

        {step === 'select' && (
          <>
            {select}
            {errorLine && <div className="px-4 pb-4">{errorLine}</div>}
          </>
        )}
        {step === 'redact' && (
          <>
            {redact}
            {errorLine && <div className="px-4 pb-4">{errorLine}</div>}
          </>
        )}
        {step === 'details' && details}
        {step === 'share' && done}
      </div>
    </dialog>
  )
}
