# Decisions

Choices made where the brief did not specify. Privacy-over-convenience calls are marked **(privacy)**.

Prompt 01 decisions come first (1 to 47); prompt 02 and its review addendum follow (48 to 99), then prompt 03 (100 to 134), prompt 04 (135 to 173) and prompt 05 (174 onwards).

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
11. **(privacy) No referrer ever leaves the site.** Every response carries `Referrer-Policy: no-referrer` (and the page has the matching meta tag), so outbound links and the quick exit never reveal where the visitor came from. The site's own API calls ask for `same-origin` explicitly, and the admin's pages use `same-origin` (decision 174): under `no-referrer` browsers send `Origin: null` on POST, which fails Django's CSRF origin check. `same-origin` still sends nothing to other sites.
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
47. (Replaced in prompt 05, decision 175.) `render.yaml` first served the SPA as a static site that rewrote `/api/*` and `/media/*` to the API service.

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

64. Audiences: `public` events are visible to everyone and need a verified account to RSVP. `account` events are hidden from signed-out visitors everywhere: list, detail, calendar, ICS and journal links. `members` events are visible to everyone, and RSVP needs the `members_events` entitlement (an active or grace membership whose tier grants it). Others see the membership panel instead of the form. This rule is final.
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
99. Compose host ports can be overridden with `DB_PORT`, `CACHE_PORT`, `API_PORT` and `WEB_PORT`, and the API, worker and beat share one image (`rose-backend:dev`), so it is built once.

## Prompt 03

### Access and entitlement

100. Feed access lives in `apps/feed/access.py`. `has_feed_entitlement()` holds the entitlement rule: the `feed` entitlement from `memberships.access.entitlements`, which comes from an active or grace membership whose tier grants the feed, or from the staff grant (`Profile.feed_access_granted`, with who and when recorded by the admin). The staff grant stays permanently for volunteers. This rule is final.
101. **(privacy)** The 404 check runs before CSRF and before anything else, through a session authentication class that defers CSRF until access is confirmed. Without that, a POST from someone without access would get a CSRF 403 and confirm the endpoint exists.
102. Suspended and banned members get the same 404 as everyone else. A banned member's content is hidden through `feed_visible_q()`. A suspended member's content stays visible.
103. Join, step away, erase and export live under `/api/account/feed/`, not `/api/members/`, so people who stepped away or were banned can still reach them. Those endpoints are 404 for anyone with no entitlement and no feed history, and `/account` shows them a "Member community" panel explaining that the feed comes with membership.
104. A posting cooldown comes from a moderator's warning: 24 hours (`FEED_WARNING_COOLDOWN_HOURS`). The member can still read, like and comment.
105. Rejoining goes through the same three-step flow, including the guidelines.

### Guidelines

106. Version 1 is created by a data migration so every environment starts with it. Published versions are read-only in admin, because they record what people agreed to. Publishing a new version notifies every participant in-app, and they cannot post until they accept it (they can still read).
107. "Scroll to the end" counts as reaching within 12 px of the bottom of the guidelines box. If the text fits without scrolling, the checkbox is enabled straight away.

### Posts, images and redaction

108. **(privacy)** URLs use random, opaque ids (`public_id`) for posts, images and comments, never database ids, so nothing reveals how many posts exist or their order. Avatars are served by a random key that changes on every upload.
109. **(privacy)** Member uploads, including avatars, go to private storage (`PRIVATE_MEDIA_ROOT`) through `apps.core.private_media`. That storage refuses to produce any URL, so no template, admin widget or serializer can leak one. The admin never renders private file fields; moderators see previews through a staff-only view.
110. Feed images use the consent pattern with `alt_required=False` (alt text encouraged, not required, as the brief asks for members). The post's attestation sets `image_consent_confirmed` on every image, and `image_faces_visible` is recorded as true, since the server cannot know.
111. Raw uploads wait in private `incoming/` until the Celery worker strips and re-encodes them, then the raw file is deleted. A file that fails processing is dropped; a post left with no images and no caption is marked removed. Each image is processed in its own savepoint.
112. Avatars are small, so they are cleaned in the request rather than queued. An avatar that "shows a face" needs the attestation. The hint that a non-face avatar is normal appears wherever an avatar is chosen.
113. **(privacy)** Redaction is written with canvas directly, with no library. Order: rotate, crop, then cover or pixelate. Cover is a solid fill in the ink colour; pixelate keeps about 10 blocks across a region's long side. Changing the crop clears earlier cover-ups, because they would no longer line up. Output is JPEG at quality 0.9, capped at 2400 px. Even photos with no edits go through this pipeline, so the original file never leaves the device. The UI says covering is the safest choice.
114. New members' first 3 posts (`FEED_PREMODERATION_POSTS`) are pending until approved. The count is of posts that were ever published, so a removed post still counts towards the three. The author alone sees "Waiting for review", via an author-only `in_review` flag.
115. Limits are counted in the database rather than the cache: 10 posts per rolling 24 hours and 60 comments per rolling hour, with HTTP 429 beyond that.
116. Text-only posts need no attestation. A post must have a caption or a photo. Editing a post that has no photos cannot empty its caption.

