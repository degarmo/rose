import { Settings } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { Avatar } from '@/components/members/Avatar'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { useMembers } from '@/components/members/membersContext'
import { OverflowMenu } from '@/components/members/OverflowMenu'
import { ProfileSettings } from '@/components/members/ProfileSettings'
import { ReportDialog } from '@/components/members/ReportDialog'
import { Button, ImageFrame, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { members, type FeedPost, type MemberProfile } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { useCursorList } from '@/lib/useCursorList'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '../NotFoundPage'

const monthFormatter = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' })

function joinedLabel(month: string) {
  const [year, value] = month.split('-').map(Number)
  return monthFormatter.format(new Date(Date.UTC(year, value - 1, 1)))
}

function PostGrid({ handle, version }: { handle: string; version: number }) {
  const { base, status, loadMore, retry, bindSentinel } = useCursorList(
    (cursor) => members.memberPosts(handle, cursor),
    `${handle}|${version}`,
  )
  return (
    <div>
      <ul className="grid grid-cols-3 gap-0.5 sm:gap-1">
        {base.map((post: FeedPost) => (
          <li key={post.id}>
            <Link to={`/members/p/${post.id}`} className="relative block aspect-square overflow-hidden bg-surface-raised" aria-label={`Open post from ${post.posted.at ?? post.posted.month}`}>
              {post.images[0] ? (
                <ImageFrame remote={post.blur ? null : post.images[0]} alt="" ratio="1/1" placeholder="velvet" reveal={false} protect className={post.blur ? 'blur-xl' : undefined} />
              ) : (
                <span className="absolute inset-0 line-clamp-5 p-2 text-xs leading-snug text-fg-muted" dangerouslySetInnerHTML={{ __html: post.caption_html }} />
              )}
            </Link>
          </li>
        ))}
      </ul>
      <div ref={bindSentinel} className="mt-6 flex justify-center" aria-live="polite">
        {status === 'loading' && <LoadingState label="Loading posts" />}
        {status === 'error' && <ErrorState title="Posts did not load" onRetry={retry} />}
        {status === 'idle' && <Button variant="ghost" onClick={() => void loadMore()}>Load more</Button>}
        {status === 'done' && base.length === 0 && <p className="text-sm text-fg-subtle">No posts yet.</p>}
      </div>
    </div>
  )
}

export function MemberProfilePage() {
  const { handle = '' } = useParams()
  useDocumentMeta({ title: handle, noindex: true })
  const { me, postsVersion } = useMembers()
  const toast = useToast()
  const navigate = useNavigate()
  const [version, setVersion] = useState(0)
  const state = useAsync(() => members.profile(handle), `${handle}|${version}|${me.avatar}|${me.bio}`)
  const [dialog, setDialog] = useState<'settings' | 'report' | 'block' | null>(null)

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return <NotFoundPage />
  if (state.status === 'loading') return <LoadingState label="Loading profile" />
  if (state.status === 'error') return <ErrorState title="This profile did not load" onRetry={state.retry} />
  const profile: MemberProfile = state.data

  async function relate(kind: 'follow' | 'mute', on: boolean) {
    try {
      await (on ? members.relate(profile.handle, kind) : members.unrelate(profile.handle, kind))
      setVersion((n) => n + 1)
    } catch {
      toast.show({ tone: 'error', title: 'That did not work' })
    }
  }

  return (
    <div>
      <header className="flex items-start gap-4">
        <Avatar member={profile} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="break-all text-2xl leading-tight text-fg sm:text-3xl">{profile.handle}</h1>
          <p className="mt-1 text-sm text-fg-subtle">Joined {joinedLabel(profile.joined)}</p>
          {profile.bio && <p className="mt-3 leading-relaxed text-fg-muted">{profile.bio}</p>}
          <div className="mt-4 flex flex-wrap gap-2">
            {profile.is_self ? (
              <Button variant="ghost" onClick={() => setDialog('settings')}>
                <Settings aria-hidden="true" className="size-4" />
                Edit profile
              </Button>
            ) : (
              profile.relationship && (
                <>
                  <Button variant={profile.relationship.following ? 'ghost' : 'primary'} onClick={() => void relate('follow', !profile.relationship?.following)}>
                    {profile.relationship.following ? 'Following' : 'Follow'}
                  </Button>
                  <Button variant="ghost" onClick={() => void relate('mute', !profile.relationship?.muted)}>
                    {profile.relationship.muted ? 'Unmute' : 'Mute'}
                  </Button>
                </>
              )
            )}
          </div>
          {!profile.is_self && <p className="mt-2 text-xs text-fg-subtle">Follows are private. Nobody sees who follows whom.</p>}
        </div>
        {!profile.is_self && (
          <OverflowMenu
            label="Profile options"
            items={[
              { label: 'Report profile', onSelect: () => setDialog('report') },
              { label: `Block ${profile.handle}`, onSelect: () => setDialog('block'), danger: true },
            ]}
          />
        )}
      </header>
      <div className="mt-8">
        <PostGrid handle={profile.handle} version={postsVersion} />
      </div>
      {profile.is_self && <ProfileSettings open={dialog === 'settings'} onClose={() => setDialog(null)} />}
      <ReportDialog open={dialog === 'report'} onClose={() => setDialog(null)} targetType="profile" targetId={profile.handle} />
      <ConfirmDialog
        open={dialog === 'block'}
        title={`Block ${profile.handle}?`}
        confirmLabel="Block"
        onClose={() => setDialog(null)}
        onConfirm={async () => {
          try {
            await members.relate(profile.handle, 'block')
            toast.show({ tone: 'success', title: `${profile.handle} is blocked` })
            navigate('/members/feed', { replace: true })
          } catch {
            toast.show({ tone: 'error', title: 'That did not work' })
          }
        }}
      >
        <p>You will not see each other's posts, comments or profiles. They are not told.</p>
      </ConfirmDialog>
    </div>
  )
}
