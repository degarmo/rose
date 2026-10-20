import { Link } from 'react-router'
import { api } from '@/lib/api'
import { dateParts } from '@/lib/format'
import { postedShort } from '@/lib/membersApi'
import { leaveNow, quickExitUrl } from '@/lib/quickExit'
import { useAsync } from '@/lib/useAsync'
import { Avatar } from '../Avatar'
import { useMembers } from '../membersContext'
import { eventAction, timeOnly } from './events'
import { profilePath } from './postUtils'

/** Captions may hold links; inside a link to the post only their text is shown. */
function plainText(html: string) {
  return new DOMParser().parseFromString(html.replace(/<br>/g, ' '), 'text/html').body.textContent ?? ''
}

/** The copyright year, read once when the module loads. */
const YEAR = new Date().getFullYear()

/** The date tile (design: 44px, 8px corners, the rose tint, day name over the day). */
export function DateTile({ iso }: { iso: string }) {
  const { weekday, day } = dateParts(iso)
  return (
    <span aria-hidden="true" className="flex size-11 shrink-0 flex-col items-center justify-center rounded-app bg-tint leading-none text-tint-fg">
      <span className="text-[0.625rem] font-semibold uppercase">{weekday}</span>
      <span className="text-base font-semibold">{day}</span>
    </span>
  )
}

/**
 * Beside the home feed from 1160px (design: "Right rail 320px"): your own mini profile,
 * the next three events and the two latest journal posts (both open the website pages),
 * and small footer links. Deliberately no "suggested for you": suggesting members would
 * reveal who is here.
 */
export function RightRail() {
  const { me } = useMembers()
  const events = useAsync(() => api.events('', 1, 3), 'rail-events')
  const journal = useAsync(() => api.journal(), 'rail-journal')

  return (
    <aside aria-label="Coming up and from the club" className="hidden w-[320px] shrink-0 flex-col gap-5 pt-2 rail:flex">
      <div className="flex items-center gap-3">
        <Link to={profilePath(me.handle)} className="flex min-w-0 flex-1 items-center gap-3">
          <Avatar member={me} size="md" />
          <span className="min-w-0">
            <span className="block truncate font-semibold text-fg">{me.handle}</span>
            <span className="block text-fg-muted">Your profile</span>
          </span>
        </Link>
        <Link to="/members/settings" className="text-meta font-semibold text-link hover:text-primary-hover">
          Edit
        </Link>
      </div>

      <section aria-labelledby="rail-events" className="flex flex-col gap-3">
        <h2 id="rail-events" className="text-sm font-semibold text-fg-muted">
          Coming up
        </h2>
        <ul className="flex flex-col gap-3">
          {events.status === 'success' &&
            events.data.results.map((event) => {
              const { status, action } = eventAction(event)
              return (
                <li key={event.id} className="relative flex items-center gap-3">
                  <DateTile iso={event.starts_at} />
                  <span className="min-w-0 flex-1">
                    <Link to={`/events/${event.slug}`} className="block truncate font-semibold text-fg after:absolute after:inset-0">
                      {event.title}
                    </Link>
                    <span className="block text-meta text-fg-muted">
                      {timeOnly.format(new Date(event.starts_at))} · {status}
                    </span>
                  </span>
                  <span aria-hidden="true" className="text-meta font-semibold text-link">
                    {action}
                  </span>
                </li>
              )
            })}
          {events.status === 'success' && events.data.count === 0 && <li className="text-fg-muted">Nothing on the calendar yet.</li>}
        </ul>
      </section>

      <section aria-labelledby="rail-journal" className="flex flex-col gap-3">
        <h2 id="rail-journal" className="text-sm font-semibold text-fg-muted">
          From the club
        </h2>
        <ul className="flex flex-col gap-3">
          {journal.status === 'success' &&
            journal.data.posts.slice(0, 2).map((post) => (
              <li key={post.slug}>
                <Link to={`/journal/${post.slug}`} className="flex items-center gap-3">
                  <span className="wash-rose size-11 shrink-0 overflow-hidden rounded-app">
                    {post.images[0] && <img src={post.images[0].url} alt="" className="size-full object-cover" loading="lazy" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold text-fg">{plainText(post.caption_html)}</span>
                    <span className="block text-meta text-fg-muted">From the Journal · {postedShort({ recent: true, at: post.published_at, month: null })}</span>
                  </span>
                </Link>
              </li>
            ))}
        </ul>
      </section>

      <nav aria-label="Website links">
        <ul className="flex flex-wrap gap-x-2 text-[0.6875rem] leading-4 text-fg-muted">
          <li>
            <Link to="/about" className="hover:underline">
              About
            </Link>
          </li>
          <li>
            <Link to="/privacy" className="hover:underline">
              Privacy
            </Link>
          </li>
          <li>
            <Link to="/contact" className="hover:underline">
              Contact
            </Link>
          </li>
          <li>
            <a
              href={quickExitUrl()}
              onClick={(event) => {
                event.preventDefault()
                leaveNow()
              }}
              rel="noreferrer"
              className="hover:underline"
            >
              Leave
            </a>
          </li>
        </ul>
      </nav>
      <p className="text-[0.6875rem] text-fg-muted">© {YEAR} Rose</p>
    </aside>
  )
}
