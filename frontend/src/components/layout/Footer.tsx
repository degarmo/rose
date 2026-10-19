import { Link, useLocation } from 'react-router'
import { cn } from '@/lib/cn'
import { GUTTER } from '../ui'
import { useAuth } from './authContext'
import { QuickExit } from './QuickExit'
import { useSiteSettings } from './siteSettingsContext'
import { SubscribeForm } from './SubscribeForm'

/** The address as one sentence: its lines joined, each ending in a full stop. */
function oneLine(text: string) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => (/[.!?]$/.test(line) ? line : `${line}.`))
    .join(' ')
}

function PrivacyLinks() {
  const auth = useAuth()
  const staffGuide = auth.user?.staff_guide_url
  return (
    <>
      <Link to="/privacy" className="text-fg-muted hover:text-fg">
        Privacy
      </Link>
      {/* Staff only: the admin's own page, behind the staff login. */}
      {staffGuide && (
        <a href={staffGuide} className="text-fg-muted hover:text-fg">
          Staff guide
        </a>
      )}
    </>
  )
}

/**
 * The website footer. The home page has the full one (design "Home"): the wordmark,
 * address and email, the email list sign-up, then Privacy and Leave. Every other page has
 * the single row from the inner-page designs (Events, Contact): address and email, then
 * Privacy and Leave.
 */
export function Footer() {
  const { pathname } = useLocation()
  const settings = useSiteSettings()
  const data = settings.status === 'success' ? settings.data : null
  const address = data?.address_text ? oneLine(data.address_text) : ''
  const email = data?.contact_email

  const contact = (
    <>
      {settings.status === 'error' && (
        <span>
          Contact details are unavailable right now.{' '}
          <button type="button" onClick={settings.retry} className="underline underline-offset-4 hover:text-fg">
            Try again
          </button>
        </span>
      )}
      {address && <span>{address}</span>}
      {email && (
        <a href={`mailto:${email}`} className="break-all text-link hover:text-primary-hover">
          {email}
        </a>
      )}
    </>
  )

  if (pathname !== '/') {
    return (
      <footer className="border-t border-border bg-canvas py-8 text-sm text-fg-muted lg:py-10 print:hidden">
        <div className={cn('mx-auto flex max-w-[1440px] flex-col gap-4 lg:flex-row lg:items-center lg:justify-between', GUTTER)}>
          <p className="flex flex-col gap-1 sm:flex-row sm:flex-wrap sm:gap-x-1.5">{contact}</p>
          <div className="flex items-center justify-between gap-5 lg:justify-end">
            <div className="flex gap-5">
              <PrivacyLinks />
            </div>
            <QuickExit />
          </div>
        </div>
      </footer>
    )
  }

  return (
    <footer className="border-t border-border bg-canvas pb-10 pt-8 text-sm lg:py-10 print:hidden">
      <div className={cn('mx-auto grid max-w-[1440px] gap-4 lg:grid-cols-3 lg:gap-8', GUTTER)}>
        <div className="flex flex-col gap-1.5 text-fg-muted lg:gap-1.5">
          <Link to="/" className="self-start font-display text-[1.375rem] leading-tight text-wordmark">
            Rose
          </Link>
          {contact}
          {data && data.social_links.length > 0 && (
            <ul className="flex flex-wrap gap-x-4">
              {data.social_links.map((link) => (
                <li key={link.url}>
                  <a href={link.url} rel="noopener noreferrer" className="hover:text-fg">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
        <SubscribeForm />
        <div className="flex items-center justify-between gap-5 lg:justify-end">
          <div className="flex gap-5">
            <PrivacyLinks />
          </div>
          <QuickExit />
        </div>
      </div>
    </footer>
  )
}
