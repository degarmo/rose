import { Bookmark, Ellipsis, Grid3x3, Settings } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { ActionSheet } from '@/components/members/app/ActionSheet'
import { PostGrid } from '@/components/members/app/PostGrid'
import { profilePath } from '@/components/members/app/postUtils'
import { PhoneBar } from '@/components/members/app/Nav'
import { AppButton } from '@/components/members/app/primitives'
import { appButtonClasses, ICON } from '@/components/members/app/ui'
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

/** Phones: icon tabs in two halves with a 1px underline. From 768px: 12px caps with a top rule. */
function Tabs({ profile, saved }: { profile: MemberProfile; saved: boolean }) {
  const base = profilePath(profile.handle)
  const tab = (to: string, label: string, Icon: typeof Grid3x3, active: boolean) => (
    <Link
      to={to}
      replace
      aria-current={active ? 'page' : undefined}
      className={cn(
        'flex h-12 flex-1 items-center justify-center gap-1.5 border-b md:-mt-px md:h-auto md:flex-none md:border-b-0 md:border-t md:py-4',
        'text-xs font-semibold uppercase tracking-[0.08em]',
        active ? 'border-fg text-fg' : 'border-transparent text-fg-muted hover:text-fg',
      )}
    >
      <Icon aria-hidden="true" size={16} strokeWidth={ICON.stroke} />
      <span className="sr-only md:not-sr-only">{label}</span>
    </Link>
  )
  return (
    <nav aria-label="Profile sections" className="flex border-t border-border md:justify-center md:gap-[60px]">
      {tab(base, 'Posts', Grid3x3, !saved)}
      {profile.is_self && tab(`${base}/saved`, 'Saved', Bookmark, saved)}
    </nav>
  )
}

