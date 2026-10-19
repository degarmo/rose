import { useState } from 'react'
import { members, type FeedPost } from '@/lib/membersApi'
import { Button, FormField, Modal, Textarea, useToast } from '../ui'
import { Toggle } from '@/components/ui/Toggle'

const CAPTION_LIMIT = 2200

/** Caption and toggles only. Photos cannot change after posting. */
export function EditPostDialog({ open, post, onClose, onSaved }: { open: boolean; post: FeedPost; onClose: () => void; onSaved: (post: FeedPost) => void }) {
  const toast = useToast()
  const [caption, setCaption] = useState(post.caption ?? '')
  const [sensitive, setSensitive] = useState(post.is_sensitive)
  const [comments, setComments] = useState(post.comments_enabled)
  const [busy, setBusy] = useState(false)

  async function save() {
    setBusy(true)
    try {
      onSaved(await members.editPost(post.id, { caption, is_sensitive: sensitive, comments_enabled: comments }))
      toast.show({ tone: 'success', title: 'Post updated' })
    } catch (error) {
      toast.show({ tone: 'error', title: 'Your changes were not saved', message: error instanceof Error ? error.message : undefined })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Edit post"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} disabled={busy} aria-busy={busy}>
            {busy ? 'Saving' : 'Save'}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-5">
        <FormField label="Caption" optionalLabel="">
          {(field) => <Textarea {...field} rows={5} maxLength={CAPTION_LIMIT} value={caption} onChange={(e) => setCaption(e.target.value)} />}
        </FormField>
        <Toggle label="Sensitive" hint="Blurred until a member taps View" checked={sensitive} onChange={setSensitive} />
        <Toggle label="Comments on" checked={comments} onChange={setComments} />
        <p className="text-sm text-fg-muted">Photos cannot be changed after posting. Delete the post and share it again instead.</p>
      </div>
    </Modal>
  )
}
