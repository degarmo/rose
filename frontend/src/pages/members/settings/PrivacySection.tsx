import { Ban, CalendarDays, Download, EyeOff, Pause, Search, Undo2, VolumeX } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { useAuth } from '@/components/layout/authContext'
import { ConfirmDialog } from '@/components/members/ConfirmDialog'
import { appButtonClasses } from '@/components/members/app/ui'
import { useOptionalMembers } from '@/components/members/membersContext'
import { RelationList } from '@/components/members/ProfileSettings'
import { ButtonRow, Card, FeedOnlyNote, LoadError, RowIcon, RowText, Skeleton, SwitchRow } from '@/components/members/settings/ui'
import { useFeedAccount } from '@/components/members/settings/useFeedAccount'
import { usePreferences } from '@/components/members/settings/usePreferences'
import { useToast } from '@/components/ui'
import { api, type DataExportState } from '@/lib/api'
import { formatEventDate } from '@/lib/format'
import { feedAccount, members as membersApi } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'

/** Inside the feed: who can find you, the blur, blocks and mutes, and stepping away. */
function FeedPrivacy() {
  const members = useOptionalMembers()
  const toast = useToast()
  const feed = useFeedAccount()
  const [saving, setSaving] = useState(false)
  const [stepAway, setStepAway] = useState(false)

  if (!members) {
    const account = feed.account
    if (feed.controls && feed.state.status === 'loading') return <Skeleton lines={3} />
    if (account?.banned) {
      return (
        <p className="rounded-app bg-surface p-4 text-fg">
          Your access to the member feed has been withdrawn. You can still get a copy of your data or erase what you shared.
        </p>
      )
    }
    if (account?.suspended_until) {
      return <p className="rounded-app bg-surface p-4 text-fg">Your feed access is paused until {formatEventDate(account.suspended_until)}.</p>
    }
    if (account && !account.participating && account.can_join && account.has_content) {
      return (
        <div className="flex flex-col items-start gap-3 rounded-app border border-border p-4">
          <p className="font-semibold text-fg">You stepped away from the feed</p>
          <p className="text-sm text-fg-muted">Nothing you shared is visible. Rejoin and it all comes back.</p>
          <Link to="/members/join-feed" className={appButtonClasses('primary')}>
            <Undo2 aria-hidden="true" className="size-4" />
            Rejoin the feed
          </Link>
        </div>
      )
    }
    return (
      <FeedOnlyNote icon={EyeOff} title="Feed privacy">
        Who can find you, sensitive posts, blocks and mutes are settings for the member feed. They appear here once you join it.
      </FeedOnlyNote>
    )
  }

  const { me, setMe } = members
  async function update(changes: Parameters<typeof membersApi.updateMe>[0]) {
    setSaving(true)
    try {
      setMe(await membersApi.updateMe(changes))
    } catch {
      toast.show({ tone: 'error', title: 'Your change was not saved' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <ul>
        <SwitchRow
          icon={Search}
          label="Hide me from the member directory"
          sub="You can still post and comment"
          checked={me.hide_from_directory}
          disabled={saving}
          onChange={(value) => void update({ hide_from_directory: value })}
        />
        <SwitchRow
          icon={EyeOff}
          label="Always show sensitive posts"
          sub="Skip the blur and View step"
          checked={me.always_show_sensitive}
          disabled={saving}
          onChange={(value) => void update({ always_show_sensitive: value })}
        />
        <ButtonRow
          icon={Pause}
          label="Step away from the feed"
          sub="Opt out for a while: everything you shared hides until you rejoin"
          onClick={() => setStepAway(true)}
        />
      </ul>
      <div className="mt-2 flex min-h-14 items-center gap-4 border-t border-border px-1 pt-2">
        <RowIcon icon={Ban} />
        <RowText label="People you blocked" sub="They are not told, and you can unblock any time" />
      </div>
      <RelationList kind="block" />
      <div className="mt-2 flex min-h-14 items-center gap-4 border-t border-border px-1 pt-2">
        <RowIcon icon={VolumeX} />
        <RowText label="People you muted" sub="Their posts stay out of your feed; they are not told" />
      </div>
      <RelationList kind="mute" />
      <ConfirmDialog
        open={stepAway}
        title="Step away from the feed?"
        confirmLabel="Step away"
        busy={feed.busy}
        onClose={() => setStepAway(false)}
        onConfirm={() =>
          void feed.act(feedAccount.stepAway, 'You have stepped away').then((ok) => {
            // The refreshed session closes the feed; Settings stays open without it.
            if (ok) setStepAway(false)
          })
        }
      >
        <p>Everything you posted, commented on or liked disappears for everyone straight away, along with your picture and bio.</p>
        <p>Nothing is deleted. Rejoin any time and it all comes back.</p>
      </ConfirmDialog>
    </>
  )
}

/** Calendar files: generic by default, so a calendar never says more than it needs to. */
function CalendarDefault() {
  const auth = useAuth()
  const { preferences, save, saving } = usePreferences()
  if (!preferences) return <Skeleton lines={1} />
  return (
    <ul>
      <SwitchRow
        icon={CalendarDays}
        label="Name the event in calendar files"
        sub={preferences.calendar_details ? 'Calendar files show the event and the place' : 'Off: calendar files say only “Rose - Evening”'}
        checked={preferences.calendar_details}
        disabled={saving}
        onChange={(value) =>
          void save({ calendar_details: value }).then((ok) => {
            if (ok) void auth.refresh()
          })
        }
      />
    </ul>
  )
}

/** A zip of your data, emailed as a link that works once. */
function DataExport() {
  const toast = useToast()
  const state = useAsync(() => api.dataExport(), 'data-export')
  const [local, setLocal] = useState<DataExportState | null>(null)
  const [busy, setBusy] = useState(false)
  const current = local ?? (state.status === 'success' ? state.data : null)
  if (state.status === 'error' && !local) return <LoadError title="Your export status did not load" onRetry={state.retry} />
  if (!current) return <Skeleton lines={1} />
  const preparing = Boolean(current.export && !current.export.ready)
  const waiting = Boolean(current.export?.ready)

  async function request() {
    setBusy(true)
    try {
      setLocal(await api.requestDataExport())
      toast.show({
        tone: 'success',
        title: 'We will email you a link shortly',
      })
    } catch (error) {
      toast.show({
        tone: 'error',
        title: 'That did not work',
        message: error instanceof Error ? error.message : undefined,
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <ul>
      <ButtonRow
        icon={Download}
        label="Export my data"
        sub={
          preparing
            ? 'Your copy is being prepared. Watch your inbox.'
            : waiting
              ? 'Your link is in your inbox. Ask again for a new one.'
              : 'Your account, RSVPs, membership and anything you shared, as a zip. The emailed link works once, for 24 hours.'
        }
        disabled={busy || preparing}
        onClick={() => void request()}
      />
    </ul>
  )
}

/** Settings · Privacy: feed visibility, opting out, blocks and mutes, calendar files and your data. */
export function PrivacySection() {
  return (
    <div className="flex flex-col gap-4">
      <Card title="In the member feed">
        <FeedPrivacy />
      </Card>
      <Card title="Calendar files">
        <CalendarDefault />
      </Card>
      <Card title="Your data">
        <DataExport />
      </Card>
    </div>
  )
}
