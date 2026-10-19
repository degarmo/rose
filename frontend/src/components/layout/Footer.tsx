import { BookOpen, Mail, MapPin } from 'lucide-react'
import { Link } from 'react-router'
import { useAuth } from './authContext'
import { isGroup, NAV } from './navigation'
import { QuickExit } from './QuickExit'
import { useSiteSettings } from './siteSettingsContext'
import { SubscribeForm } from './SubscribeForm'
import { Wordmark } from './Wordmark'

const HEADING = 'font-sans text-xs font-semibold uppercase tracking-[0.24em] text-highlight'
const LINK = 'inline-flex min-h-9 items-center text-fg-muted hover:text-fg'

/** The single links, then each group's links, for the footer's two link columns. */
const EXPLORE = NAV.filter((entry) => !isGroup(entry) && entry.to !== '/')
const GROUPS = NAV.filter(isGroup)

export function Footer() {
  const settings = useSiteSettings()
  const auth = useAuth()
  const data = settings.status === 'success' ? settings.data : null
  const staffGuide = auth.user?.staff_guide_url

  return (
    <footer className="border-t border-border bg-surface-sunken pb-28 pt-16 sm:pb-16 print:hidden">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 sm:px-8 md:grid-cols-2 lg:grid-cols-[1.3fr_1fr_1fr_1fr]">
        <div>
          <Wordmark />
          {data?.tagline && <p className="mt-5 max-w-sm text-sm leading-relaxed text-fg-muted">{data.tagline}</p>}
          <div className="mt-8 max-w-sm">
            <h2 className={HEADING}>Stay in touch</h2>
            <div className="mt-4">
              <SubscribeForm />
            </div>
          </div>
        </div>

        <div className="text-sm">
          <h2 className={HEADING}>Find us</h2>
          {settings.status === 'loading' && <p className="mt-4 text-fg-subtle">Loading details</p>}
          {settings.status === 'error' && (
            <p className="mt-4 text-fg-muted">
              Contact details are unavailable right now.{' '}
              <button type="button" onClick={settings.retry} className="underline underline-offset-4 hover:text-fg">
                Try again
              </button>
            </p>
          )}
          {data && (
            <ul className="mt-4 space-y-4 text-fg-muted">
              {data.address_text && (
                <li className="flex gap-3">
                  <MapPin aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-highlight" />
                  <span className="whitespace-pre-line">{data.address_text}</span>
                </li>
              )}
              {data.contact_email && (
                <li className="flex gap-3">
                  <Mail aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-highlight" />
                  <a href={`mailto:${data.contact_email}`} className="break-all underline-offset-4 hover:text-fg hover:underline">
                    {data.contact_email}
                  </a>
                </li>
              )}
            </ul>
          )}
          {data && data.social_links.length > 0 && (
            <>
              <h2 className={`${HEADING} mt-8`}>Elsewhere</h2>
              <ul className="mt-3 flex flex-col">
                {data.social_links.map((link) => (
                  <li key={link.url}>
                    <a href={link.url} rel="noopener noreferrer" className={LINK}>
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <nav aria-label="Footer" className="text-sm">
          <h2 className={HEADING}>Explore</h2>
          <ul className="mt-4 flex flex-col">
            {EXPLORE.map((entry) =>
              isGroup(entry) ? null : (
                <li key={entry.to}>
                  <Link to={entry.to} className={LINK}>
                    {entry.label}
                  </Link>
                </li>
              ),
            )}
            <li>
              <Link to="/about/staff" className={LINK}>
                Our Staff
              </Link>
            </li>
          </ul>
        </nav>

        <div className="text-sm">
          {GROUPS.map((group) => (
            <div key={group.label} className="mb-8 last:mb-0">
              <h2 className={HEADING}>{group.label}</h2>
              <ul className="mt-4 flex flex-col">
                {group.items.map((item) => (
                  <li key={item.to}>
                    <Link to={item.to} className={LINK}>
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className="mx-auto mt-14 flex max-w-7xl flex-col gap-4 border-t border-border/60 px-5 pt-8 text-xs text-fg-subtle sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-5">
          {data?.nonprofit_status_text && <p>{data.nonprofit_status_text}</p>}
          <p>Adults 18+ only. No trackers, no analytics, no photos without consent.</p>
          <Link to="/privacy" className="underline-offset-4 hover:text-fg hover:underline">
            Privacy
          </Link>
          {staffGuide && (
            // Staff only: the admin's own page, behind the staff login.
            <a href={staffGuide} className="inline-flex items-center gap-1.5 underline-offset-4 hover:text-fg hover:underline">
              <BookOpen aria-hidden="true" className="size-3.5" />
              Staff guide
            </a>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden sm:inline">Press Esc twice to leave quickly.</span>
          <QuickExit variant="inline" />
        </div>
      </div>
    </footer>
  )
}
