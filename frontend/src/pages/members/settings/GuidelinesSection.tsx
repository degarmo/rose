import { BadgeCheck, Flag, ScrollText } from 'lucide-react'
import { Link } from 'react-router'
import { GuidelinesText } from '@/components/members/GuidelinesText'
import { appButtonClasses } from '@/components/members/app/ui'
import { Card, FeedOnlyNote, LinkRow, LoadError, Skeleton, StatusChip } from '@/components/members/settings/ui'
import { useFeedAccount } from '@/components/members/settings/useFeedAccount'
import { formatDay } from '@/lib/format'

/** The current version, and the date you accepted it. */
function CurrentGuidelines() {
  const feed = useFeedAccount()
  if (!feed.controls) {
    return (
      <FeedOnlyNote icon={ScrollText} title="Community guidelines">
        You read and accept the community guidelines when you join the member feed. At events, the house rules apply.
      </FeedOnlyNote>
    )
  }
  if (feed.state.status === 'error') return <LoadError title="The guidelines did not load" onRetry={feed.state.retry} />
  const account = feed.account
  if (!account) return <Skeleton lines={3} />
  const guidelines = account.guidelines
  if (!guidelines) return <p className="text-fg-muted">The guidelines are being written. They will show here.</p>
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-fg">{guidelines.title}</p>
          <p className="text-meta text-fg-muted">
            Version {guidelines.version} · published {formatDay(guidelines.published_at)}
          </p>
        </div>
        {account.accepted_current_guidelines ? <StatusChip tone="ok">Accepted</StatusChip> : <StatusChip tone="wait">Not accepted yet</StatusChip>}
      </div>
      {account.accepted_current_guidelines && account.guidelines_accepted_at ? (
        <p className="flex items-center gap-2 text-fg">
          <BadgeCheck aria-hidden="true" className="size-5 text-link" />
          You accepted this version on {formatDay(account.guidelines_accepted_at)}.
        </p>
      ) : (
        account.participating && (
          <Link to="/members/join-feed?guidelines=1" className={appButtonClasses('primary', 'self-start')}>
            Read and accept
          </Link>
        )
      )}
      <details className="group rounded-app border border-border">
        <summary className="flex min-h-11 cursor-pointer items-center px-3 font-semibold text-fg">Read the guidelines</summary>
        <div className="border-t border-border p-4">
          <GuidelinesText body={guidelines.body} />
        </div>
      </details>
    </div>
  )
}

/** Settings · Community guidelines: the current version, the date you accepted it, and Report a concern. */
export function GuidelinesSection() {
  return (
    <div className="flex flex-col gap-4">
      <Card title="The guidelines">
        <CurrentGuidelines />
      </Card>
      <Card>
        <ul>
          <LinkRow icon={Flag} label="Report a concern" sub="Something that happened at an event or the club" to="/members/report" />
        </ul>
      </Card>
    </div>
  )
}
