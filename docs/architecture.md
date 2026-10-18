# Architecture

## Overview

```
Browser --> rose-web (static SPA) --/api, /media rewrite--> rose-api (Django + DRF)
                                                               |-- Postgres
                                                               |-- Redis (cache, rate limits, Celery queue)
                                                               `-- Celery worker + beat (email, reminders, retention)
```

The browser only ever talks to one origin. In development the Vite dev server proxies
`/api` and `/media` to Django (target set by `VITE_PROXY_TARGET`); in production the static
site rewrites them to the API service (see `render.yaml`). Session and CSRF cookies are
therefore first-party, and the SPA uses Django session auth with CSRF on every write. No
token is ever stored in browser storage.

## Backend (`/backend`)

| Path | Purpose |
| --- | --- |
| `config/settings.py` | All settings, read from the environment through django-environ. Production hardening turns on when `DJANGO_DEBUG` is false. |
| `config/celery.py` | Celery app. Reads `CELERY_*` settings; beat schedule lives in settings. |
| `config/urls.py` | `/robots.txt`, the admin (path from `DJANGO_ADMIN_PATH`) and everything under `/api/`. |
| `templates/admin/` | Admin additions: Image review, door list, Repeat weekly form, and the index link to Image review. |
| `apps/core` | Shared helpers with no models: `consent_images.py` (the image + alt + faces + consent pattern), `images.py` (EXIF/GPS stripping, random names), `manifest.py` and the `review_images` command, `admin_site.py` (custom AdminSite with the Image review page), `api.py` (CSRF-protected API base view), `ratelimit.py` (hashed, proxy-aware keys), `text.py` (nh3 sanitising), `email.py` (neutral sender, Message-ID, site links), `middleware.py`, `views.py`. |
| `apps/accounts` | `User` (email login, `display_name`, private `legal_name`, `phone`, `email_verified_at`), `Profile`, registration, verification, login lockout, password reset and change, display-name change, account deletion. Email tasks in `tasks.py`. |
| `apps/pages` | `SiteSettings`, `SocialLink`, `FAQItem`; `seed_demo` command and its generated placeholder art (`demo_media.py`). |
| `apps/education` | `Opportunity` (uses the consented image pattern). |
| `apps/contact` | `ContactMessage`, content-free staff notification, `anonymize_messages_from()`. |
| `apps/events` | `Event`, `RSVP`, `AttendeeExport`; `access.can_rsvp()`, `services.py` (capacity and waitlist under a row lock), `tasks.py` (RSVP emails, reminders, retention purge), `ics.py`, `recurrence.py` (Repeat weekly), admin door list and CSV export. |
| `apps/journal` | Staff-written public posts: `Post` and `PostImage` (1 to 10 images, consented image pattern), cursor-paginated API. |
| `apps/feed`, `apps/memberships` | Empty shells for prompts 3 and 4. |
| `tests/` | pytest suite, including the attendee-identity sweep over every API route and a two-thread race for the last place. |

### API

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/csrf/` | `{csrfToken}`; the cookie itself is HttpOnly. |
| GET | `/api/health/` | Health check. |
| GET | `/api/site-settings/`, `/api/faqs/` | Site content. |
| GET | `/api/education/opportunities/[<slug>/]` | `?category=&level=` filters. |
| POST | `/api/contact/` | Rate limited, honeypot. |
| GET, PATCH | `/api/account/session/` | Who is signed in (`user: null` if nobody); PATCH changes display name. The only endpoint that returns an email, and only the caller's own. |
| POST | `/api/account/register/`, `verify-email/`, `verify-email/resend/`, `login/`, `logout/`, `password-reset/`, `password-reset/confirm/`, `password/`, `delete/` | Account actions. Login, register and reset are rate limited per IP and per email. |
| GET | `/api/account/rsvps/` | The caller's own upcoming RSVPs. |
| GET | `/api/events/` | Upcoming visible events; `?category=`, `?past=1`. |
| GET | `/api/events/calendar/?start=&end=` | Events overlapping a date range (max 62 days). |
| GET | `/api/events/<slug>/` | Detail with the caller's RSVP state. |
| POST, DELETE | `/api/events/<slug>/rsvp/` | RSVP or update; cancel. |
| GET | `/api/events/<slug>/calendar.ics[?details=1]` | Discreet by default. |
| POST | `/api/events/rsvp/cancel/` | Cancel from an emailed, signed link. |
| GET | `/api/journal/posts/[<slug>/]` | Cursor-paginated, 12 per page. |

### Background work

| Task | When | What |
| --- | --- | --- |
| `accounts.tasks.*` | On commit after account actions | Verification, reset, password changed, account closed. Tasks take ids and build tokens in the worker, so no token sits in the queue. |
| `events.tasks.send_rsvp_email` | On commit after RSVP changes | Confirmation, waitlist, promoted, cancellation. |
| `events.tasks.send_due_reminders` | Beat, every 15 minutes | 24-hour reminder, once per RSVP. |
| `events.tasks.purge_expired_rsvps` | Beat, every 6 hours | Deletes RSVPs `RSVP_RETENTION_DAYS` after the event ends and keeps `final_going_count` and `final_checked_in_count`. |

## Frontend (`/frontend/src`)