### Interactions and notifications

117. Liking your own post is allowed but never notifies you. A like count only ever goes to the post's author, and counts only likes from visible members outside a block with the author.
118. Comments are plain text with links, 500 characters, rendered through the same sanitiser as captions. The post's author and the commenter can delete a comment; anyone can report one.
119. Blocking also removes follows in both directions, because a follow is a relationship, not content. Likes and comments between the two people are hidden from everyone, not deleted, and return if the block is lifted. Only the blocker can see and lift their blocks (from their profile settings); the blocked person never learns of the block.
120. Mute hides someone from your feed tabs only; their profile and posts stay reachable.
121. Notifications: one grouped row per post for likes with a live, nameless count ("3 people liked your post"); a comment notification names the commenter. Notifications from people who opted out, were banned or are in a block with you are dropped. The list keeps the latest 50, and opening it marks everything read.
122. **(privacy)** Direct messages are deliberately left out for safety and moderation reasons. Private one-to-one channels are where pressure and harassment hide from moderators, and where images leave the watermarked, reportable feed.

### Directory and profiles

123. The directory returns at most 20 matches for 3 or more typed characters, and lists only members who turned "Hide me" off (default on). Profiles show the month someone joined the feed, never a date. Posts older than 7 days carry only a month; the API never sends their exact time.
124. A profile hidden by a report disappears for others (404) but stays visible to its owner.

### Reports and moderation

125. One report per person per item; repeats are accepted silently. "Other" needs a short description. Comments and profiles can be auto-hidden too. For a profile, hiding means the profile page, avatar and bio disappear for others while their posts stay.
126. The moderation queue is a custom admin page with a form per item: approve, remove (a reason is required and goes to the author in-app), dismiss (restores hidden content), warn (24-hour posting pause), suspend for N days, ban, and erase (type the display name to confirm). Moderation actions refresh the target from the database first, because reports may have changed it since it was loaded.
127. The moderation log (now `core.AuditLog`, decision 140) is append-only in three places: the model refuses save-after-create and delete, its queryset refuses update and delete, and the admin has no add, change or delete permission. A member's deletion only clears the actor or target link; the labels stay.
128. Reporters never receive notifications about outcomes. Authors are told about removals, warnings, suspensions and approvals in-app. A ban sends no notification, because the person can no longer see the feed.

### Media and leak deterrence

129. **(privacy)** The watermark is a faint (about 13 percent opacity), diagonal, tiled overlay of the viewer's display name and the date, rendered with Pillow on every image a viewer is served. It deters leaks and identifies the leaker; it does not prevent screenshots. Watermarked variants are cached per viewer, image and day for 10 minutes in a file-based cache on private disk, not in Redis, which also carries the task queue.
130. Feed images block the context menu, dragging and the iOS long-press callout, and there are no download buttons. This is a deterrent only. There is no service worker.
131. The members area is a separate lazy-loaded bundle, so public visitors never download its code.

### Erasure and export

132. **(privacy)** Leave and erase hides everything at once (it opts the member out), then the worker deletes posts, image files, comments, likes, follows in both directions, blocks and mutes they created, notifications to and from them, guideline acceptances and exports, and clears the avatar and bio. Reports they filed and moderation records stay. The account itself stays. Confirmation means typing the display name exactly, case included. A neutral "Your request is complete" email follows.
133. Exports contain `data.json` (profile, posts, comments, likes with post ids) and the stripped images. Only a hash of the token is stored, the worker mints the token (so it never passes through the queue), and the link sits in the URL fragment. The download is single-use (marked used on first claim), expires after 24 hours, and an hourly beat task deletes used and expired files. Only one export can be pending at a time.

### Seed

134. The feed seed runs only with `DEBUG` on. Demo feed accounts get random passwords. Only `demo.member@example.org` has its password printed, so a second account is available for testing. The verified demo account is granted access but not joined, so the join flow can be tried.

