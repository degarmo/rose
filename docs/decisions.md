# Decisions

Choices made where the brief did not specify. Privacy-over-convenience calls are marked **(privacy)**.

## Privacy

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

## Age gate and quick exit

14. Age gate cookie: `age_ok`, 12 hours, `SameSite=Strict`, `Secure` on HTTPS, set by the browser only. Twelve hours covers one evening without lingering for days.
15. Declining goes to `/exit`, an unbranded white page ("This page is not available."), and replaces the history entry. `/exit` is also disallowed in `robots.txt`.
16. Default quick-exit destination is `https://www.weather.gov/`. Only `https://` URLs are accepted. `SiteSettings.quick_exit_url` overrides the build default once loaded, so Leave works even when the API is down.
17. Double Escape means two presses within 800 ms. The listener runs in the capture phase so dialogs cannot swallow it; key-repeat events are ignored.
18. On phones the Leave control sits in the fixed header next to the menu button rather than floating, because a floating button covered full-width buttons. On large screens it floats bottom-right. It also appears in the mobile menu, the footer and on the age gate.

## Backend

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

## Frontend

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

## Infrastructure

46. Docker Compose maps Postgres to host port 5433 and Redis to 6380 so they do not clash with locally installed services.
47. `render.yaml` serves the SPA as a static site that rewrites `/api/*` and `/media/*` to the API service, keeping one origin. The static site sets its own CSP, HSTS and robots headers.