| Path | Purpose |
| --- | --- |
| `App.tsx` | Age gate first; then site settings, auth and toast providers around the router. |
| `router.tsx` | All routes under the shared `Layout`. |
| `components/ui` | Design-system components. See `docs/design-system.md`. |
| `components/layout` | Header (with `AccountMenu`), footer, `QuickExit`, `AgeGate`, auth and site settings providers. |
| `components/content` | `EventCard`, `MonthCalendar`, `RSVPPanel`, `Carousel`, `PostView`, `JournalTile`, opportunity card, FAQ accordion, states. |
| `pages` | One file per page; `pages/account/` holds login, register, verify, forgot, reset and the account page. |
| `lib/api.ts` | Typed API client; keeps the CSRF token in memory and refreshes it from session responses. |
| `lib/calendar.ts`, `lib/events.ts`, `lib/format.ts` | Month grid maths, RSVP state labels, Chicago-time formatting, safe `next` paths, URL fragment parsing. |
| `**/*.test.tsx`, `test/` | Vitest + Testing Library. |

## How later prompts plug in

**Prompt 3: member social feed.** Add models to `apps/feed` with an `author` foreign key.
Every queryset a member can see must filter with `feed_visible_q()` from
`apps.accounts.models`, which is what makes opting out hide everything without deleting it.
Images use `consented_image(...)` from `apps.core.consent_images`. Routes go under
`/members/...` and `/api/members/...`, which robots.txt, `X-Robots-Tag` and the SPA already
treat as private. Author bylines use `PublicUserSerializer`.

**Prompt 4: paid membership.** Add models to `apps/memberships`. Replace only the members
branch inside `apps.events.access.can_rsvp` with a real membership check; nothing else in
the RSVP path needs to change. Replace `pages/JoinPage.tsx`. Store only the payment
provider's identifiers, never card data.

**Prompt 5: hardening and deploy.** Finalise `render.yaml` (domains, plans, the
`rose-api.onrender.com` rewrite target), configure SMTP through `EMAIL_URL`, set
`DJANGO_ADMIN_PATH`, move media to private object storage, add retention for contact
messages and the attendee export log, and review request logging so client IPs are not kept.

## Privacy checklist

Check every change against this list.

- [ ] **No third-party trackers.** No analytics, pixels, session recorders, social share
      buttons or comment widgets. Fonts are bundled. CSP `default-src 'self'` on the API and
      the static site enforces this. Calendar files are downloaded, never Google Calendar links.
- [ ] **Age gate first.** `App.tsx` renders only `AgeGate` until the `age_ok` cookie exists.
      No API call is made before that, including the session check.
- [ ] **Quick exit everywhere.** `QuickExit` on every page and Esc twice.
- [ ] **Nothing explicit in public.** Every image field uses `consented_image(...)`: alt text
      is required, and anything with faces visible but no consent is blocked from publishing
      in admin and withheld by the API (`consent_image_payload`). Manifest images follow the
      same rule in `ImageFrame`. Admin > Image review shows what is hidden and why.
- [ ] **Private paths are not indexed.** `/members`, `/account`, `/api`, `/exit` and
      `/events/cancel` are disallowed and carry `noindex, nofollow`.
- [ ] **Private user fields never leave the server.** Only `AccountSerializer` (marked
      `self_only`) includes an email, and only `session_payload()` uses it, for the caller.
      `tests/test_privacy.py` checks every serializer.
- [ ] **Social participation is opt-in** through `Profile.participates_in_feed` and
      `feed_visible_q()`.
- [ ] **Uploads are sanitised** by `SanitizedImageField`.
- [ ] **Email is neutral.** Subjects never name the organisation, the event or its category
      ("Your plans for Friday"). Notifications about contact messages carry no content.
- [ ] **Security baseline.** Session auth with CSRF on every write; Argon2; 12-character
      passwords checked against email and display name; secure cookies, HSTS, CSP; rate
      limits on contact, login, registration and password reset (per IP and per email,
      hashed keys); 15-minute lockout after 5 failed logins.
- [ ] **No account enumeration.** Registration, password reset and login give the same
      response whether or not an email has an account.
- [ ] **Tokens stay out of logs.** Verification, reset and cancel links put their tokens in
      the URL fragment, which browsers never send to the server.
- [ ] **Minimum data.** No IP or user agent stored with messages; deleting an account
      deletes the profile and RSVPs and strips identity from contact messages.

### RSVP privacy rules

- [ ] **Attendee lists are never exposed** through any public or member API, not even to
      other attendees. The only per-person RSVP data any endpoint returns is the caller's own.
      `test_no_endpoint_reveals_who_is_attending` sweeps every API route as three viewers.
- [ ] **The only public signal is a count**, and only when `Event.show_attendee_count` is on.
      Names are never shown.
- [ ] **Staff see attendees in admin only**: the RSVP list and the per-event door list (display
      names, party size, note, check-in). Door lists never include email addresses.
- [ ] **Every CSV export is logged** in `AttendeeExport` with who exported it and when, and
      needs the `events.export_attendees` permission.
- [ ] **RSVPs are deleted** `RSVP_RETENTION_DAYS` (default 30) after the event ends; only the
      aggregate counts remain on the event.
- [ ] **Calendar files are discreet by default**: "Rose - Evening" and no location, unless the
      person ticks the box to include details.
