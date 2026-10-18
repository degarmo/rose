import { ArrowLeft } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { Avatar } from '@/components/members/Avatar'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { OverflowMenu } from '@/components/members/OverflowMenu'
import { PostCard } from '@/components/members/PostCard'
import { ReportDialog } from '@/components/members/ReportDialog'
import { Button, ButtonLink, FormField, Textarea, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { relativeDate } from '@/lib/format'
import { members, postedLabel, type FeedComment, type FeedPost } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '../NotFoundPage'

const COMMENT_LIMIT = 500

function Comments({ post }: { post: FeedPost }) {
  const toast = useToast()
  const [version, setVersion] = useState(0)
  const state = useAsync(() => members.comments(post.id), `${post.id}|${version}`)
  const [body, setBody] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [reporting, setReporting] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<FeedComment | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!body.trim()) return setError('Write a comment first.')
    setBusy(true)
    try {
      await members.addComment(post.id, body.trim())
      setBody('')
      setError(undefined)
      setVersion((n) => n + 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Your comment was not posted.')
    } finally {
      setBusy(false)
    }
  }

  async function remove(comment: FeedComment) {
    try {
      await members.deleteComment(comment.id)
      setDeleting(null)
      setVersion((n) => n + 1)
      toast.show({ tone: 'success', title: 'Comment deleted' })
    } catch {
      toast.show({ tone: 'error', title: 'That did not work' })
    }
  }

  return (
    <section aria-labelledby="comments" className="mt-6">
      <h2 id="comments" className="text-2xl text-fg">
        Comments
      </h2>
      {state.status === 'loading' && <LoadingState label="Loading comments" />}
      {state.status === 'error' && <ErrorState title="Comments did not load" onRetry={state.retry} />}
      {state.status === 'success' && (
        <ul className="mt-4 flex flex-col gap-4">
          {state.data.length === 0 && <li className="text-sm text-fg-subtle">No comments yet.</li>}
          {state.data.map((comment) => (
            <li key={comment.id} className="flex gap-3">
              <Avatar member={comment.author} />
              <div className="min-w-0 flex-1">
                <p className="text-sm">
                  <span className="font-medium text-fg">{comment.author.handle}</span>{' '}
                  <span className="text-fg-subtle">{postedLabel(comment.posted, relativeDate)}</span>
                </p>
                <div
                  className="mt-0.5 break-words leading-relaxed text-fg-muted [&_a]:text-accent [&_a]:underline"
                  // Sanitised on the server.
                  dangerouslySetInnerHTML={{ __html: comment.body_html }}
                />
              </div>
              <OverflowMenu
                label="Comment options"
                items={[
                  ...(comment.can_delete ? [{ label: 'Delete', onSelect: () => setDeleting(comment), danger: true }] : []),
                  { label: 'Report', onSelect: () => setReporting(comment.id) },
                ]}
              />
            </li>
          ))}
        </ul>
      )}
      {post.comments_enabled && post.state !== 'pending' && post.state !== 'processing' ? (
        <form onSubmit={submit} noValidate className="mt-6 flex flex-col gap-3" aria-label="Add a comment">
          <FormField label="Add a comment" error={error} optionalLabel="">
            {(field) => (
              <Textarea {...field} rows={2} maxLength={COMMENT_LIMIT} value={body} onChange={(e) => { setBody(e.target.value); setError(undefined) }} />
            )}
          </FormField>
          <div className="flex items-center justify-between">
            <span className="text-xs text-fg-subtle">
              {body.length} / {COMMENT_LIMIT}
            </span>
            <Button type="submit" disabled={busy} aria-busy={busy}>
              {busy ? 'Posting' : 'Comment'}
            </Button>
          </div>
        </form>
      ) : (
        <p className="mt-6 text-sm text-fg-subtle">Comments are off for this post.</p>
      )}
      <ReportDialog open={reporting !== null} onClose={() => setReporting(null)} targetType="comment" targetId={reporting ?? ''} />
      <ConfirmDialog open={deleting !== null} title="Delete this comment?" confirmLabel="Delete" onClose={() => setDeleting(null)} onConfirm={() => deleting && void remove(deleting)}>
        <p>This cannot be undone.</p>
      </ConfirmDialog>
    </section>
  )
}

export function PostPage() {
  useDocumentMeta({ title: 'Post', noindex: true })
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const state = useAsync(() => members.post(id), id)
  const [override, setOverride] = useState<FeedPost | null>(null)

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return <NotFoundPage />
  const post = override?.id === id ? override : state.status === 'success' ? state.data : null

  return (
    <div>
      <ButtonLink to="/members/feed" variant="link" className="mb-3">
        <ArrowLeft aria-hidden="true" className="size-4" />
        Feed
      </ButtonLink>
      {state.status === 'loading' && <LoadingState label="Loading post" />}
      {state.status === 'error' && <ErrorState title="This post did not load" onRetry={state.retry} />}
      {post && (
        <>
          <h1 className="sr-only">Post by {post.author.handle}</h1>
          <PostCard
            post={post}
            linkToDetail={false}
            onChange={(next) => (next ? setOverride(next) : navigate('/members/feed', { replace: true }))}
          />
          <Comments post={post} />
        </>
      )}
    </div>
  )
}
