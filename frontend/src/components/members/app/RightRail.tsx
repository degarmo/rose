import { Link } from 'react-router'
import { api } from '@/lib/api'
import { formatEventDate } from '@/lib/format'
import { useAsync } from '@/lib/useAsync'
import { Avatar } from '../Avatar'
import { useMembers } from '../membersContext'
import { profilePath } from './postUtils'

/** Captions may hold links; inside a link to the post only their text is shown. */
function plainText(html: string) {
  return new DOMParser().parseFromString(html.replace(/<br>/g, ' '), 'text/html').body.textContent ?? ''
}

/**
 * Beside the home feed from 1160px: your own mini profile, the next three events and
 * the two latest journal posts (both open the website pages), and small footer links.
 * Deliberately no "suggested for you": suggesting members would reveal who is here.
 */
export function RightRail() {
  const { me } = useMembers()
  const events = useAsync(() => api.events(), 'rail-events')
  const journal = useAsync(() => api.journal(), 'rail-journal')

  return (
    <aside aria-label="Coming up and from the club" className="hidden w-[320px] shrink-0 pl-16 pt-9 rail:block">
      <Link to={profilePath(me.handle)} className="flex items-center gap-3">
        <Avatar member={me} size="md" />
        <span className="min-w-0">
          <span className="block truncate font-semibold text-fg">{me.handle}</span>
          <span className="block text-fg-muted">Your profile</span>
        </span>
      </Link>

      <section aria-labelledby="rail-events" className="mt-6">
        <div className="flex items-center justify-between">
          <h2 id="rail-events" className="font-semibold text-fg-muted">
            Coming up
          </h2>
          <Link to="/events" className="text-xs font-semibold text-fg hover:text-fg-muted">
            See all
          </Link>
        </div>
        <ul className="mt-2 flex flex-col">
          {events.status === 'success' &&
            events.data.slice(0, 3).map((event) => (
              <li key={event.id}>
                <Link to={`/events/${event.slug}`} className="block py-2">
                  <span className="block truncate font-semibold text-fg">{event.title}</span>
                  <span className="block text-xs text-fg-muted">{formatEventDate(event.starts_at)}</span>
                </Link>
              </li>
            ))}
          {events.status === 'success' && events.data.length === 0 && <li className="py-2 text-fg-muted">Nothing on the calendar yet.</li>}
        </ul>
      </section>

      <section aria-labelledby="rail-journal" className="mt-4">
        <h2 id="rail-journal" className="font-semibold text-fg-muted">
          From the club
        </h2>
        <ul className="mt-2 flex flex-col">
          {journal.status === 'success' &&
            journal.data.posts.slice(0, 2).map((post) => (
              <li key={post.slug}>
                <Link to={`/journal/${post.slug}`} className="flex items-center gap-3 py-2">
                  {post.images[0] && <img src={post.images[0].url} alt="" className="size-11 shrink-0 rounded-[4px] object-cover" loading="lazy" />}
                  <span className="line-clamp-2 text-fg">{plainText(post.caption_html)}</span>
                </Link>
              </li>
            ))}
        </ul>
      </section>

      <nav aria-label="Website links" className="mt-8">
        <ul className="flex flex-wrap gap-x-3 text-xs text-fg-muted">
          <li>
            <Link to="/" className="hover:underline">
              Website
            </Link>
          </li>
          <li>
            <Link to="/privacy" className="hover:underline">
              Privacy
            </Link>
          </li>
        </ul>
      </nav>
    </aside>
  )
}
