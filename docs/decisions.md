# Decisions

Choices made where the brief did not specify. Privacy-over-convenience calls are marked **(privacy)**.

Prompt 01 decisions come first (1 to 47); prompt 02 and its review addendum follow (48 onwards).

## Prompt 01

### Privacy

1. **(privacy) Contact notification emails contain no submitted content.** Staff get "New message received" or "Priority message received", the topic, a priority flag and an admin link. Names, addresses and message text stay in the database, so they never sit in a mailbox or an email provider's logs. The cost: staff have to open the admin to read a message.
2. **(privacy) No IP address or user agent is stored with contact messages.** Rate limiting uses a salted SHA-256 hash of the client IP as the cache key, and the hash expires with the rate window.
3. **(privacy) Quick exit hides the page before it navigates.** `leaveNow()` sets the document to hidden and retitles the tab, then calls `location.replace`, so nothing stays visible while the next site loads and Back does not return to the current page.
4. **(privacy) Images from `fetch_images.py` default to `faces_visible: true, consent_confirmed: false`.** They are hidden until a person reviews them and marks them safe.
5. **(privacy) Uploaded images follow the same face-consent rule as the manifest.** `Opportunity` gained `hero_image_alt`, `hero_image_faces_visible` and `hero_image_consent_confirmed`. The API returns `hero_image: null` for an image with faces and no consent.
6. **(privacy) ICC colour profiles are stripped along with EXIF, GPS and XMP.** Profiles can carry device information. Colours may shift slightly on wide-gamut photos.
7. **(privacy) Email Message-ID uses the sender's domain** instead of Django's default (the server hostname).
8. **(privacy) The `/prompts` folder is excluded from git** because it names the organisation and its focus.
9. **(privacy) The seeded address is a neighbourhood plus "shared with confirmed visitors".** No street address is seeded, and the Visit page says exact directions come with confirmation.
10. **(privacy) No social links are seeded.** The footer shows them only if staff add them in the admin, and only as plain outbound links.
11. **(privacy) Referrer-Policy is `no-referrer` site-wide**, including an HTML meta tag and `referrerPolicy` on API calls, so outbound links and the quick exit never reveal where the visitor came from.
12. **(privacy) The admin path is configurable** through `DJANGO_ADMIN_PATH`, so production can move it away from `/admin/`.
13. **(privacy) `/media/` responses carry `X-Robots-Tag: noindex, nofollow`.**

### Age gate and quick exit

14. Age gate cookie: `age_ok`, 12 hours, `SameSite=Strict`, `Secure` on HTTPS, set by the browser only. Twelve hours covers one evening without lingering for days.
15. Declining goes to `/exit`, an unbranded white page ("This page is not available."), and replaces the history entry. `/exit` is also disallowed in `robots.txt`.
16. Default quick-exit destination is `https://www.weather.gov/`. Only `https://` URLs are accepted. `SiteSettings.quick_exit_url` overrides the build default once loaded, so Leave works even when the API is down.
17. Double Escape means two presses within 800 ms. The listener runs in the capture phase so dialogs cannot swallow it; key-repeat events are ignored.
18. On phones the Leave control sits in the fixed header next to the menu button rather than floating, because a floating button covered full-width buttons. On large screens it floats bottom-right. It also appears in the mobile menu, the footer and on the age gate.

### Backend

