import { ArrowDown, ArrowLeft, ArrowUp, ImagePlus, ShieldCheck, Trash2 } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { cn } from '@/lib/cn'
import { members, type FeedPost } from '@/lib/membersApi'
import { exportRedacted, loadSource, NO_EDITS, type Edits, type Source } from '@/lib/redact'
import { Button, FormField, Input, Modal, Textarea, useToast } from '../ui'
import { RedactionEditor } from './RedactionEditor'
import { Toggle } from './Toggle'

const MAX_IMAGES = 10
const CAPTION_LIMIT = 2200

export type ComposerStep = 'pick' | 'redact' | 'arrange' | 'details'

const STEP_TITLES: Record<ComposerStep, string> = {
  pick: 'Choose photos',
  redact: 'Cover anything identifying',
  arrange: 'Order and describe',
  details: 'Caption and post',
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

interface ComposerProps {
  open: boolean
  onClose: () => void
  onPosted: (post: FeedPost) => void
}

export function Composer({ open, onClose, onPosted }: ComposerProps) {
  const toast = useToast()
  const fileInput = useRef<HTMLInputElement>(null)
  const attestId = useId()
  const [step, setStep] = useState<ComposerStep>('pick')
  const [items, setItems] = useState<Item[]>([])
  const [current, setCurrent] = useState(0)
  const [caption, setCaption] = useState('')
  const [sensitive, setSensitive] = useState(false)
  const [comments, setComments] = useState(true)
  const [attested, setAttested] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const previews = useRef<string[]>([])

  useEffect(
    () => () => {
      previews.current.forEach((url) => URL.revokeObjectURL(url))
    },
    [],
  )

  function reset() {
    previews.current.forEach((url) => URL.revokeObjectURL(url))
    previews.current = []
    setStep('pick')
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
      setStep('arrange')
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

  async function submit() {
    if (items.length > 0 && !attested) {
      setError('Please confirm that everyone identifiable agreed before you post.')
      return
    }
    if (items.length === 0 && !caption.trim()) {
      setError('Write something or add a photo.')
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
        title: post.in_review ? 'Sent for a quick review' : 'Posted',
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

  const item = items[current]

  return (
    <Modal open={open} onClose={close} title={STEP_TITLES[step]} variant="sheet">
      <div className="mx-auto flex h-full max-w-2xl flex-col">
        <ol className="mb-6 flex gap-2" aria-label="Steps">
          {(['pick', 'redact', 'arrange', 'details'] as ComposerStep[])
            .filter((s) => items.length > 0 || s === 'pick' || s === 'details')
            .map((s) => (
              <li
                key={s}
                aria-current={s === step ? 'step' : undefined}
                className={cn('h-1 flex-1 rounded-full', s === step ? 'bg-highlight' : 'bg-border')}
              >
                <span className="sr-only">{STEP_TITLES[s]}</span>
              </li>
            ))}
        </ol>

        <div className="min-h-0 flex-1 overflow-y-auto pb-6">
          {step === 'pick' && (
            <div>
              <p className="text-fg-muted">Up to {MAX_IMAGES} photos, or skip to write a text post.</p>
              <input
                ref={fileInput}
                type="file"
                accept="image/*"
                multiple
                className="sr-only"
                id="composer-files"
                onChange={(event) => void pick(event.target.files)}
              />
              <label
                htmlFor="composer-files"
                className="mt-6 flex min-h-40 cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border-strong text-fg-muted hover:border-highlight hover:text-fg"
              >
                <ImagePlus aria-hidden="true" className="size-8 text-highlight" />
                {busy ? 'Opening photos' : 'Choose photos'}
              </label>
              {items.length > 0 && (
                <p className="mt-4 text-sm text-fg">
                  {items.length} photo{items.length === 1 ? '' : 's'} chosen. Next, cover anything that could identify someone.
                </p>
              )}
            </div>
          )}

          {step === 'redact' && item && (
            <div>
              <p className="mb-4 text-sm text-fg-subtle" aria-live="polite">
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
                  <Button variant="ghost" disabled={current === 0} onClick={() => setCurrent((i) => i - 1)}>
                    Previous photo
                  </Button>
                  <Button variant="ghost" disabled={current === items.length - 1} onClick={() => setCurrent((i) => i + 1)}>
                    Next photo
                  </Button>
                </div>
              )}
            </div>
          )}

          {step === 'arrange' && (
            <ul className="flex flex-col gap-4" aria-label="Photos in this post">
              {items.map((entry, index) => (
                <li key={entry.key} className="flex gap-4 rounded-xl border border-border p-3">
                  {entry.preview && (
                    <img src={entry.preview} alt="" className="size-24 shrink-0 rounded-lg object-cover" draggable={false} />
                  )}
                  <div className="flex-1">
                    <FormField label={`Describe photo ${index + 1}`} hint="Helps people using screen readers." optionalLabel="Encouraged">
                      {(field) => (
                        <Input
                          {...field}
                          maxLength={200}
                          value={entry.alt}
                          onChange={(e) => setItems((list) => list.map((x, i) => (i === index ? { ...x, alt: e.target.value } : x)))}
                        />
                      )}
                    </FormField>
                    <div className="mt-2 flex gap-1">
                      <button type="button" className="inline-flex size-11 items-center justify-center rounded-full text-fg-muted hover:text-fg disabled:opacity-30" disabled={index === 0} onClick={() => move(index, -1)}>
                        <ArrowUp aria-hidden="true" className="size-4" />
                        <span className="sr-only">Move photo {index + 1} earlier</span>
                      </button>
                      <button type="button" className="inline-flex size-11 items-center justify-center rounded-full text-fg-muted hover:text-fg disabled:opacity-30" disabled={index === items.length - 1} onClick={() => move(index, 1)}>
                        <ArrowDown aria-hidden="true" className="size-4" />
                        <span className="sr-only">Move photo {index + 1} later</span>
                      </button>
                      <button type="button" className="inline-flex size-11 items-center justify-center rounded-full text-fg-muted hover:text-danger" onClick={() => setItems((list) => list.filter((_, i) => i !== index))}>
                        <Trash2 aria-hidden="true" className="size-4" />
                        <span className="sr-only">Remove photo {index + 1}</span>
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {step === 'details' && (
            <div className="flex flex-col gap-6">
              <FormField label="Caption" optionalLabel={items.length ? 'Optional' : ''} required={items.length === 0}>
                {(field) => (
                  <Textarea {...field} rows={5} maxLength={CAPTION_LIMIT} value={caption} onChange={(e) => setCaption(e.target.value)} />
                )}
              </FormField>
              <p className="-mt-4 text-right text-xs text-fg-subtle">
                {caption.length} / {CAPTION_LIMIT}
              </p>
              <Toggle label="Mark as sensitive" hint="Photos stay blurred until someone taps View." checked={sensitive} onChange={setSensitive} />
              <Toggle label="Allow comments" checked={comments} onChange={setComments} />
              {items.length > 0 && (
                <div className="flex gap-3 rounded-xl border border-highlight/40 bg-primary-deep/40 p-4">
                  <input
                    id={attestId}
                    type="checkbox"
                    checked={attested}
                    onChange={(event) => {
                      setAttested(event.target.checked)
                      setError('')
                    }}
                    className="mt-1 size-5 shrink-0 accent-[var(--color-primary)]"
                  />
                  <label htmlFor={attestId} className="text-sm leading-relaxed text-fg">
                    <ShieldCheck aria-hidden="true" className="mr-1 inline size-4 text-highlight" />
                    Everyone identifiable in these photos agreed to them being posted here.
                  </label>
                </div>
              )}
            </div>
          )}

          {error && (
            <p role="alert" className="mt-4 text-sm text-danger">
              {error}
            </p>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
          {step === 'pick' ? (
            <span />
          ) : (
            <Button
              variant="ghost"
              onClick={() => setStep(step === 'details' ? (items.length ? 'arrange' : 'pick') : step === 'arrange' ? 'redact' : 'pick')}
            >
              <ArrowLeft aria-hidden="true" className="size-4" />
              Back
            </Button>
          )}
          {step === 'pick' && (
            <Button onClick={() => setStep(items.length ? 'redact' : 'details')} disabled={busy}>
              {items.length ? 'Next' : 'Write a text post'}
            </Button>
          )}
          {step === 'redact' && (
            <Button onClick={() => void renderAll()} disabled={busy} aria-busy={busy}>
              {busy ? 'Preparing' : 'Next'}
            </Button>
          )}
          {step === 'arrange' && (
            <Button onClick={() => setStep(items.length ? 'details' : 'pick')}>Next</Button>
          )}
          {step === 'details' && (
            <Button onClick={() => void submit()} disabled={busy || (items.length > 0 && !attested)} aria-busy={busy}>
              {busy ? 'Posting' : 'Post'}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  )
}
