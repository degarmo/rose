import { Bookmark, Ellipsis, Grid3x3, Settings } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { ActionSheet } from '@/components/members/app/ActionSheet'
import { PostGrid } from '@/components/members/app/PostGrid'
import { profilePath } from '@/components/members/app/postUtils'
import { IgButton } from '@/components/members/app/primitives'
import { igButtonClasses } from '@/components/members/app/ui'
import { Avatar } from '@/components/members/Avatar'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { useMembers } from '@/components/members/membersContext'
import { EditProfileDialog } from '@/components/members/ProfileSettings'
import { ReportDialog } from '@/components/members/ReportDialog'
import { useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { members, type MemberProfile } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '../NotFoundPage'

const monthFormatter = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' })

function joinedLabel(month: string) {
  const [year, value] = month.split('-').map(Number)
  return monthFormatter.format(new Date(Date.UTC(year, value - 1, 1)))
}

function Tabs({ profile, saved }: { profile: MemberProfile; saved: boolean }) {
  const base = profilePath(profile.handle)
  const tab = (to: string, label: string, Icon: typeof Grid3x3, active: boolean) => (
    <Link
      to={to}
      replace
      aria-current={active ? 'page' : undefined}
      className={cn(
        '-mt-px inline-flex h-[52px] items-center gap-1.5 border-t text-xs font-semibold uppercase tracking-[0.1em]',
        active ? 'border-fg text-fg' : 'border-transparent text-fg-muted hover:text-fg',
      )}
    >
      <Icon aria-hidden="true" className="size-3" strokeWidth={2} />
      {label}
    </Link>
  )
  return (
    <nav aria-label="Profile sections" className="flex justify-center gap-14 border-t border-border">
      {tab(base, 'Posts', Grid3x3, !saved)}
      {profile.is_self && tab(`${base}/saved`, 'Saved', Bookmark, saved)}
    </nav>
  )
}

/**
 * A member's profile: picture, name, the number of posts (never followers or
 * following), bio, then their posts, or your own saved posts on your own profile.
 */
export function MemberProfilePage() {
  const { handle = '' } = useParams()
  const { pathname } = useLocation()
  const saved = pathname.endsWith('/saved')
  useDocumentMeta({ title: handle, noindex: true })
  const { me, postsVersion } = useMembers()
  const toast = useToast()
  const navigate = useNavigate()
  const [version, setVersion] = useState(0)
  const state = useAsync(() => members.profile(handle), `${handle}|${version}|${me.avatar}|${me.bio}`)
  const [dialog, setDialog] = useState<'edit' | 'sheet' | 'report' | 'block' | null>(null)

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return <NotFoundPage />
  if (state.status === 'loading') return <LoadingState label="Loading profile" />
  if (state.status === 'error') return <ErrorState title="This profile did not load" onRetry={state.retry} />
  const profile = state.data
  // Saved posts are private: the tab exists only on your own profile.
  if (saved && !profile.is_self) return <NotFoundPage />

  async function relate(kind: 'follow' | 'mute', on: boolean) {
    try {
      await (on ? members.relate(profile.handle, kind) : members.unrelate(profile.handle, kind))
      setVersion((n) => n + 1)
    } catch {
      toast.show({ tone: 'error', title: 'That did not work' })
    }
  }

  const buttons = profile.is_self ? (
    <>
      <IgButton variant="secondary" onClick={() => setDialog('edit')}>
        Edit profile
      </IgButton>
      <Link to="/members/settings" className={igButtonClasses('secondary')}>
        <Settings aria-hidden="true" className="size-4" />
        Settings
      </Link>
    </>
  ) : (
    profile.relationship && (
      <>
        <IgButton
          variant={profile.relationship.following ? 'secondary' : 'primary'}
          aria-pressed={profile.relationship.following}
          onClick={() => void relate('follow', !profile.relationship?.following)}
        >
          {profile.relationship.following ? 'Following' : 'Follow'}
        </IgButton>
        <IgButton variant="secondary" aria-pressed={profile.relationship.muted} onClick={() => void relate('mute', !profile.relationship?.muted)}>
          {profile.relationship.muted ? 'Unmute' : 'Mute'}
        </IgButton>
        <button type="button" onClick={() => setDialog('sheet')} className="inline-flex size-8 items-center justify-center rounded-lg text-fg hover:bg-hover">
          <Ellipsis aria-hidden="true" className="size-6" strokeWidth={1.75} />
          <span className="sr-only">Profile options</span>
        </button>
      </>
    )
  )

  return (
    <div className="mx-auto w-full max-w-[935px] md:px-5 md:pt-8">
      {/*
        Phones: avatar and post count side by side, then the name, bio and join date, then
        the buttons filling the width. From 768px: the avatar on the left, and the name with
        its buttons, the count and the bio stacked beside it.
      */}
      <header
        className={cn(
          'grid grid-cols-[77px_1fr] px-4 pb-6 pt-4 [grid-template-areas:"avatar_stats"_"name_name"_"about_about"_"actions_actions"]',
          'md:grid-cols-[290px_auto_1fr] md:px-0 md:pb-11 md:pt-0 md:[grid-template-areas:"avatar_name_actions"_"avatar_stats_stats"_"avatar_about_about"]',
        )}
      >
        <div className="[grid-area:avatar] md:row-span-3 md:justify-self-center">
          <Avatar member={profile} size="profile" />
        </div>
        <h1 className="mt-3 break-all text-sm font-semibold text-fg [grid-area:name] md:mt-0 md:self-center md:text-xl md:font-normal">
          {profile.handle}
        </h1>
        <p className="flex flex-col items-center self-center justify-self-center text-fg [grid-area:stats] md:mt-5 md:flex-row md:gap-1 md:self-start md:justify-self-start md:text-base">
          <span className="text-base font-semibold">{profile.post_count}</span>{' '}
          <span>{profile.post_count === 1 ? 'post' : 'posts'}</span>
        </p>
        <section aria-label="About" className="min-w-0 [grid-area:about] md:mt-3">
          {profile.bio && <p className="whitespace-pre-line break-words text-fg">{profile.bio}</p>}
          <p className="mt-1 text-fg-muted">Joined {joinedLabel(profile.joined)}</p>
          {!profile.is_self && <p className="mt-1 text-xs text-fg-muted">Follows are private. Nobody sees who follows whom.</p>}
        </section>
        <div
          className={cn(
            'mt-4 grid gap-2 [grid-area:actions] md:ml-5 md:mt-0 md:flex md:items-center md:self-center',
            profile.is_self ? 'grid-cols-2' : 'grid-cols-[1fr_1fr_auto]',
          )}
        >
          {buttons}
        </div>
      </header>

      <Tabs profile={profile} saved={saved} />
      {saved ? (
        <>
          <p className="px-4 pb-3 pt-1 text-xs text-fg-muted md:px-0">Only you can see what you have saved.</p>
          <PostGrid loader={(cursor) => members.saved(cursor)} listKey={`saved|${postsVersion}`} empty={<p className="py-10 text-center text-fg-muted">Save posts with the bookmark to find them here.</p>} />
        </>
      ) : (
        <PostGrid
          loader={(cursor) => members.memberPosts(profile.handle, cursor)}
          listKey={`${profile.handle}|${postsVersion}`}
          empty={<p className="py-10 text-center text-fg-muted">No posts yet.</p>}
        />
      )}

      {profile.is_self && <EditProfileDialog open={dialog === 'edit'} onClose={() => setDialog(null)} />}
      <ActionSheet
        open={dialog === 'sheet'}
        onClose={() => setDialog((d) => (d === 'sheet' ? null : d))}
        label="Profile options"
        actions={[
          { label: 'Report profile', onSelect: () => setDialog('report'), danger: true },
          { label: `Block ${profile.handle}`, onSelect: () => setDialog('block'), danger: true },
        ]}
      />
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