## Prompt 04

### Entitlements

135. `memberships/access.py` is the single source of paid access. `entitlements(user)` is the active tier's flags plus `feed` from the staff grant. Active and grace are entitled; pending, expired, cancelled and suspended are not. `events.access.can_rsvp` and `feed.access.has_feed_entitlement` both read it, and neither has any remaining extension point.
136. **(privacy)** Members-only education is enforced in the serializer. For anyone without `members_education`, the body is `null` and the call to action is blanked, in both the list and the detail. Only the title, summary, schedule and the names of the tiers that unlock it are public. The UI's panel is just the explanation.

### Model choices

137. A month is 30 days and a year is 365 days, counted from the moment a period starts. Fixed lengths make renewals and grace predictable at the door and avoid month-end edge cases.
138. Reference codes are six characters as `XXX-XXX` from an alphabet without look-alikes (no 0, O, 1, I or L), generated with `secrets`. They identify a membership, not a person, and the door desk accepts them with or without the dash and in any case.
139. **(privacy)** `Membership.user` is nullable. Deleting an account cancels any open membership (stopping online renewals through the provider), keeps membership and payment rows for the books with the person detached, and deletes the agreement signature with the account. Financial records outliving the account is the minimum a nonprofit's accounts need; nothing in them identifies the person afterwards.
140. `feed.ModerationAction` became `core.AuditLog` with a `category` (moderation, door desk, export, private data). A data migration copies every row, keeping its time, and the reverse migration copies them back. Append-only in the model, queryset and admin, as before.
141. `Payment` is immutable the same way. A refund is a new row with `status=refunded` pointing at the original, and refunding more than what is left is refused. A refund does not change the membership's status; staff suspend or leave it as they judge.
142. `Payment.provider_payment_ref` is NULL (not blank) for in-person payments, so the uniqueness constraint on `(provider_payment_ref, status)` applies only to processor payments.
143. `created_at` on memberships and payments defaults to now but can be set, so the demo seed can create history without bypassing payment immutability.
144. Agreements are versioned. Once published, an agreement's title and body cannot be edited or deleted in the admin, so a signature always refers to the exact text signed. Joining sends the version the person read; if it changed meanwhile, they are asked to read the new one.

### Joining and payment

145. **(privacy)** An online payment from someone with no ID check on file records the payment but does not activate. The membership stays `pending_payment` with `paid_awaiting_id_check`, never expires while waiting, and the door desk's "Activate" finishes it after the check. The brief requires an ID check before first activation; this keeps that true for online payments too.
146. Activation only ever comes from a stored webhook event or a staff action. The `/join/confirming` page only polls `/api/membership/me/` (every 2 seconds, for about a minute) and says "Still confirming" if nothing has arrived.
147. Webhook events are stored before they are applied, and an event that cannot be applied (for example, no matching membership) is kept with its error and still answered with 200. The processor would otherwise retry forever an event that can never apply; staff can read it in Admin > Webhook events.
148. Joining is rate limited to 10 an hour per account. Webhooks are rate limited to 120 a minute per hashed IP, far above any processor's real rate.
149. The sandbox delivers its webhooks through a Celery task that builds a signed request and calls the real webhook view in-process, so routing, signature checking and the event service all run exactly as for a processor. Its signing secret is derived from `SECRET_KEY`. It exists only with DEBUG on and the sandbox enabled.
150. **(privacy)** Unpaid reference codes lapse after `MEMBERSHIP_PENDING_EXPIRY_DAYS` (default 30), so abandoned sign-ups do not linger as open memberships.
151. The in-person method is always offered, including next to an online processor.
152. Cancelling a pending membership ends it at once. Cancelling a running one sets `cancel_at_period_end`: access continues to the period end, then it becomes cancelled without a grace period and without reminders. Nothing is refunded automatically.
153. Auto-renew is offered only for online memberships with a subscription. Turning it back on calls the provider's `resume_subscription`, added to the interface for this.

### Door desk and reporting