/**
 * A member's profile (design: "Profile (own)" and "Profile (other member)"): picture, the
 * number of posts (never followers or following), bio, then their posts, or your own
 * saved posts on your own profile. Follow, Mute, Block and Report sit behind "more".
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

  const loadingBar = <PhoneBar back title={handle} />
  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return <NotFoundPage />
  if (state.status === 'loading') return <>{loadingBar}<LoadingState label="Loading profile" className="px-4" /></>
  if (state.status === 'error') return <>{loadingBar}<ErrorState title="This profile did not load" onRetry={state.retry} className="m-4" /></>
  const profile = state.data
  // Saved posts are private: the tab exists only on your own profile.
  if (saved && !profile.is_self) return <NotFoundPage />
  const relationship = profile.relationship

  async function relate(kind: 'follow' | 'mute', on: boolean) {
    try {
      await (on ? members.relate(profile.handle, kind) : members.unrelate(profile.handle, kind))
      setVersion((n) => n + 1)
      toast.show({
        tone: 'success',
        title: kind === 'follow' ? (on ? `You follow ${profile.handle}` : `You unfollowed ${profile.handle}`) : on ? `${profile.handle} is muted` : `${profile.handle} is unmuted`,
      })
    } catch {
      toast.show({ tone: 'error', title: 'That did not work' })
    }
  }

  const iconButton = 'inline-flex size-10 items-center justify-center text-fg'
  const more = (className: string) => (
    <button type="button" onClick={() => setDialog('sheet')} className={className}>
      <Ellipsis aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
      <span className="sr-only">Profile options</span>
    </button>
  )

  return (
    <>
      <PhoneBar
        back={!profile.is_self}
        title={<h1 className="truncate text-base font-semibold">{profile.handle}</h1>}
        actions={
          profile.is_self ? (
            <Link to="/members/settings" className={iconButton}>
              <Settings aria-hidden="true" size={ICON.size} strokeWidth={ICON.stroke} />
              <span className="sr-only">Settings</span>
            </Link>
          ) : (
            more(iconButton)
          )
        }
      />
      <div className="mx-auto w-full max-w-[975px] md:px-5 md:pt-8">
        {/*
          Phones: the avatar with the post count 28px beside it, then the bio, then two
          buttons filling the width. From 768px: a 150px avatar, then the handle with its
          buttons, the count and the bio stacked beside it.
        */}
        <header className="grid grid-cols-[77px_1fr] gap-x-7 px-4 pb-4 pt-2 [grid-template-areas:'avatar_stats'_'about_about'_'actions_actions'] md:grid-cols-[150px_1fr] md:gap-x-[60px] md:gap-y-4 md:pb-8 md:pl-12 md:pr-0 md:pt-0 md:[grid-template-areas:'avatar_name'_'avatar_stats'_'avatar_about'] md:[grid-template-rows:auto_auto_1fr]">
          <div className="[grid-area:avatar]">
            <Avatar member={profile} size="profile" />
          </div>
          <div className="hidden min-w-0 items-center gap-3 pt-1.5 [grid-area:name] md:flex">
            <h1 className="truncate text-xl font-normal text-fg">{profile.handle}</h1>
            {profile.is_self ? (
              <>
                <AppButton variant="secondary" onClick={() => setDialog('edit')}>
                  Edit profile
                </AppButton>
                <Link to="/members/settings" className={appButtonClasses('secondary', 'w-8 px-0')}>
                  <Settings aria-hidden="true" size={20} strokeWidth={ICON.stroke} />
                  <span className="sr-only">Settings</span>
                </Link>
              </>
            ) : (
              more('-ml-1 inline-flex size-8 items-center justify-center rounded-app text-fg hover:bg-surface')
            )}
          </div>
          <p className="flex flex-col items-center self-center justify-self-start text-fg [grid-area:stats] md:flex-row md:gap-1 md:self-start">
            <span className="text-base font-semibold md:text-sm">{profile.post_count}</span> <span>{profile.post_count === 1 ? 'post' : 'posts'}</span>
          </p>
          <section aria-label="About" className="mt-3 min-w-0 [grid-area:about] md:mt-0">
            <p className="font-semibold text-fg">{profile.handle}</p>
            {profile.bio && <p className="whitespace-pre-line break-words text-fg">{profile.bio}</p>}
            <p className="text-fg-muted">Joined {joinedLabel(profile.joined)}</p>
          </section>
          {profile.is_self && (
            <div className="mt-3 grid grid-cols-2 gap-2 [grid-area:actions] md:hidden">
              <AppButton variant="secondary" onClick={() => setDialog('edit')}>
                Edit profile
              </AppButton>
              <Link to="/members/settings" className={appButtonClasses('secondary')}>
                Settings
              </Link>
            </div>
          )}
        </header>

        <Tabs profile={profile} saved={saved} />
        {saved ? (
          <>
            <p className="px-4 pb-3 pt-1 text-meta text-fg-muted md:px-0">Only you can see what you have saved.</p>
            <PostGrid loader={(cursor) => members.saved(cursor)} listKey={`saved|${postsVersion}`} empty={<p className="py-10 text-center text-fg-muted">Save posts with the bookmark to find them here.</p>} />
          </>
        ) : (
          <PostGrid
            loader={(cursor) => members.memberPosts(profile.handle, cursor)}
            listKey={`${profile.handle}|${postsVersion}`}
            empty={<p className="py-10 text-center text-fg-muted">No posts yet.</p>}
          />
        )}
      </div>

      {profile.is_self && <EditProfileDialog open={dialog === 'edit'} onClose={() => setDialog(null)} />}
      {!profile.is_self && (
        <ActionSheet
          open={dialog === 'sheet'}
          onClose={() => setDialog((d) => (d === 'sheet' ? null : d))}
          label="Profile options"
          actions={[
            ...(relationship
              ? [
                  { label: relationship.following ? `Unfollow ${profile.handle}` : `Follow ${profile.handle}`, onSelect: () => void relate('follow', !relationship.following) },
                  { label: relationship.muted ? `Unmute ${profile.handle}` : `Mute ${profile.handle}`, onSelect: () => void relate('mute', !relationship.muted) },
                ]
              : []),
            { label: 'Report profile', onSelect: () => setDialog('report'), danger: true },
            { label: `Block ${profile.handle}`, onSelect: () => setDialog('block'), danger: true },
          ]}
        />
      )}
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
    </>
  )
}