19. Django 5.2 (current LTS) rather than 5.0 or 5.1.
20. Apps live in `backend/apps/` with an extra `core` app (no models) for shared helpers.
21. Redis is required in production for rate limiting. django-ratelimit refuses non-shared or non-atomic caches. Locmem is allowed only when `DJANGO_DEBUG` is true. `render.yaml` provisions a Render Key Value instance.
22. Contact rate limit defaults to 5 per hour per client (`CONTACT_RATE_LIMIT`). Invalid submissions count too. Limited requests get HTTP 429.
23. The client IP for rate limiting trusts exactly `DJANGO_TRUSTED_PROXY_COUNT` proxies (1 on Render), so a forged `X-Forwarded-For` cannot dodge the limit.
24. The honeypot field is `website`. A filled honeypot gets a normal 201 and nothing is stored or sent.
25. CSRF: the SPA gets its token from `GET /api/csrf/`; the cookie is HttpOnly and `SameSite=Strict`. The contact view is wrapped in `csrf_protect` because DRF exempts API views by default.
26. DRF renders JSON only; the browsable API is off everywhere.
27. `ContactMessage.is_priority` is a stored field set automatically for "Report a concern", so the admin can filter and sort on it. The admin is read-only for submissions except the `handled` flag, has bulk "mark handled / not handled" actions, and cannot create messages.
28. Notification recipient: `CONTACT_NOTIFY_EMAIL` (a private inbox) if set, otherwise the public `SiteSettings.contact_email`.
29. `SiteSettings` gained `directions_text` so the Visit page's directions are editable rather than hard-coded. Social links are a `SocialLink` inline model instead of a JSON blob.
30. `User.display_name`: 3 to 30 characters from `A-Z a-z 0-9 _ . -`, unique. Emails are stored lowercased and matched case-insensitively. Minimum password length is 12.
31. `Profile.visibility` choices are `private` (default) and `members`. `feed_status_changed_at` records the last opt-in or opt-out. `feed_visible_q()` is the single filter the feed must use.
32. Opportunity `cta_url` accepts a site path (`/contact`), an `https://` URL or a `mailto:` link only.
33. The home page features the first three published opportunities by `sort_order`. No separate "featured" flag.
34. Uploaded images are capped at 40 megapixels, resized to a 2400 px longest side, and stored as WebP at quality 82, with transparency kept.
35. Time zone is `America/Chicago`. Seeded class dates fall on upcoming Thursdays at 7 pm.

### Frontend

36. Fonts: Fraunces (display, variable with optical sizing) and Manrope (body), from `@fontsource-variable`. Common ligatures are off for body text because Manrope turns "(c)" into a copyright sign, which broke "501(c)(3)".
37. Tailwind CSS v4 with tokens in `@theme` (CSS variables), primitives plus semantic aliases. See `design-system.md`.
38. `npm run lint` uses oxlint, the current Vite React template default. The backend uses ruff.
39. Placeholder textures are pure CSS gradients (velvet, candle, silk, leather, shadow, architecture, rose), each sized to the final aspect ratio.
40. Image variants from `fetch_images.py` are 640, 1280 and 1920 px wide WebP. They are never upscaled.
41. Data loading uses a small `useAsync` hook instead of a data library. Each result is tagged with the request it answers, so a stale response cannot overwrite a newer one.
42. Modal uses the native `<dialog>` element for focus trapping and Escape handling. The mobile menu is a full-screen Modal sheet.
43. The FAQ accordion uses native `<details>` and `<summary>`.
44. Education filters are kept in the URL (`?category=&level=`), so filtered views can be linked and survive reload.
45. The staff section on About uses six placeholder display names with monogram tiles, not photos.

### Infrastructure

46. Docker Compose maps Postgres to host port 5433 and Redis to 6380 so they do not clash with locally installed services.
47. `render.yaml` serves the SPA as a static site that rewrites `/api/*` and `/media/*` to the API service, keeping one origin. The static site sets its own CSP, HSTS and robots headers.

## Prompt 02

### Image consent pattern and review (addendum)