154. **(privacy)** The door desk shows display name, code, tier, status, period end, whether an ID check is on file and recent payments. Never the email or the typed legal name. "Show signature name" reveals the name for that one page view and writes an audit entry; nothing about the name goes into the log itself.
155. **(privacy)** QR scanning decodes camera frames on the tablet with a vendored copy of jsQR 1.4.0 (Apache-2.0, `static/memberships/vendor/`), not a CDN. The door desk page alone sends `Permissions-Policy: camera=(self)`; the middleware now keeps a policy a view sets and applies the camera-off policy everywhere else.
156. Door desk actions need the `memberships.change_membership` permission and reporting needs `view_membership`, so a "Door desk" group can be given to volunteers without the rest of the admin. The seed creates that group and a `desk_volunteer` account in development.
157. Renew extends from the later of now and the current period end, so paying early never loses days and paying late never backdates. Reinstating sets the membership active and leaves the daily lifecycle to move it on if its period already ended.
158. A comp is recorded as a zero-amount `comp` payment with the reason as its note, so every period has a payment row, and the summary's revenue table leaves comps out.
159. **(privacy)** The CSV export contains display name, tier, status, period end and source. Contact email is added only when a superuser ticks "Include contact email", and that is logged as a separate action. Cells starting with `=`, `+`, `-` or `@` are prefixed with `'` so a spreadsheet never runs them. The export is POST-only and `no-store`.
160. Revenue in the summary is by local month and method, with refunds subtracted. "New" is a membership's first succeeded payment in the month; "renewed" is any later one.

### Lifecycle and email

161. The lifecycle runs once a day at 06:00 Chicago. Reminders go at 14 and 3 days before the period end, once each, only to active memberships that do not renew automatically and are not cancelling. Moving to grace and expiry each send one note.
162. **(privacy)** Membership email subjects are "Your reference code", "Your account is ready" and "A note about your account". Bodies use "your account" and "membership" and never name the organisation, its activities or the tier.
163. Receipts carry the merchant display name (`MERCHANT_DISPLAY_NAME`), date, amount, method, a reference (`CODE-paymentid`) and the word "Membership". Not the tier name.

### Import and development tools

164. `import_members` validates the whole file first and writes nothing if any row has a problem, so a half-imported list never needs untangling. It is a dry run unless `--commit` is given. New accounts get an unusable password and a verified email (the address came from the organisation's own records), and the invite tells them to choose a password through "Forgot password" rather than carrying a reset token, which would expire in two hours.
165. **(privacy)** Imported ID checks are recorded against an inactive `system_import` account, and an imported paid-up member with `id_checked=no` waits for the door desk like an online payment does (decision 145). Email addresses appear in the command's output only with DEBUG on; otherwise rows are referred to by line number.
166. `membership_clock --days N` (DEBUG only) moves every membership date back N days and runs the lifecycle, which is the same as the calendar moving forward. It exists for walkthroughs and manual testing.
167. Seeded tiers and the agreement are flagged `is_placeholder` (not editable in the admin). With DEBUG off they are never offered and joining is refused while the placeholder agreement is current, so placeholder prices or text can never reach production. The join page labels them "Placeholder price" and "Placeholder text".

### Frontend

168. The header's "Join" reads "Membership" for anyone with any membership, past or present (`Account.has_membership`, the caller's own only).
169. One `PaywallPanel` is used everywhere paid content is gated: locked classes, members-only RSVPs and the member community on `/account`. It picks log in and register, "Become a member" or "See my membership" from the session.
170. The QR encoder (`qrcode`) is loaded on demand, so the public bundle stays small, and every QR is made on the device.
171. The sandbox checkout page is a lazily loaded route that renders the site's 404 whenever its API is absent, which is always in production.

172. An RSVP made while a membership was active stays when the membership lapses, but it can no longer be updated, only cancelled; once cancelled, the membership panel replaces the form. The person may renew at the door, and hosts check entry there. Cancelling it automatically would release a place without telling them.
173. Receipts print on white with the header, footer and Leave control hidden.

## Prompt 05

### Hosting

