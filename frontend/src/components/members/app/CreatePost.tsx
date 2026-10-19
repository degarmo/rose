import { ArrowDown, ArrowLeft, ArrowUp, ImagePlus, ShieldCheck, Trash2, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { cn } from '@/lib/cn'
import { members, type FeedPost } from '@/lib/membersApi'
import { exportRedacted, loadSource, NO_EDITS, type Edits, type Source } from '@/lib/redact'
import { useToast } from '../../ui'
import { RedactionEditor } from '../RedactionEditor'
import { Toggle } from '../Toggle'
import { IgButton, LeaveIcon } from './primitives'

const MAX_IMAGES = 10
const CAPTION_LIMIT = 2200

export type CreateStep = 'select' | 'redact' | 'details' | 'share'

const STEP_TITLES: Record<CreateStep, string> = {
  select: 'Create new post',
  redact: 'Crop & redact',
  details: 'Details',
  share: 'Share',
}

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
  onClose: () => void
  onPosted: (post: FeedPost) => void
}

/**
 * Select, then Crop & redact, then Details, then Share. Redaction runs on this device
 * and only the rendered result is uploaded. Photos need the consent attestation, which
 * sits on the Details step; Share stays disabled until it is ticked.
 */
export function CreatePost({ open, fullScreen, onClose, onPosted }: CreatePostProps) {
  const toast = useToast()
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

  function toShare() {
    if (items.length === 0 && !caption.trim()) {
      setError('Write something or add a photo.')
      return
    }
    setError('')
    setStep('share')
  }

  async function share() {
    if (items.length > 0 && !attested) {
      setError('Please confirm that everyone identifiable agreed before you share.')
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
      toast.show({
        tone: 'success',
        title: post.in_review ? 'Sent for a quick review' : 'Shared',
        message: post.in_review
          ? 'New members’ first posts are checked by our team before they appear.'
          : post.state === 'processing'
            ? 'Your photos are being prepared.'
            : undefined,
      })
      onPosted(post)
      close()
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
    else if (step === 'share') setStep('details')
  }

  const item = items[current]
  const steps: CreateStep[] = items.length ? ['select', 'redact', 'details', 'share'] : ['select', 'details', 'share']

  const next =
    step === 'select' ? (
      <IgButton variant="plain" disabled={busy || items.length === 0} onClick={() => setStep('redact')}>
        Next
      </IgButton>
    ) : step === 'redact' ? (
      <IgButton variant="plain" disabled={busy} aria-busy={busy} onClick={() => void renderAll()}>
        {busy ? 'Preparing' : 'Next'}
      </IgButton>
    ) : step === 'details' ? (
      <IgButton variant="plain" onClick={toShare}>
        Next
      </IgButton>
    ) : (
      <IgButton variant="plain" disabled={busy || (items.length > 0 && !attested)} aria-busy={busy} onClick={() => void share()}>
        {busy ? 'Sharing' : 'Share'}
      </IgButton>
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
        'm-0 max-h-none max-w-none bg-transparent p-0 text-fg open:flex',
        fullScreen ? 'h-dvh w-screen' : 'h-dvh w-screen items-center justify-center p-6',
      )}
    >
      <div
        className={cn(
          'flex flex-col overflow-hidden bg-canvas',
          fullScreen ? 'size-full' : 'h-[min(90dvh,820px)] w-full max-w-[760px] rounded-xl shadow-[var(--ui-shadow)]',
        )}
      >
        <header className="grid h-11 shrink-0 grid-cols-[1fr_auto_1fr] items-center border-b border-border px-2">
          <span className="justify-self-start">
            {step === 'select' ? (
              <button type="button" onClick={close} className="inline-flex size-10 items-center justify-center text-fg">
                <X aria-hidden="true" className="size-6" strokeWidth={1.75} />
                <span className="sr-only">Close</span>
              </button>
            ) : (
              <button type="button" onClick={back} className="inline-flex size-10 items-center justify-center text-fg">
                <ArrowLeft aria-hidden="true" className="size-6" strokeWidth={1.75} />
                <span className="sr-only">Back</span>
              </button>
            )}
          </span>
          <h2 id={titleId} className="text-base font-semibold text-fg">
            {STEP_TITLES[step]}
          </h2>
          <span className="flex items-center justify-self-end">
            {step === 'select' && items.length === 0 ? null : next}
            <LeaveIcon className="text-danger" />
          </span>
        </header>
        <ol className="flex gap-1 px-4 pt-3" aria-label="Steps">
          {steps.map((s) => (
            <li key={s} aria-current={s === step ? 'step' : undefined} className={cn('h-0.5 flex-1 rounded-full', s === step ? 'bg-fg' : 'bg-border')}>
              <span className="sr-only">{STEP_TITLES[s]}</span>
            </li>
          ))}
        </ol>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {step === 'select' && (
            <div className="flex h-full min-h-72 flex-col items-center justify-center gap-4 text-center">
              <ImagePlus aria-hidden="true" className="size-20 text-fg" strokeWidth={1} />
              <p className="text-xl text-fg">Choose up to {MAX_IMAGES} photos</p>
              <input
                ref={fileInput}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
                multiple
                className="sr-only"
                id="composer-files"
                onChange={(event) => void pick(event.target.files)}
              />
              <label htmlFor="composer-files" className="inline-flex h-8 cursor-pointer items-center rounded-lg bg-primary px-4 text-sm font-semibold text-on-primary hover:bg-primary-hover">
                {busy ? 'Opening photos' : 'Choose photos'}
              </label>
              {items.length > 0 ? (
                <p className="text-fg">
                  {items.length} photo{items.length === 1 ? '' : 's'} chosen. Next, cover anything that could identify someone.
                </p>
              ) : (
                <IgButton variant="plain" onClick={() => setStep('details')}>
                  Write a text post
                </IgButton>
              )}
            </div>
          )}

          {step === 'redact' && item && (
            <div>
              <p className="mb-3 text-fg-muted" aria-live="polite">
                Photo {current + 1} of {items.length}
              </p>
              <RedactionEditor
                key={item.key}
                source={item.source}
                edits={item.edits}
                onChange={(edits) => setItems((list) => list.map((entry, i) => (i === current ? { ...entry, edits } : entry)))}
              />
              {items.length > 1 && (
                <div className="mt-4 flex gap-2">
                  <IgButton variant="secondary" disabled={current === 0} onClick={() => setCurrent((i) => i - 1)}>
                    Previous photo
                  </IgButton>
                  <IgButton variant="secondary" disabled={current === items.length - 1} onClick={() => setCurrent((i) => i + 1)}>
                    Next photo
                  </IgButton>
                </div>
              )}
            </div>
          )}

          {step === 'details' && (
            <div className="flex flex-col gap-6">
              {items.length > 0 && (
                <ul className="flex flex-col gap-3" aria-label="Photos in this post">
                  {items.map((entry, index) => (
                    <li key={entry.key} className="flex gap-3">
                      {entry.preview && <img src={entry.preview} alt="" className="size-20 shrink-0 rounded-[4px] object-cover" draggable={false} />}
                      <div className="min-w-0 flex-1">
                        <label htmlFor={`alt-${entry.key}`} className="block font-semibold text-fg">
                          Describe photo {index + 1}
                        </label>
                        <input
                          id={`alt-${entry.key}`}
                          maxLength={200}
                          value={entry.alt}
                          placeholder="Helps people using screen readers"
                          onChange={(e) => setItems((list) => list.map((x, i) => (i === index ? { ...x, alt: e.target.value } : x)))}
                          className="mt-1 h-9 w-full rounded-lg border border-border-strong bg-surface px-3 text-sm text-fg placeholder:text-fg-muted"
                        />
                        <div className="mt-1 flex gap-1">
                          <button type="button" className="inline-flex size-8 items-center justify-center rounded-lg text-fg hover:bg-hover disabled:opacity-30" disabled={index === 0} onClick={() => move(index, -1)}>
                            <ArrowUp aria-hidden="true" className="size-4" />
                            <span className="sr-only">Move photo {index + 1} earlier</span>
                          </button>
                          <button type="button" className="inline-flex size-8 items-center justify-center rounded-lg text-fg hover:bg-hover disabled:opacity-30" disabled={index === items.length - 1} onClick={() => move(index, 1)}>
                            <ArrowDown aria-hidden="true" className="size-4" />
                            <span className="sr-only">Move photo {index + 1} later</span>
                          </button>
                          <button type="button" className="inline-flex size-8 items-center justify-center rounded-lg text-fg hover:bg-hover hover:text-danger" onClick={() => setItems((list) => list.filter((_, i) => i !== index))}>
                            <Trash2 aria-hidden="true" className="size-4" />
                            <span className="sr-only">Remove photo {index + 1}</span>
                          </button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              <div>
                <label htmlFor={captionId} className="block font-semibold text-fg">
                  Caption{items.length ? <span className="font-normal text-fg-muted"> (optional)</span> : null}
                </label>
                <textarea
                  id={captionId}
                  rows={5}
                  maxLength={CAPTION_LIMIT}
                  value={caption}
                  onChange={(e) => {
                    setCaption(e.target.value)
                    setError('')
                  }}
                  placeholder="Write a caption…"
                  className="mt-1 w-full resize-y rounded-lg border border-border-strong bg-surface p-3 text-sm text-fg placeholder:text-fg-muted"
                />
                <p className="text-right text-xs text-fg-muted">
                  {caption.length} / {CAPTION_LIMIT}
                </p>
              </div>
              <Toggle label="Mark as sensitive" hint="Photos stay blurred until someone taps View." checked={sensitive} onChange={setSensitive} />
              <Toggle label="Allow comments" checked={comments} onChange={setComments} />
              {items.length > 0 && (
                <div className="flex gap-3 rounded-lg border border-border p-4">
                  <input
                    id={attestId}
                    type="checkbox"
                    checked={attested}
                    onChange={(event) => {
                      setAttested(event.target.checked)
                      setError('')
                    }}
                    className="mt-0.5 size-5 shrink-0 accent-[var(--color-primary)]"
                  />
                  <label htmlFor={attestId} className="leading-relaxed text-fg">
                    <ShieldCheck aria-hidden="true" className="mr-1 inline size-4" />
                    Everyone identifiable in these photos agreed to them being posted here.
                  </label>
                </div>
              )}
            </div>
          )}

          {step === 'share' && (
            <div className="mx-auto flex max-w-sm flex-col gap-4">
              {items[0]?.preview && (
                <div className="relative">
                  <img src={items[0].preview} alt="" className="w-full rounded-[4px] border border-border object-cover" draggable={false} />
                  {items.length > 1 && <span className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-0.5 text-xs font-semibold text-white">1 of {items.length}</span>}
                </div>
              )}
              {caption.trim() ? <p className="whitespace-pre-line break-words text-fg">{caption}</p> : <p className="text-fg-muted">No caption.</p>}
              <ul className="text-fg-muted">
                <li>{sensitive ? 'Marked sensitive: blurred until someone taps View.' : 'Not marked sensitive.'}</li>
                <li>{comments ? 'Comments on.' : 'Comments off.'}</li>
              </ul>
              {items.length > 0 && !attested && (
                <p className="text-danger">Go back to Details and confirm that everyone identifiable agreed. Share stays off until then.</p>
              )}
            </div>
          )}

          {error && (
            <p role="alert" className="mt-4 text-danger">
              {error}
            </p>
          )}
        </div>
      </div>
    </dialog>
  )
}
