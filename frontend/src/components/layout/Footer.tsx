import { Mail, MapPin } from 'lucide-react'
import { Link } from 'react-router'
import { NAV_ITEMS } from './navigation'
import { QuickExit } from './QuickExit'
import { useSiteSettings } from './siteSettingsContext'
import { Wordmark } from './Wordmark'

export function Footer() {
  const settings = useSiteSettings()
  const data = settings.status === 'success' ? settings.data : null

  return (
    <footer className="border-t border-border bg-surface-sunken pb-28 pt-16 sm:pb-16 print:hidden">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Wordmark />
          <p className="mt-5 max-w-sm text-sm leading-relaxed text-fg-muted">
            {data?.tagline || 'A volunteer-run members’ house in Chicago.'}
          </p>
          <p className="mt-6 text-xs text-fg-subtle">A volunteer-run 501(c)(3) nonprofit. Adults 18+ only.</p>
        </div>

        <div className="text-sm">
          <h2 className="font-sans text-xs font-semibold uppercase tracking-[0.24em] text-highlight">Find us</h2>
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
                  <a href={`mailto:${data.contact_email}`} className="underline-offset-4 hover:text-fg hover:underline">
                    {data.contact_email}
                  </a>
                </li>
              )}
              {data.social_links.map((link) => (
                <li key={link.url}>
                  <a
                    href={link.url}
                    rel="noopener noreferrer"
                    className="underline-offset-4 hover:text-fg hover:underline"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="text-sm">
          <h2 className="font-sans text-xs font-semibold uppercase tracking-[0.24em] text-highlight">Explore</h2>
          <ul className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1 md:grid-cols-1">
            {NAV_ITEMS.filter((item) => item.to !== '/').map((item) => (
              <li key={item.to}>
                <Link to={item.to} className="inline-flex min-h-9 items-center text-fg-muted hover:text-fg">
                  {item.label}
                </Link>
              </li>
            ))}
            <li>
              <Link to="/privacy" className="inline-flex min-h-9 items-center text-fg-muted hover:text-fg">
                Privacy
              </Link>
            </li>
          </ul>
        </div>
      </div>

      <div className="mx-auto mt-14 flex max-w-7xl flex-col gap-4 border-t border-border/60 px-5 pt-8 text-xs text-fg-subtle sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <p>No trackers, no analytics, no photos without consent.</p>
        <div className="flex items-center gap-4">
          <span className="hidden sm:inline">Press Esc twice to leave quickly.</span>
          <QuickExit variant="inline" />
        </div>
      </div>
    </footer>
  )
}