174. **(privacy)** `Referrer-Policy: no-referrer` on every response except the admin, which gets `same-origin`. Django's admin forms post with an `Origin` header that `no-referrer` would turn into `null`, failing its CSRF check. `same-origin` sends nothing to any other site, so no referrer ever leaves.
175. The built React app is served by Django through WhiteNoise, and the separate static site with its `/api` and `/media` rewrites is gone from `render.yaml`. One origin with no proxy hop means one set of headers (CSP, HSTS, robots) in one place, first-party cookies without rewrite rules, one artifact to deploy and roll back, and no second service to keep in step.
176. One Docker image runs the web service, the worker and beat. Python 3.12.13 and Node 22.23.1 are pinned, and the image carries the PostgreSQL 16 client (from the PostgreSQL apt repository, matching the database version) for backups.
177. `DJANGO_ENV` (development, test, e2e, staging, production) controls HTTPS-only cookies, HSTS and the redirect, instead of `DJANGO_DEBUG`. The e2e stack runs with DEBUG off over plain HTTP, like production apart from TLS.
178. The safety checks run in Render's pre-deploy step and again whenever the web process, the worker or beat starts, so a bad setting can never serve a request or send an email. Staging gets the same checks, plus basic auth and in-person payments only.
179. `seed_demo` writes a `SeedMarker` row and refuses to run in staging or production; the marker stops those environments starting. The e2e data command runs only with `DJANGO_ENV=e2e`.
180. **(privacy)** `robots.txt` is served by Django. Indexable sites list the private paths but never the admin path, which would publish it. Indexing is on only in production (`SITE_INDEXABLE`, which a measurement run can switch on); staging is always closed.
181. `/join` is a public page and indexable; only `/join/confirming` is private.
182. `/healthz` is answered by the first middleware, before host validation, the staging gate and the HTTPS redirect, so the platform's internal checks always reach it. It says only `ok` or `unavailable`.

### Storage

183. Media uses django-storages against S3-compatible buckets, with Cloudflare R2 as the documented default (no egress fees, CDN in front of the public bucket). Staging and production never share a bucket. Uploaded public images have random names and are cached for a year; site imagery keeps fixed names and is cached for a week.
184. **(privacy)** Signed URLs also set `response-cache-control: private, no-store` and an inline disposition, so the bucket's own response is not cached either.
185. **(privacy)** Watermarked copies are rendered once per image, viewer and day and stored under `watermarks/<image key>/<viewer key>-<label key>.webp`, with every key an HMAC so names reveal nothing. Deleting an image deletes all its copies; deleting an account or erasing feed data deletes every copy carrying that person's name. This replaces the earlier 10-minute disk cache.
186. **(privacy)** Export downloads stream through Django instead of redirecting, because the download is a single-use token posted by the page; a signed bucket URL could be copied and reused within its lifetime.
187. Private storage is a lazy proxy, like Django's default storage, so model fields follow the configured backend instead of the one present at import time.
188. `migrate_media_to_storage` keeps every object name the database already stores, so no row changes. It verifies size and MD5 (from the ETag when it is a plain MD5, otherwise by reading the object back), skips identical objects, replaces different ones, leaves the old local watermark cache behind, and is a dry run unless `--commit` is given.
189. Both buckets allow CORS from the site origin only, with GET only. The app also prunes `watermarks/`, `exports/` and `backups/` itself, so a missing lifecycle rule never means data is kept for ever.
190. The official MinIO images are no longer published, so development, tests and CI use the archived `bitnamilegacy/minio:2025.4.22`. It never runs anywhere deployed: the safety checks refuse any local or plain-HTTP storage endpoint.

### Security

191. Staff two-factor uses django-otp (TOTP plus ten single-use backup codes) through a custom two-step login that replaces the admin's. Nobody is logged in until both steps pass; enrolment is forced on first login; the QR code is drawn on the server as a data URI. **(privacy)** The authenticator app shows the issuer (`OTP_ISSUER`, "Rose") and the display name, never the email. django-otp's pause after a wrong code is kept; wrong codes also count toward the 15-minute lockout shared with member login. Enrolment and backup-code use are audited, in two new audit categories: staff security and operations.
192. Sessions end through a per-account `session_epoch` mixed into Django's session hash: "Sign out everywhere" and any change to staff, superuser or active status, groups or permissions raise it. Staff sessions are browser-session cookies limited to 12 hours. Member sessions expire after 14 idle days, which means saving the session on every request; the extra write is accepted.
193. "Sign out everywhere" includes the device it is pressed on, so a lost-phone panic button cannot leave the person thinking only other devices were affected.
194. **(privacy)** The feed controls under `/api/account/feed/` now answer 404 to signed-out visitors too (they answered 403, which confirmed the endpoints exist). Found by the end-to-end privacy sweep.
195. Uploads: 15 MB, 40 megapixels, 12,000 px on a side, and JPEG, PNG, WebP or HEIC by magic bytes. GIF is no longer accepted. HEIC decodes through pillow-heif and is stored as WebP like everything else. Pillow's decompression-bomb warning is treated as a refusal.
196. Every write endpoint has a limit, applied in the shared API base classes: 120 an hour per endpoint per account (or per IP when signed out) by default; 30 an hour for account changes, RSVPs and membership and feed requests; 30 an hour per IP for token links. Specific limits (login, registration, contact, webhooks, posting) stay on top.
197. The breached-password check uses the standard library and the padded range API, fails open (accepts the password and logs only that the service was unreachable) and is off by default.
198. Logs use a small JSON formatter of our own rather than another dependency. gunicorn's access log has no client address, query string or user agent. sentry-sdk is installed but dormant unless `SENTRY_DSN` is set.
199. **(privacy)** Handled contact messages are deleted after `CONTACT_RETENTION_DAYS` (365); unhandled ones wait for staff. The audit log and the attendee export log are kept: they are the record of who saw or exported what, which an incident review needs.
200. **(privacy)** No analytics. If the club later wants traffic numbers, the acceptable shape is a server-side counter of path and day only, with no IP, user id, cookie or referrer. It is not built.
201. Email goes through django-anymail (Postmark in the blueprint; SES, Resend, Mailgun or SMTP by one setting), with open and click tracking off. anymail is installed without its `amazon-ses` extra, whose extra package capped `cryptography` below a security fix; SES needs only boto3. `send_test_email` requires `--staff` naming an active staff account and logs without the recipient.
202. Backups are encrypted on the server with pyrage (age) using only the public key, as custom-format dumps. `verify_restore` is the documented, read-only check for any restore; it rolls back anything its view calls might write.

