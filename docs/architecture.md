# Architecture

## Overview

```
Browser --> rose-web (static SPA) --/api, /media rewrite--> rose-api (Django + DRF)
                                                               |-- Postgres
                                                               `-- Redis (rate limiting)
```

The browser only ever talks to one origin. In development the Vite dev server proxies
`/api` and `/media` to Django; in production the static site rewrites them to the API
service (see `render.yaml`). Cookies therefore stay first-party and CSRF works without
cross-site exceptions.

## Backend (`/backend`)

| Path | Purpose |
| --- | --- |
| `config/settings.py` | All settings, read from the environment through django-environ. Production hardening (secure cookies, HSTS, SSL redirect) turns on when `DJANGO_DEBUG` is false. |
| `config/urls.py` | `/robots.txt`, the admin (path from `DJANGO_ADMIN_PATH`) and everything under `/api/`. |
| `apps/core` | Shared helpers with no models: `images.py` (EXIF/GPS stripping, `SanitizedImageField`, random filenames), `email.py` (neutral sender and Message-ID), `ratelimit.py` (proxy-aware, hashed client key), `middleware.py` (`X-Robots-Tag`, `Cache-Control`, `Permissions-Policy`), `views.py` (CSRF token, health, robots). |
| `apps/accounts` | Custom `User` (email login, public `display_name`, private `legal_name` and `phone`), `Profile` (feed opt-in, visibility), `PublicUserSerializer`, `feed_visible_q()`. |
| `apps/pages` | `SiteSettings` singleton, `SocialLink`, `FAQItem`; read-only endpoints; `seed_demo` command. |
| `apps/education` | `Opportunity`; read-only list and detail with category and level filters. |
| `apps/contact` | `ContactMessage`; CSRF-protected, rate-limited POST with honeypot; content-free staff notification. |
| `apps/events`, `apps/feed`, `apps/memberships` | Empty shells. Each `models.py` docstring describes what will live there. |
| `tests/` | pytest suite, including the privacy serializer sweep and the GPS fixture. |

### API

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/csrf/` | Returns `{csrfToken}`. The cookie itself is HttpOnly. |
| GET | `/api/health/` | Health check. |
| GET | `/api/site-settings/` | Singleton. |
| GET | `/api/faqs/` | Published FAQs in order. |
| GET | `/api/education/opportunities/?category=&level=` | Published only. Unknown filter values return 400. |
| GET | `/api/education/opportunities/<slug>/` | Adds `body`. |
| POST | `/api/contact/` | Requires `X-CSRFToken`. 201 on success, 400 with field errors, 429 when limited. |

The API serves JSON only; the browsable API is disabled.

## Frontend (`/frontend/src`)

| Path | Purpose |
| --- | --- |
| `App.tsx` | Age gate first. Nothing else renders, and no API call is made, until the visitor confirms. |
| `router.tsx` | Routes under the shared `Layout`. |
| `components/ui` | Design-system components. See `docs/design-system.md`. |
| `components/layout` | Header, mobile menu, footer, `QuickExit`, `AgeGate`, site settings provider. |
| `components/content` | Page-level building blocks (opportunity card, FAQ accordion, reveal, loading and error states). |
| `pages` | One file per page. |
| `lib/api.ts` | Typed API client, CSRF handling, `ApiError`. |
| `lib/images.ts` | Reads `docs/image-manifest.json` at build time and enforces the face-consent rule. |
| `lib/quickExit.ts`, `lib/useDoubleEscapeExit.ts` | Leave control behaviour. |
| `lib/ageGate.ts` | The 12-hour first-party cookie. |

## How later prompts plug in

**Prompt 2: events and posts with RSVP.** Add models to `apps/events` as its docstring
describes. Mount `apps.events.urls` under `api/events/` in `config/urls.py`. Use
`SanitizedImageField` for any image and `PublicUserSerializer` for any attendee list. On the
frontend, add `pages/EventsPage.tsx` and routes in `router.tsx`, add a nav item in
`components/layout/navigation.ts`, and extend `lib/api.ts`.

**Prompt 3: member social feed.** Add models to `apps/feed` with an `author` foreign key.
Every queryset that a member can see must filter with `feed_visible_q()` from
`apps.accounts.models`, which is what makes opting out hide everything without deleting it.
Routes live under `/members/...` and `/api/members/...`, which robots.txt, `X-Robots-Tag`
and the SPA's robots meta already treat as private.

**Prompt 4: paid membership.** Add models to `apps/memberships`, a member permission class,
and authentication endpoints under `/api/account/`. Replace `pages/JoinPage.tsx`. Store only
the payment provider's identifiers, never card data.

**Prompt 5: hardening and deploy.** Finalise `render.yaml` (domains, plans, the
`rose-api.onrender.com` rewrite target), configure SMTP through `EMAIL_URL`, set
`DJANGO_ADMIN_PATH`, move media to private object storage, add retention rules for contact
messages, and review logging so request logs do not keep client IPs longer than needed.

## Privacy checklist

Check every change against this list.

- [ ] **No third-party trackers.** No analytics, pixels, session recorders, social share
      buttons or comment widgets. Fonts come from `@fontsource` and are bundled. CSP
      (`default-src 'self'`) on both the API and the static site enforces this.
- [ ] **Age gate first.** `App.tsx` renders only `AgeGate` until the `age_ok` cookie exists
      (12 hours, SameSite=Strict). Declining replaces the history entry with `/exit`, which is
      unbranded.
- [ ] **Quick exit everywhere.** `QuickExit` is in the layout (floating on large screens, in
      the header on phones), the mobile menu, the footer and the age gate. It hides the page,
      replaces the history entry and goes to `VITE_QUICK_EXIT_URL` or the SiteSettings
      override. Pressing Esc twice within 800 ms does the same.
- [ ] **Nothing explicit in public.** Imagery is suggestive at most. `ImageFrame` refuses any
      manifest image with `faces_visible: true` and `consent_confirmed: false`, and the API
      withholds uploaded images on the same rule.
- [ ] **Private paths are not indexed.** `/members`, `/account` and `/api` are disallowed in
      `frontend/public/robots.txt`, carry `X-Robots-Tag: noindex, nofollow` from Django and
      Render, and get a `noindex, nofollow` robots meta in the SPA. The API host's own
      robots.txt disallows everything.
- [ ] **Private user fields never leave the server.** `legal_name`, `email` and `phone` are
      never serialized to a public or member endpoint. `tests/test_privacy.py` scans every
      serializer in `apps/` and every public endpoint's output.
- [ ] **Social participation is opt-in.** `Profile.participates_in_feed` defaults to False
      and `visibility` to `private`. Opting out hides content through `feed_visible_q()`; it
      never deletes, and it is reversible.
- [ ] **Uploads are sanitised.** Every image goes through `apps.core.images`: EXIF, GPS,
      XMP and ICC data removed, re-encoded to WebP, random filename.
- [ ] **Email is neutral.** Sender name from `EMAIL_SENDER_NAME`, plain subjects, Message-ID
      on the sender's domain, and contact notifications carry no submitted content.
- [ ] **Security baseline.** django-environ, secure and HttpOnly cookies, HSTS in
      production, django-csp, CSRF on the contact form, django-ratelimit (Redis-backed, hashed
      keys) on the contact endpoint, Argon2 password hashing.
- [ ] **Minimum data.** No IP address or user agent is stored with contact messages.
- [ ] **Neutral naming.** No organisation name, address or explicit terms in package names,
      repository names, environment variable names or commit messages.
