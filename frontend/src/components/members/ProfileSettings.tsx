import { ImagePlus } from 'lucide-react'
import { useId, useState } from 'react'
import { ErrorState, LoadingState } from '@/components/content/States'
import { members, type Me } from '@/lib/membersApi'
import { exportRedacted, loadSource, NO_EDITS, type Edits, type Source } from '@/lib/redact'
import { useAsync } from '@/lib/useAsync'
import { Button, FormField, Input, Modal, Textarea, useToast } from '../ui'
import { RedactionEditor } from './RedactionEditor'
import { Toggle } from './Toggle'
import { useMembers } from './membersContext'

export const BIO_LIMIT = 160

/** Avatar picker. The hint says plainly that a non-face picture is normal here. */
export function AvatarPicker({ onSaved }: { onSaved: (me: Me) => void }) {
  const toast = useToast()
  const inputId = useId()
  const attestId = useId()
  const [source, setSource] = useState<(Source & CanvasImageSource) | null>(null)
  const [edits, setEdits] = useState<Edits>(NO_EDITS)
  const [showsFace, setShowsFace] = useState(false)
  const [attested, setAttested] = useState(false)
  const [alt, setAlt] = useState('')
  const [busy, setBusy] = useState(false)

  async function choose(files: FileList | null) {
    const file = files?.[0]
    if (!file) return
    try {
      setSource((await loadSource(file)) as unknown as Source & CanvasImageSource)
      setEdits(NO_EDITS)
    } catch {
      toast.show({ tone: 'error', title: 'That file could not be opened as a photo.' })
    }
  }

  async function save() {
    if (!source) return
    setBusy(true)
    try {
      const blob = await exportRedacted(source, edits)
      onSaved(await members.uploadAvatar(blob, alt, showsFace, attested))
      setSource(null)
      toast.show({ tone: 'success', title: 'Profile picture updated' })
    } catch (error) {
      toast.show({ tone: 'error', title: 'Your picture was not saved', message: error instanceof Error ? error.message : undefined })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <p className="text-sm text-fg-muted">
        Many members use a texture, an object or a silhouette rather than their face. That is completely normal here.
      </p>
      <input id={inputId} type="file" accept="image/*" className="sr-only" onChange={(e) => void choose(e.target.files)} />
      {!source ? (
        <label htmlFor={inputId} className="mt-3 inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border border-border-strong px-4 text-sm text-fg hover:border-highlight">
          <ImagePlus aria-hidden="true" className="size-4" />
          Choose a picture
        </label>
      ) : (
        <div className="mt-4 flex flex-col gap-4">
          <RedactionEditor source={source} edits={edits} onChange={setEdits} />
          <FormField label="Describe it" optionalLabel="Encouraged">
            {(field) => <Input {...field} maxLength={200} value={alt} onChange={(e) => setAlt(e.target.value)} />}
          </FormField>
          <Toggle label="This picture shows a face" checked={showsFace} onChange={(value) => { setShowsFace(value); setAttested(false) }} />
          {showsFace && (
            <div className="flex gap-3">
              <input id={attestId} type="checkbox" checked={attested} onChange={(e) => setAttested(e.target.checked)} className="mt-1 size-5 accent-[var(--color-primary)]" />
              <label htmlFor={attestId} className="text-sm text-fg">It is me, or everyone shown agreed to it being used here.</label>
            </div>
          )}
          <div className="flex gap-3">
            <Button onClick={() => void save()} disabled={busy || (showsFace && !attested)} aria-busy={busy}>
              {busy ? 'Saving' : 'Use this picture'}
            </Button>
            <Button variant="ghost" onClick={() => setSource(null)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function BlockedList() {
  const toast = useToast()
  const [version, setVersion] = useState(0)
  const state = useAsync(() => members.myBlocks(), `blocks|${version}`)
  if (state.status === 'loading') return <LoadingState label="Loading" className="py-2" />
  if (state.status === 'error') return <ErrorState title="Could not load your blocks" onRetry={state.retry} />
  if (state.data.blocked.length === 0) return <p className="text-sm text-fg-subtle">You have not blocked anyone.</p>
  return (
    <ul className="flex flex-col gap-2">
      {state.data.blocked.map((handle) => (
        <li key={handle} className="flex items-center justify-between gap-3 text-sm text-fg">
          {handle}
          <Button
            variant="ghost"
            onClick={async () => {
              try {
                await members.unrelate(handle, 'block')
                setVersion((n) => n + 1)
                toast.show({ tone: 'success', title: `${handle} is unblocked` })
              } catch {
                toast.show({ tone: 'error', title: 'That did not work' })
              }
            }}
          >
            Unblock
          </Button>
        </li>
      ))}
    </ul>
  )
}

export function ProfileSettings({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { me, setMe } = useMembers()
  const toast = useToast()
  const [bio, setBio] = useState(me.bio)
  const [busy, setBusy] = useState(false)

  async function update(changes: Parameters<typeof members.updateMe>[0]) {
    setBusy(true)
    try {
      setMe(await members.updateMe(changes))
      toast.show({ tone: 'success', title: 'Saved' })
    } catch {
      toast.show({ tone: 'error', title: 'Your change was not saved' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Profile settings" variant="sheet">
      <div className="mx-auto flex max-w-xl flex-col gap-8 overflow-y-auto pb-10">
        <section>
          <h3 className="font-display text-xl text-fg">Picture</h3>
          <div className="mt-3">
            <AvatarPicker onSaved={setMe} />
          </div>
          {me.avatar && (
            <Button variant="link" onClick={async () => setMe(await members.removeAvatar())}>
              Remove current picture
            </Button>
          )}
        </section>
        <section>
          <FormField label="Bio" hint="A line or two. No real names or workplaces." optionalLabel="">
            {(field) => <Textarea {...field} rows={3} maxLength={BIO_LIMIT} value={bio} onChange={(e) => setBio(e.target.value)} />}
          </FormField>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-fg-subtle">{bio.length} / {BIO_LIMIT}</span>
            <Button variant="ghost" disabled={busy || bio === me.bio} onClick={() => void update({ bio })}>
              Save bio
            </Button>
          </div>
        </section>
        <section className="flex flex-col gap-5">
          <Toggle
            label="Hide me from the member directory"
            hint="When on, people can only find you through your posts."
            checked={me.hide_from_directory}
            disabled={busy}
            onChange={(value) => void update({ hide_from_directory: value })}
          />
          <Toggle
            label="Always show sensitive posts"
            hint="Skip the blur on posts marked sensitive."
            checked={me.always_show_sensitive}
            disabled={busy}
            onChange={(value) => void update({ always_show_sensitive: value })}
          />
        </section>
        <section>
          <h3 className="font-display text-xl text-fg">Blocked</h3>
          <div className="mt-3">
            <BlockedList />
          </div>
        </section>
      </div>
    </Modal>
  )
}
