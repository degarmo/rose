import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { members, type FeedPost } from '@/lib/membersApi'
import { useToast } from '../../ui'
import { ConfirmDialog } from '../ConfirmDialog'
import { EditPostDialog } from '../EditPostDialog'
import { ReportDialog } from '../ReportDialog'
import { useMembers } from '../membersContext'
import { ActionSheet, type SheetAction } from './ActionSheet'

/** The freshest copy of a member post: the session's latest change wins over the list's copy. */
export function useLatestPost(post: FeedPost): FeedPost | null {
  const { postUpdates } = useMembers()
  return postUpdates.has(post.id) ? (postUpdates.get(post.id) ?? null) : post
}

/** Like, save and the post-option dialogs for one member post. Shared by the card and the detail view. */
export function usePostActions(post: FeedPost) {
  const { updatePost, patchPost } = useMembers()
  const toast = useToast()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [dialog, setDialog] = useState<'sheet' | 'report' | 'edit' | 'delete' | 'block' | null>(null)
  const [busy, setBusy] = useState(false)

  async function toggleLike() {
    const liking = !post.liked_by_me
    const before = { liked_by_me: post.liked_by_me, like_count: post.like_count }
    patchPost(post, (current) => ({
      ...current,
      liked_by_me: liking,
      like_count: current.like_count === null ? null : current.like_count + (liking ? 1 : -1),
    }))
    try {
      const fresh = await (liking ? members.like(post.id) : members.unlike(post.id))
      patchPost(post, (current) => ({ ...current, liked_by_me: fresh.liked_by_me, like_count: fresh.like_count }))
    } catch {
      patchPost(post, (current) => ({ ...current, ...before }))
      toast.show({ tone: 'error', title: 'That did not work', message: 'Please try again.' })
    }
  }

  /** Double-tap only ever likes; it never takes a like away. */
  function likeOnce() {
    if (!post.liked_by_me) void toggleLike()
  }

  async function toggleSave() {
    const saving = !post.saved_by_me
    patchPost(post, (current) => ({ ...current, saved_by_me: saving }))
    try {
      await (saving ? members.save(post.id) : members.unsave(post.id))
    } catch {
      patchPost(post, (current) => ({ ...current, saved_by_me: !saving }))
      toast.show({ tone: 'error', title: 'That did not work', message: 'Please try again.' })
    }
  }

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true)
    try {
      await action()
      setDialog(null)
      toast.show({ tone: 'success', title: success })
      updatePost(post.id, null)
    } catch {
      toast.show({ tone: 'error', title: 'That did not work', message: 'Please try again.' })
    } finally {
      setBusy(false)
    }
  }

  const handle = post.author.handle
  const postPath = `/members/p/${post.id}`
  // Design: "No Share, no Send, no Copy link. Report goes to hosts, not to the author."
  const goToPost: SheetAction[] = pathname === postPath ? [] : [{ label: 'Go to post', onSelect: () => navigate(postPath) }]
  const actions: SheetAction[] = post.is_own
    ? [{ label: 'Delete', onSelect: () => setDialog('delete'), danger: true }, { label: 'Edit', onSelect: () => setDialog('edit') }, ...goToPost]
    : [
        { label: 'Report to hosts', onSelect: () => setDialog('report'), danger: true },
        { label: 'Hide this post', onSelect: () => void run(() => members.hide(post.id), 'Hidden from your feed') },
        { label: `Mute ${handle}`, onSelect: () => void run(() => members.relate(handle, 'mute'), `${handle} is muted`) },
        { label: `Block ${handle}`, onSelect: () => setDialog('block') },
        { label: post.saved_by_me ? 'Remove from saved' : 'Save', onSelect: () => void toggleSave() },
        ...goToPost,
      ]

  const dialogs = (
    <>
      <ActionSheet open={dialog === 'sheet'} onClose={() => setDialog((d) => (d === 'sheet' ? null : d))} actions={actions} label="Post options" />
      <ReportDialog open={dialog === 'report'} onClose={() => setDialog(null)} targetType="post" targetId={post.id} />
      <EditPostDialog
        open={dialog === 'edit'}
        post={post}
        onClose={() => setDialog(null)}
        onSaved={(next) => {
          patchPost(post, (current) => ({ ...next, recent_comments: current.recent_comments, saved_by_me: current.saved_by_me }))
          setDialog(null)
        }}
      />
      <ConfirmDialog
        open={dialog === 'delete'}
        title="Delete this post?"
        confirmLabel="Delete for good"
        busy={busy}
        onClose={() => setDialog(null)}
        onConfirm={() => void run(() => members.deletePost(post.id), 'Post deleted')}
      >
        <p>The post, its photos and its comments are deleted permanently.</p>
      </ConfirmDialog>
      <ConfirmDialog
        open={dialog === 'block'}
        title={`Block ${handle}?`}
        confirmLabel="Block"
        busy={busy}
        onClose={() => setDialog(null)}
        onConfirm={() => void run(() => members.relate(handle, 'block'), `${handle} is blocked`)}
      >
        <p>You will not see each other's posts, comments or profiles. They are not told.</p>
        <p>You can unblock them later from Settings.</p>
      </ConfirmDialog>
    </>
  )

  return { toggleLike, likeOnce, toggleSave, openSheet: () => setDialog('sheet'), dialogs }
}