### Build, tests and CI

203. CI has four jobs (backend, frontend, audit, end-to-end) with no secrets. MinIO runs as a service, and `REQUIRE_S3_TESTS` and `REQUIRE_PG_DUMP` turn the skips used on machines without them into failures.
204. Browser tests use Playwright with the Chrome already on the machine or runner (`channel: chrome`). Each test sends its own made-up `X-Forwarded-For` (the e2e stack trusts one proxy hop), so per-IP rate limits never bleed between tests; mail is read from Mailpit; the stack allows more logins per email because the tests reuse known accounts; one worker runs them in order.
205. Lighthouse was measured in mobile emulation against the production image, with the age gate accepted (and the gate measured on its own) and `SITE_INDEXABLE` switched on for the run.
206. Every page except home loads on demand; the two fonts used above the fold are preloaded; Vite never inlines assets as data URLs (the CSP blocks `data:` fonts, which silently broke one font file); the built files are pre-compressed with gzip and Brotli.
207. Public uploads get 640 and 1280 px copies and their size recorded, served as `srcset` with width and height. Member images get none (they are watermarked per viewer). Images stored before this change have no recorded size and are served as before.
208. Event, class and journal detail pages show a skeleton the size of their heading while loading and keep room below it, which removed a layout shift that cost the event page 25 Lighthouse points.
209. Definition lists put each icon inside its `<dt>` (a shared `DetailItem`), so every `<dt>`/`<dd>` pair is valid for screen readers; axe flagged the old markup.
210. Logging out from `/account` lands on the home page (the account page's own redirect to the login form used to win).
211. Dependabot opens grouped weekly updates per ecosystem: Python, the site, the browser tests and GitHub Actions.

### Deployment

212. The blueprint uses Render projects with two environments. Each has a settings group (values) and a secrets group (every key `sync: false`), which web, worker and beat all read, so a secret is entered once per environment. Key Value uses `noeviction` (Celery's queue lives there); beat is pinned to one instance; the pre-deploy step runs the safety checks, then migrations.
213. Staging was not deployed: the Render CLI is not installed or signed in on this machine, and the blueprint creates paid resources.
214. `ADMIN_BASE_URL` defaults to `SITE_URL`, since the admin shares the site's origin.
215. The composer and avatar pickers list the accepted formats (`image/jpeg,png,webp,heic,heif`) instead of `image/*`.
216. The CSP needs no nonce or hash: nothing inline runs. It adds `worker-src 'none'` and `manifest-src 'self'`. The Permissions-Policy denies every device feature by name and drops `interest-cohort`, which browsers no longer recognise.

### Admin dashboard

217. The admin home page shows a dashboard: a "Needs attention" list (open feed reports, first posts awaiting review, unhandled concerns, online payments waiting for an ID check, hidden images, failed payment events, an overdue backup) and cards of totals for membership, income, events, accounts, the feed, messages, images and, for superusers, the system. **(privacy)** It shows totals only, never a name, email or who did what. Each card appears only to staff holding the permission its own admin page needs; income follows the membership view permission, because the Membership summary already shows revenue to the same people. Upcoming events show places taken with a `<meter>`, so no inline style is needed under the CSP. Zero-count attention items are left out.