48. The pattern is a cached factory, `consented_image(field, upload_to)`, that returns an abstract model adding `<field>`, `<field>_alt`, `<field>_faces_visible` and `<field>_consent_confirmed`, plus `ConsentImageMixin` for the publish check and `consent_image_payload()` as the render block. A factory, rather than a fixed mixin, so each model keeps the field names the brief asked for (`hero_image_*`).
49. `Opportunity` moved onto it with a migration that only changes help text, so no data is touched. A test migrates a row from the old schema and checks every image field survives.
50. `PostImage` follows the addendum's naming (`image`, `image_alt`, `image_faces_visible`, `image_consent_confirmed`) rather than prompt 02's `alt_text`, `faces_visible`, `consent_confirmed`, so every image in the project works the same way.
51. Alt text is required whenever an image is set. The consent check blocks publishing; drafts may hold an unconsented image while staff sort out consent.
52. `review_images` is interactive by default, with `--list` to only list and `--set file=no-faces|consent|keep-hidden` for scripted use. Quitting part-way saves the decisions made so far.
53. The admin uses a custom `AdminSite` (installed by replacing `django.contrib.admin` with `apps.core.apps.RoseAdminConfig`) to add the read-only Image review page. Manifest images are served to staff through an admin-only view with `Cache-Control: private, no-store`, so hidden images are never public. The page also lists uploaded images (opportunities, events, journal) with the reason each is shown or hidden.

### Accounts

54. **(privacy)** Registering with an email that already has an account returns exactly the same response as a new sign-up and emails the owner instead ("About your sign-up"). Password reset and login also look identical for known and unknown emails. Nobody can test which emails have accounts.
55. **(privacy)** Registration does not sign the person in. They confirm their email and then log in, because signing in straight away would reveal whether the email was new.
56. **(privacy)** Tokens in emailed links (verify, reset, cancel) sit in the URL fragment (`#token=...`), which browsers never send to servers, so they stay out of access logs and proxies. Pages strip them from the address bar once used.
57. Verification links last 3 days and stop working if the email changes. Reset links last 2 hours and stop working once the password changes. Following a reset link also counts as verifying the email.
58. Unverified accounts can log in (to resend the link) but cannot RSVP.
59. Lockout: 5 failed logins for an email lock it for 15 minutes, whether or not the email has an account. Rate limits by default: login 20/hour per IP and 10/hour per email; registration 5/hour per IP and 3/hour per email; password reset 5/hour per IP and 3/hour per email. All are configurable, and every key is a salted hash.
60. The password similarity check also compares against email, display name and legal name. Display names are unique regardless of letter case.
61. Login rotates the CSRF token, so session responses carry the new one and the client swaps it in. CSRF failures return JSON (`CSRF_FAILURE_VIEW`), so the client can tell them apart and retry once with a fresh token.
62. **(privacy)** Account email tasks receive ids, not tokens; the worker builds the link. The one exception is the "account closed" email, which carries the address because the account no longer exists.
63. Deleting an account first cancels its upcoming RSVPs through the normal service, so freed places go to the waitlist (without emailing the departing person), then deletes the user, profile and every RSVP. Their contact messages keep the message text for safety records but lose name, email and phone (`anonymized_at` is set). For that, `ContactMessage.email` became optional.

### Events and RSVP

64. Audiences: `public` events are visible to everyone and need a verified account to RSVP. `account` events are hidden from signed-out visitors everywhere: list, detail, calendar, ICS and journal links. `members` events are visible, but RSVP shows "Members only". Prompt 04 changes only the members branch of `events.access.can_rsvp`.
65. `can_rsvp` checks, in order: unpublished, account-only while signed out, past the RSVP deadline, members only, not open yet, signed out, unverified.
66. RSVPs close when the event starts unless staff set `rsvp_closes_at`, which cannot be after the event ends.
67. `max_party_size` is 1 or 2 per event (default 2, meaning one guest). Capacity counts people, not RSVPs.
68. Changing party size while going needs room for it. Editing a waitlisted RSVP keeps its place in line. Re-RSVPing after a cancellation reuses the same row, so the one-per-person rule holds.
69. Promotion goes oldest first and promotes every waitlisted RSVP that fits, skipping parties too big for the space left. A later party of one can therefore get in ahead of an earlier party of two that still does not fit.
70. A full event without a waitlist refuses the RSVP with HTTP 409 and code `full`.
71. Event bodies are sanitised on save with nh3: paragraphs, line breaks, bold, italics, lists, h3, h4, blockquote, and `https:` or `mailto:` links with `rel="noopener noreferrer nofollow"`.
72. Event slugs `calendar`, `rsvp` and `cancel` are reserved because they collide with routes.
73. "Repeat weekly" makes 1 to 26 copies at the same Chicago wall-clock time across daylight-saving changes. The slug is the base plus the date, replacing any existing date suffix. Copies that already exist are skipped and reported. Publish state and the image file are copied; RSVPs never are.
74. The door list shows going RSVPs only, sorted by display name, with party size, note to hosts and a check-in toggle. Viewing needs `view_rsvp`, toggling needs `change_rsvp`, and the CSV needs a new `export_attendees` permission. **(privacy)** The CSV contains no email addresses and is protected against spreadsheet formula injection. The export log records the exporter's display name and the row count, not attendee data, and is read-only in admin.
75. Retention counts are people, not RSVPs: `final_going_count` and `final_checked_in_count` sum party sizes. The purge runs every 6 hours and deletes cancelled RSVPs too.
76. Reminders run every 15 minutes for events in the next 24 hours, once per RSVP. People who RSVPed inside that window are skipped because they just got a confirmation.
77. Email subjects: "Your plans for {day}", "Your waitlist place for {day}", "A place opened up for {day}", "Your plans for {day} are cancelled", "A reminder for {day}". Bodies include the title, time, party size, an ID reminder, a cancel link and the event link. Cancel links are signed and stop working once RSVPs are purged.
78. Calendar files are always named `evening.ics` and downloaded as attachments. Opting in adds the real title, plus the location label and the site address. UIDs are derived from the event id and reveal nothing.
79. RSVP states shown to people: Open, Waitlist (full, waitlist open), Full (no waitlist), Closed, Members only, Opens soon, Going, On the waitlist (their own).
80. When enabled, the attendee count is shown even when it is zero.
81. The month view is a Sunday-first six-week grid in Chicago time: dots on phones, titles on wider screens, and the month's events listed below the grid.

### Journal

82. Captions are plain text. Line breaks are kept, `https://` URLs become links, and the server renders `caption_html` with nh3 as a final pass.
83. Posts with a future `published_at` stay hidden until then.
84. Cursor pagination, 12 per page, newest first. Infinite scroll uses an IntersectionObserver, with a visible Load more button as the fallback.
85. A linked event beats the CTA. A link to an account-only event is hidden from signed-out visitors.
86. If a post's author is deleted, the byline reads "The house".
87. Opening a post shows a modal without changing the URL; the modal links to the permalink. Tiles in the home page Journal strip go straight to the permalink.
88. Seeded journal images are generated by Pillow (soft candlelight gradients in the palette, no photography) and go through the same metadata-stripping upload path.
89. Demo accounts are always created by `seed_demo`, with new random passwords on every run. Credentials are printed only when `DEBUG` is on. The verified demo account fills the at-capacity event (party of 2).

### Frontend

90. With Events, Journal and the account menu added, the desktop nav starts at the `xl` breakpoint (1280 px). The Home item is dropped there because the wordmark links home.
91. "Add to calendar" appears once someone is going; the include-details box is unticked by default.
92. Vitest 5 with Testing Library and jsdom. The setup file polyfills `<dialog>` and `matchMedia`, which jsdom lacks.
93. `VITE_PROXY_TARGET` sets where the dev server forwards `/api` and `/media`; Docker points it at the api service.

### Infrastructure

94. Celery uses the same Redis as the cache: database 0 for the queue and 1 for the cache locally, and one Render Key Value instance with `noeviction` in production, since Celery needs nothing evicted.
95. On macOS, run the local worker with `--pool=threads`. The default prefork pool fails there, because Python uses `spawn`. Docker and Render run Linux and use prefork.
96. Compose runs the whole stack with the repository mounted. `node_modules` lives in a named volume so macOS-built native binaries never reach the Linux container.
97. In `render.yaml`, the API, worker and beat share one generated `DJANGO_SECRET_KEY` through an env group, because the worker signs links that the API verifies.
98. `redis` is pinned to 6.4.0 because the current kombu requires it.
