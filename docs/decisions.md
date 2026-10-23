# Decisions

> **The public website follows docs/design/source (Rose Public Site). Instagram-style design applies ONLY to /members/* for entitled users. A request to make anything 'look like Instagram' refers to the member app only. Never restyle public pages toward Instagram.**

> **The public Events page uses a 3-column image card grid (15 per page), at the owner's request. This overrides the list layout in Rose Public Site.dc.html for the Events page only.**

Choices made where the brief did not specify. Privacy-over-convenience calls are marked **(privacy)**.

Prompt 01 decisions come first (1 to 47); prompt 02 and its review addendum follow (48 to 99), then prompt 03 (100 to 134), prompt 04 (135 to 173), prompt 05 and its follow-ups (174 to 227), prompt 06 (228 to 284), prompt 07 and 07b (285 to 331) and prompt 08 (332 onwards).

**Prompt 07:** the member area under `/members/*` uses an Instagram-style app shell and design. The public website keeps its prompt 01–06 layout and structure, with a lighter palette. Where an earlier doc conflicts with prompt 07 on member-area layout or on colors, prompt 07 wins.

**Prompt 08:** the designs in `docs/design/` replace every earlier visual spec, for the website and the member app alike. The privacy, access and security rules in `docs/architecture.md` still win over the designs; each conflict is recorded below.

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

### Staff admin look

218. The staff admin takes the layout and feel of a photo-sharing app, as asked: a fixed left sidebar with outline icons and plain labels (Home, Door desk, Messages, Notifications, Create, Events, Moderation, Images, Dashboard, All sections), red count badges and a red notification dot, the current page in bold, a light or dark palette, the system font, and post-style cards in one centred column. **Settings** (gear) is at the bottom left, opening a menu upwards with site settings, password, appearance, the public site and log out. It keeps the site's own "Rose" name; no other company's logo, name or wordmark is used. Django's own sidebar is switched off.
219. The sidebar stays on the left at every width (an icon rail on tablets and phones), as asked, rather than moving to a bottom tab bar on phones.
220. Items and badges follow permissions: a door volunteer sees Home, Door desk, Notifications, Images, Dashboard and All sections; badges are counts only. "Recent actions" becomes the last card in the home column.

### Members area look

221. Only the logged-in members area (`/members/*`) takes the photo-app look. The public website and the account page keep the site's own design. An earlier attempt restyled every page; it was reverted at the owner's request.
222. The look is scoped through CSS variables on an `.ig-app` root, not separate components. Colours, fonts and corner shapes are tokens, and `.ig-app` redefines them, so the public site renders exactly as before. Three corner tokens (`--radius-control`, `--radius-card`, `--radius-field`) were added for this; their public values equal the old classes.
223. The sidebar stays on the left at every width (a rail on tablets and phones), like the staff admin and as asked for there, rather than a bottom tab bar on phones. Leave stays near the top of it on every page. **(privacy)** The Settings menu also ends with "Leave this site now".
224. Blue is #0067d1 and red is #d61f3a (light) or #ff3040 (dark), chosen to pass WCAG AA contrast, instead of copying any app's exact colours. Muted text is 4.74:1 in light and 8.83:1 in dark; input borders are 3.26:1. The "Rose" name is set in a script typeface; no other company's logo, name or wordmark is used.
225. The appearance choice (automatic, light or dark) is a per-browser convenience in localStorage, guarded for private windows and never sent to the server.
226. The loading state and the no-access 404 keep the public look. **(privacy)** Someone without feed access must not be able to tell the members area exists.
227. The composer's sidebar button reads "Create" (its tooltip says "New post"); the old floating button is gone.

## Prompt 06

### Guests

228. A guest night pass is a `Tier` with `is_guest_pass`, and `Tier.clean()` holds it to the brief: a one-time pass lasting exactly 1 day with all three entitlement flags off. No separate guest model.
229. **(privacy)** Guest passes are paid at the door only. Joining with a guest tier and an online method is refused, and the join page offers only the in-person method for it, so a guest never meets a payment processor.
230. A returning guest's earlier pass (expired after the night) is opened again by **Guest visit**, so they keep their account, their reference code and their ID check. A guest who signs up again instead gets a new code, and their ID check still carries over (`has_id_check` looks at the person, not the pass).
231. A guest pass simply ends at the end of its day: the daily lifecycle moves it straight to expired, with no grace period, no email and no renewal reminders.
232. **(privacy)** "Convert to member" on the door desk shows a QR code for `/join`, which the guest opens on their own phone in their own account. They read and sign the agreement themselves, so their typed name never passes through a staff tablet. Joining a membership closes an open guest pass (cancelled if unpaid, expired if it was running); the ID check carries over, so the desk can activate straight away.
233. The Membership summary leaves guest passes out of the membership counts (status, tier, new, renewed, expired) but keeps their payments in revenue. Guest visits by month count successful guest-pass payments, one per evening.
234. The guest tier never appears among the memberships on `/join`. `/join?tier=<slug>` preselects a tier; the Guests page uses it to go straight to the agreement.

### Rentals

235. The time, length and party size are required by the form but nullable in the model, so the retention purge can clear them.
236. A clash is any overlap between the requested time and a published event or another booking's private hold, on either the first or the second choice. Without a start time the whole day counts. Unpublished events do not count.
237. **(privacy)** The calendar placeholder is an `Event` with a new `is_private_hold` flag: `save()` forces it unpublished, `clean()` refuses publishing it, and `published()` excludes holds, so no list, calendar, detail, ICS or journal link can ever show it. It is removed when the inquiry is declined, cancelled or moved off confirmed.
238. Status is read-only on the inquiry form. It changes only through the pipeline actions, the status form on the inquiry page and the confirm page, and each change writes an audit entry with the old and new status. Other edits are audited by field name only, never their values.
239. **(privacy)** The requester gets a neutral "We received your request"; staff get "New request received" with an admin link and nothing about who asked or what for, like contact messages.
240. **(privacy)** Retention: declined and cancelled inquiries keep only type, date and status `RENTAL_RETENTION_DAYS` (90) after they closed. Inquiries never concluded (new, in discussion, quoted) are treated the same 90 days after their last requested date. Confirmed bookings are kept as the record of the booking.
241. Deleting an account strips the contact details from that person's inquiries. A confirmed booking keeps its calendar hold, because the room is still booked.

### Volunteers

242. Interests and availability are JSON lists of choice keys; the admin filters use `contains`.
243. Sign-ups get a neutral "Thank you for your note" and staff a content-free "New note received". Rate limited to 5 an hour per IP, with the same honeypot as contact.
244. **(privacy)** Sign-ups that went nowhere (new or inactive, untouched for `VOLUNTEER_RETENTION_DAYS`, 365) are deleted; active volunteers are kept. Deleting an account deletes that person's sign-ups.
245. **(privacy)** The form does not ask for a reference check, which the old form did. Coordinators ask for one when they reply, so the site never stores references for people who never volunteer.

### Donations

246. `Donation` is append-only exactly like `Payment`: failed attempts and refunds are new rows. An online gift is recorded only when the provider's webhook confirms it; until then it is a short-lived `DonationCheckout`, deleted after 7 days.
247. **(privacy)** A gift is linked to an account only when a signed-in donor ticks "show my display name". Otherwise it is "Anonymous" with no account link at all. Donors are never listed anywhere public.
248. **(privacy)** An address for an acknowledgement is kept apart from the gift (`Acknowledgement`) and cleared the moment it is sent; an unsent one is cleared after 30 days. Acknowledgements go out automatically after an online or desk gift when wording exists; otherwise staff print or send them later. The subject comes from the wording, "Thank you for your gift" by default.
249. **(privacy)** The legal name and EIN are staff-only site settings, used only on acknowledgements. The nonprofit line, who checks are payable to and the mailing address are public, on the Donate page.
250. Recording a gift needs the door desk permission, so door volunteers can take cash, card or a check without wider admin access. It is audited in a new Donations category.
251. Online giving appears whenever an online provider is configured (in practice a real processor, or the sandbox in development). Gifts are $5 to $10,000 online; presets are $25, $50, $100 and $250. The maximum keeps unusually large gifts as a conversation.
252. One-time payments use a new `create_one_time_checkout(amount_cents, purpose, success_url, cancel_url)` on the provider interface. `purpose` ("donation:DON-XXXXXX") travels to the processor and back on `ProviderEvent.purpose`, and the existing event service routes it through a small registry (`PURPOSE_HANDLERS`) after storing and deduplicating it as usual.
253. The sandbox provider may run in the end-to-end stack (`DJANGO_ENV=e2e`) as well as with DEBUG on, so the browser tests can pay online. That environment is never deployed, and the deployment checks still refuse the sandbox in staging and production.

### Email list

254. **(privacy)** Each subscriber's token is stored as is, because every newsletter needs it to build that person's unsubscribe link. Page links carry it in the URL fragment; the RFC 8058 one-click address must carry it in the path, so the log scrubber removes it there. A token only confirms or unsubscribes one address.
255. Signing up again with a confirmed address sends nothing; a pending or unsubscribed address gets a fresh confirmation with a new token. The answer on screen is identical in every case, and sign-ups are limited per IP and per (hashed) address.
256. **(privacy)** Sign-ups never confirmed are deleted after 7 days.
257. **(privacy)** Suppression records are a salted hash of the address and the date. Confirming a new sign-up removes an old suppression, because that is a fresh opt-in; sending always skips suppressed addresses as well.
258. Newsletters are draft, scheduled or sent, with a `send_started_at` lock so one can never go out twice. **Send** schedules it for now and queues the worker; a beat task every 5 minutes starts scheduled ones.
259. Sending uses batches of 100 per connection, one message per person (each has its own unsubscribe link and headers).
260. **(privacy)** Staff cannot add subscribers in the admin: everyone on the list confirmed it themselves. Staff can unsubscribe or delete people, which is audited.

### Staff, page copy and content

261. `StaffProfile` lives in the pages app and uses the consent image pattern. The optional account link is staff-only and never serialized.
262. `PageContent` holds one value per page and dotted key (`hero.title`, `steps.1.body`), plain or formatted (sanitised like event bodies). Lists are numbered keys. `/api/content/<page>/` is read-only, cached on the server until a value changes, and sent with `Cache-Control: public, max-age=60`.
263. What moved out of React: headings, ledes, paragraphs and list items on public pages. Interface text stays in code: button and link labels, form labels and validation, status and error messages, empty states, and page titles and descriptions for the browser. While copy loads, pages show skeletons, never stand-in text.
264. The placeholder copy that used to be written into React now lives in `backend/apps/pages/demo_content/` (marked "placeholder - development only"), loaded by `seed_demo` and `e2e_fixtures`. It is development data, not a fallback; production shows the club's own copy.
265. **(privacy)** `/content` is gitignored like `prompts/`, and kept out of the Docker image, because it names the organisation. Only `content/redirects.yaml` is committed: it holds paths only, and the tests check every mapping. Production loads the copy by uploading the files on a superuser-only admin page (Page copy > Load site content), which runs the same loader with the same draft guard and audit entries.
266. The loader matches rows by slug (or page and key, or old path), never deletes, validates only the fields a file sets, and writes nothing unless every file loads. Every committed load is audited; loading drafts in production also writes a separate audit entry.
267. Tier entries change the price only when one is given; a tier that does not exist yet needs a name, an interval and a price.
268. `FAQItem` gained an optional unique `slug` so the loader can update questions in place.
269. FAQ moved to its own `/faq` page (the old site had one), and Plan Your Visit links to it. A new `/house-rules` page carries the rules that were PDFs on the old site; Guests and Visit link to it.

### Redirects

270. `/gallery` goes to `/journal` from a built-in rule, so it works whether or not the redirect table is loaded, and the single-page app redirects it too.
271. `Redirect` rows are matched case-insensitively without a trailing slash; an old path ending in `/*` covers everything under it (the old site's 755 event pages, bookings and services). Redirects never apply to the API, the admin, media or static files. Old PDFs map to the pages that replace them.
272. Not mapped, so they reach the normal not-found page: the empty shop, Wix system and template pages, the members' login pages, and paths that are the same on both sites.

### Navigation and footer

273. Dropdowns use the disclosure pattern (a button that shows a list of links), not an ARIA menu, which suits site navigation better. Arrow keys, Home and End move through the links; Escape closes and returns focus; leaving with Tab or a click outside closes. The phone menu shows the same groups as headed sections.
274. **(privacy)** The footer's staff guide link comes from a new self-only `staff_guide_url` on the signed-in session, set only for staff, so the admin's address never reaches anyone else's browser. The guide is `docs/staff-guide.md`, rendered (and sanitised) on an admin page behind the staff login.
275. The footer's nonprofit line comes from site settings instead of the code. Its email sign-up avoids the word "email" in its labels so it is not confused with a form's own Email field by assistive technology and tests.

### Content migration

276. **(privacy)** The old site publishes its street address and a phone number. The draft keeps the address (the club decides whether to keep "shared with confirmed visitors", decision 9) and leaves the phone out, because the old site shows two different numbers.
277. **(privacy)** Consent-violation and grievance reports went to Google Forms on the old site. The new site takes them through its own contact form ("Report a concern"), which is private and sends staff no content by email; the forms are not linked.
278. Tiers carried over: Rose, Rose +, Limited, Limited + and Trial at the published prices, plus a $15 guest night pass from the old guest plan. Not carried over: Community and First Fridays (free; open evenings need only a free account here), Single Event (only on a hidden plans page) and Staff (comped at the desk). The one-event-a-month limit of the Limited plans is kept by door staff, not the site.
279. **(privacy)** The old staff page names nobody; names came only from a 2024 newsletter. They load unpublished, with no bios, until staff confirm them.
280. Old images are listed in `docs/image-sources.txt`, every line commented out, with page and alt context. Images from Wix's stock library are marked as licensed for Wix sites only.

### Other

281. **(privacy)** `/subscribe` and `/unsubscribe` carry `noindex` and are disallowed in `robots.txt`, like the other token pages.
282. `AuditLog` gained Rentals, Donations, Volunteers, Email list and Site content categories.
283. The new admin pages share one stylesheet (`core/staff-tools.css`); printing an acknowledgement uses a static script, so the strict CSP stays unchanged.
284. Forms that start from the signed-in name and email (rentals, volunteering) render once the session is known and take their first values from it, rather than copying it in an effect.

## Prompt 07

### Branch and scope

285. Prompt 07 is built on a branch (`member-app`) started from prompt 06's `feature-parity`, because prompt 07 restyles prompt 06's pages and header; `main` stays as it was until both are merged.
286. Prompt 07 replaces decisions 221 to 227 where they conflict: the member app now has a top bar and bottom tabs on phones (not a left rail), light by default (not following the device), the rose accent (not blue) and the shared palette (not a separate scoped one). Scoping by `.ig-app` remains, for type, sizes and corners only.

### Palette and appearance

287. Rose text (links, eyebrows, active labels) uses the 8%-darker `#CE2156`, because the accent `#E0245E` is 4.39:1 on `#FAFAFA`. `#E0245E` is used for buttons (white text 4.58:1), the liked heart and unseen story rings.
288. Error text is `#C62A3A` (5.54:1); `#ED4956` (3.69:1 as text) marks invalid fields and error icons only (`error-mark`).
289. Form field and ghost button outlines use `#8E8E8E` (3.28:1, the non-text minimum); dividers use `#DBDBDB`.
290. Dark is neutral: canvas `#0C0C0C`, surfaces `#161616` and `#1F1F1F`, text `#F5F5F5` and `#A8A8A8`, rose text `#FF5C8A`, and the wordmark lightens to `#D4848F` (the oxblood is 1.5:1 on near-black).
291. Appearance is stored on the account (`User.appearance`, light or dark, default light) and changed through `PATCH /api/account/session/`, which now takes `display_name`, `appearance` or both. **(privacy)** A first-party `appearance` cookie (one year, SameSite=Lax) holds only "light" or "dark". It is read before the first paint, so no request is needed. After sign-in the account's choice wins and is written back to the cookie, so the next visitor on a shared device sees the last choice, and nothing else. The cookie is not HttpOnly because the page must read it before any request.
292. Appearance can be changed from the website account page, the app's Settings page and the More menu (a switch).
293. Placeholder textures are rebuilt from the palette variables, so they read as soft rose and neutral washes in light and dark; the scrims over hero images are stronger (`via-canvas/85`, `to-canvas/40` to `/50`) so text stays readable on any photograph in light.
294. The website wordmark ("R" mark and "Rose") uses the oxblood `wordmark` colour, as the brief asks; Fraunces stays the website's display face.
295. Dark scrims and controls over photographs (`ink-950`, `cream-100`, white) are fixed colours, unchanged by appearance.

### App shell

296. Search and Notifications open as 397px panels wherever the sidebar exists (768px and up), not only from 1264px; the sidebar collapses to its rail while a panel is open.
297. The post modal is opened with `?post=<id>` on the current page, so the page stays underneath without a second set of routes; `/members/p/:id` is a page at every width (phones always go there). The arrow keys ignore keystrokes inside text fields and inside the photo carousel, which uses them for its own images.
298. The quick exit is the sidebar's last item ("Leave") and the phone top bar's `LogOut` icon; double-Esc works everywhere as before.
299. **(privacy)** The right rail has no suggestions, and own profiles show no "Following" list link: building one would need a new endpoint, and follows stay private and unlisted.
300. The loading state and the no-access 404 keep the website's look, as before, so nobody without access learns the app exists.

### Feed, posts and stories

301. Journal posts join the home feed on the server (`GET /api/members/home/`), interleaved by date with member posts; `/api/members/feed/` is unchanged and still powers Explore. They appear in both tabs. **(privacy)** The cursor holds timestamps plus public ids or slugs, never database ids.
302. Club posts cannot be liked, commented on, saved or reported; their action row is the website link (RSVP for an event, the post's own button, or "Read on the website").
303. Double-tap and double-click only ever like (never unlike), and do nothing on club posts or while a post is blurred.
304. Posts now carry `recent_comments` (the two newest the viewer may see), `saved_by_me`, and image `width` and `height`; profiles carry `post_count` (posts the viewer can see). Image sizes are recorded after processing; older images without sizes show square.
305. Stories: Tonight (visible events starting before local midnight), This week (the next seven days after today), Journal (posts from the last 14 days) and News (announcements between their start and end), up to six items each; empty circles are hidden. A circle counts as seen once every item in it is seen. **(privacy)** Stories are the same for every member whether or not they RSVPed; a test checks it.
306. Announcements are a new staff model (`feed.Announcement`: title, 280-character text, optional link, start, end, published), text only, so no image consent is involved.
307. `StorySeen` rows record which story items a member opened. They are erased with "Leave and erase" and included in the export.
308. Saved posts (`SavedPost`) are private to the saver: only `saved_by_me` and `/api/members/saved/` mention them, both for the caller only. Only published posts can be saved. A post that is hidden by a report or removed leaves every saved list for good (even if later reinstated). Saves of posts by people who stepped away or blocked you are hidden, not deleted. Saves are erased with the saver's feed data, and with the post when it is erased. They are included in the export.
309. Explore shows Everyone posts as a grid (muted members excluded, as in the feed).

### Screens

310. The Create flow's Share step is a summary (first photo, caption, settings) with the Share button; the attestation is on Details, and Share stays disabled until it is ticked.
311. Profile settings are split: Edit profile (picture and bio) is a dialog; the toggles and the Blocked list live on the Settings page. "Hide me from the member directory" reads "Show me in search" there.
312. `/members/directory` redirects to `/members/search`; `/members/saved` redirects to your own profile's Saved tab.
313. The old member-area layout and components (`MembersLayout`, `MembersSidebar`, `OverflowMenu`, `PostList`, the old `PostCard` and `Composer`, `DirectoryPage`, the scoped appearance helper) and the website `Button`'s unused `secondary` variant are removed.

### Verification

314. Screenshots come from `e2e/tests/09-screenshots.spec.ts` at 390x844 and 1440x900 (the desktop test widens its window). `e2e_fixtures` adds a showcase data set for them: four members with generated gradient photos, likes, comments, saves, two journal posts, an announcement, and events tonight and this week.
315. Lighthouse for the member feed is measured signed in, by passing the session cookie to Lighthouse.
316. Full-screen layers that cover the app's own quick exit (the story viewer, Create on phones, and the post modal) carry their own Leave icon, so the quick exit stays visible on every screen.
317. The website's full-screen phone menu now scrolls within its own background. Prompt 06's longer menu could overflow it, and "My feed" landed on the dimmed page behind.
318. Tinted callouts on the website (Visit, Join, Contact, Rentals, the account page's email banner) sit on the canvas colour with their rose border, because `#737373` text fails AA on any tint. This changes colour only.
319. Only the first post's first photo loads eagerly, at high priority; every other photo waits until it is near the screen.
320. A direct visit to `/members/feed` starts the access check and the first page of the feed together, from `main.tsx`, once the age-gate cookie exists. Someone without access gets the same 404 as for any member path. The served page also preconnects to the storage origins (`MEDIA_ORIGINS`).
321. **(privacy)** Lighthouse on the member feed: accessibility 100, best practices 100, performance 86 to 90, SEO 66. SEO is low because every member page is `noindex`, which the privacy rules require. Performance stays below 90 under Lighthouse's simulated mobile network because the first photo sits behind the access-checked media view and its 60-second signed redirect to storage, which the privacy rules also require. A test also showed that dropping the website font preloads on member pages made no difference, so that change was not kept.
322. The screenshot spec also runs axe on every screen it captures, including the post modal, the story viewer and each Create step. It found unnamed avatar links beside comment authors' names; those are now hidden from the tab order and from screen readers, since the name link beside them goes to the same profile.
323. "View all N comments" and "more" are at least 24px tall (WCAG 2.2 target size).

### Prompt 07b

324. **Cause of the empty journal strip:** each tile's loading background was `surface-raised`, which became white in the light palette. A tile whose picture had not loaded yet, including lazy tiles below the fold, was therefore a white square on a white page. The full-page screenshots were also taken before lazy images loaded. Now `ImageFrame` always keeps its placeholder texture under the picture, and the screenshot specs scroll the page and wait for every image before a full-page capture. The strip moved into its own `JournalStrip` component with tests for posts, the placeholder and the empty state.
325. The watermark's strength is `FEED_WATERMARK_OPACITY` (default 0.06) and its spacing is `FEED_WATERMARK_SPACING`, the gap between marks as a share of the image width (default 0.34, about three marks across at any size). Rows are spaced about as far apart as the marks. The label is sized to fill most of each gap, about 16px on a 720px image. Each mark is light text with a dark outline at that opacity, so it shows on light and dark pictures once contrast is raised. Values outside 0–1 (opacity) or 0.1–1 (spacing) stop the server from starting.
326. Stored watermarked copies include the watermark style in their name, so changing either setting renders fresh copies rather than serving old ones. They stay in the same per-image folder, so deleting an image still finds them all.
327. Sample pictures for `seed_demo`, the feed demo and the e2e fixtures are drawn with Pillow (`sample_image(index)`). There are six light kinds: daylight, flowers, linen, paper, a bright room, and candles on a light table. They come in three shapes (1:1, 4:5, 1.91:1), and palette and layout vary with the index, so every index gives a different picture. Each has matching alt text, and its real size is recorded. The e2e showcase now has 12 posts with 16 different pictures. Existing pictures in a development database are not replaced. To get the new ones, re-seed a fresh database.
328. On phones the profile header is one CSS grid whose areas rearrange: avatar and post count, then name, then bio and join date, then the buttons in equal columns. Another member's profile gets Follow and Mute in equal columns plus the options button. The same elements serve the desktop layout, so no part is duplicated.
329. Story circles are 64px (ring included) on phones and 66px from 768px. The tray is a fixed 100px (102px) tall, with no margin, so the tabs sit 8px under the labels and the loading placeholder takes the same space.
330. On the website the Leave control sits in the header at every width (after the account menu on desktop), and the floating desktop pill is gone. The floating variant remains only where there is no header: the age gate and the member app's loading screen.
331. The screenshot helpers moved to `e2e/tests/screenshots.ts`. They no longer wait for "network idle", which never came on a slow machine; they wait for the page load, fonts and every on-screen image.

## Prompt 08

### Sources and tools

332. The design files moved unchanged to `docs/design/source/`; they link to each other by file name, so no links needed fixing. `e2e/scripts/capture-design-reference.mjs` serves that folder on a local port (the files load each other with `fetch`, which `file://` refuses) and screenshots every `data-screen-label` element, the whole design-system page and the post card into `docs/design/reference/`, named `<file>--<label>.png`.
333. `e2e/scripts/design-sweep.mjs` checks every website and member route and every designed state (age gate, month view, contact error and success, the three join steps, the post modal, stories, the panels, each Create step, dark) at 390×844 and 1440×900. It records console errors, failed and third-party requests, sideways overflow, a covered or missing Leave control, missing styles and serious or critical axe findings, follows every internal link it saw and submits the public forms. It runs against a local stack loaded with `seed_demo`; it creates one verified account for the join flow and deletes the post Create shares. For many runs an hour, the local server was started with higher login and contact rate limits through environment variables; nothing in the settings changed. `scripts/design_compare.py` writes the design / built side-by-sides.

### Functional breaks found first (gap report)

334. Development served journal pictures from the backend's port, which the browser refused as cross-origin: Vite's proxy shorthand turns on `changeOrigin`. The `/api` and `/media` proxies now keep the browser's Host.
335. **(privacy)** `/members/*` without access rendered a bare 404 with no Leave control. It now renders inside `SiteFrame`, the website's own header, main area and footer, so it is the site's ordinary 404 with the quick exit.
336. Blurred sensitive photos were `aria-hidden` while still focusable; they are `inert` until View.
337. The account page asked the feed for controls that answer 404 to anyone without feed access. The session payload gained `feed_controls` (entitled, or with feed history), and the page asks only then. It tells the person nothing new about themselves and nothing about anyone else.

### Tokens and type

338. The palette is the design's, with these dark values where the designs give none: blush `#1A1416`, waitlist `#2B2210` / `#F5C76B`, error `#F87171` (7.2:1), tint `#2A1218` / `#F1A6BD` (from the dark rail), field and control `#262626`. Rose fills stay `#CE2156` in dark (white on it is 5.2:1); rose text becomes `#E0527D` (5.4:1).
339. Tailwind's default colour palette is switched off (`--color-*: initial`), so only the design's colours can be used. The old texture placeholders, film grain and scroll-reveal motion are removed; a missing or loading picture shows the design's striped wash.
340. Two colours differ from the drawings for contrast: muted text on blush or tint uses `#6B6B6B` (the drawn `#737373` measures 4.45:1 on `#FAF7F8`), and the member app's 11px footer links use `#737373` rather than `#A3A3A3` (2.5:1). `#A3A3A3` is kept for disabled text only.
341. Fonts stay self-hosted (`@fontsource-variable`: Fraunces with its optical-size axis and italic, Manrope). A `font-serif` token keeps Fraunces for the wordmark and the club's name inside the app, where `font-display` is the system face.
342. `cn()` now merges classes with `tailwind-merge` (a new, bundled dependency), with the design's text sizes, corners and shadows registered. Before, a `className` could not reliably override a component's own size, spacing or display: the category chip on phone event cards showed when it should have been hidden.
343. Event times read "7:00–9:00 PM" and "9:00 PM–1:00 AM", as drawn.

### Website

344. The header is 72px and stays at the top of the page (it no longer floats transparent over the hero). Join is a rose pill (Membership for anyone with a membership), "My feed" a rose link for entitled members. The full navigation needs 1280px; below that the phone header (wordmark, Leave, menu) is used.
345. The home page has the full footer from the Home design (address and email, the email list, Privacy and Leave); other pages have the one-row footer from the Events and Contact designs. The footer's link columns are gone: every page is still in the header menus, and About links to the staff page. The nonprofit and "Adults 18+" lines are dropped from the footer, as drawn; the staff guide link remains for staff.
346. The age gate uses the design's card and copy. Its Leave button goes to the neutral `/exit` page and replaces the history entry (what "I am under 18" did); double Escape still works there.
347. `/join` has its own quiet header, as drawn: the wordmark, the three steps (filled in by the join page through a portal) and Leave, with no site navigation.
348. The RSVP panel is the design's: "RSVP" with a status badge, a party-size stepper, the note to hosts behind "Add a note for the hosts", the main button, the calendar file (offered when open and when going, discreet by default) and a short note; going and waitlisted show "Change or cancel". The five-state row under the design's event page is a design-system illustration and is not rendered.
349. **(privacy)** Badges show the state only ("Open", "Waitlist"), not the drawn "Open · 14 spots" or "Waitlist · 6 ahead": spaces left and waitlist length reveal how many people are coming, which is shown only when an event opts in (`show_attendee_count`, as "N going").
350. The paywall is the design's blush panel with Join and Log in (Join alone when signed in, "See my membership" for members); members-only RSVP says "Join to RSVP".
351. **(privacy)** "Save to wallet" on the join confirmation is not built: a wallet pass would carry the club's name onto the lock screen and to Apple or Google. "Go to my account" (or "Open the member app" when the app opens for them) takes its place. The confirmation greets people by display name, never the typed legal name, and claims only what is true ("We have emailed you this code too").
352. Contact keeps the phone field, honeypot and priority topic; the success panel uses only what the visitor typed (their name and email) and drops the design's "call the door line in your RSVP", which RSVPs do not carry.
353. Copy the designs write as interface text (button labels, tab names, form labels, "This week", "Learn with us") is in the components; headlines and prose remain staff-editable page copy, whose development values in `demo_content/*.yaml` now read like the designs. The `eyebrow` keys are no longer shown.

### Member app

354. **(privacy)** Every phone screen keeps the quick exit as the last icon in its top bar, although several phone designs (post, notifications, settings, explore, search, another member's profile) leave it out; the post modal, story viewer and Create keep their own Leave icon.
355. Each app page renders its own 44px phone bar (the designs give each screen a different one); the shell no longer draws a shared one.
356. Sidebar rows are 48px with 76px between them, as the design renders them; Leave is muted grey, as drawn, not red.
357. The post card follows `Post Card.dc.html`: full-bleed media, dots under the picture, icons 16px apart. Club posts keep their website link in the action row, without likes, comments or saves (decision 302). The design's on-screen watermark overlay is not drawn, because every member photo already carries the server's viewer watermark.
358. Members without a picture get a soft wash chosen by their handle, as the design's avatars are drawn, rather than an initial.
359. The post menu follows the design: Report to hosts, Hide this post, Mute, Save, Go to post, Cancel. Block stays in it (a safety control the design leaves out). There is no Share, Send or Copy link.
360. **(privacy)** "Hide this post" is built: a `HiddenPost` row, private to the person hiding it, removes the post from their own feed and Explore only. The author is never told, nothing counts it, the post can still be opened directly, and the rows are exported and erased with the hider's feed data.
361. Notifications show the post's picture and, for comments, the commenter's avatar. **(privacy)** Likes stay grouped and nameless.
362. **(privacy)** Search shows no "Recent" list: remembering who someone looked up would reveal it to anyone else on a shared device.
363. The page behind an open Search or Notifications panel fades under a half-transparent layer, as drawn; fading the page itself made its text fail contrast checks.
364. The feed still opens on Everyone, not Following as drawn, so a new member's first screen is not empty.
365. Settings is one list of rows as drawn. Its words stay true: "Leave and erase" deletes everything shared in the feed (the account stays), "Step away" pauses the feed profile, and "Hide me from the member directory" is the existing directory setting. Appearance opens a Light / Dark chooser; the Blocked list and the website account link stay below.
366. Create shares from Details (the review step is gone) and then shows "Post shared", whose text follows the real state: in review for first posts, still being prepared, or in the feed now. Block (solid cover) stays the default redaction tool because it is the safest; changing the crop carries cover-ups into the new frame.

### Widths

367. Tablets (768–1263px): the website uses the phone layouts below 1024px with two-column card grids from 640px, and the phone header below 1280px; the member app shows its 72px icon rail from 768px and the labelled sidebar from 1264px, with the right rail from 1160px.


### Verification

368. Results at the end of prompt 08: backend 952 tests; frontend 128 tests, type check, oxlint and build clean; Playwright 117 passed (1 skipped: the post modal on phones); the design sweep reports 108 captures with no console errors, failed or third-party requests, sideways overflow or serious or critical axe findings, and the Leave control on every page. Lighthouse (mobile, production build in the e2e stack): Home 97 / 100 / 100, Events 96 / 100 / 100, Visit 96 / 100 / 100 and the member feed 93 / 100 / 100 for performance, accessibility and best practices. SEO is 63 on all four only because that environment's `robots.txt` closes the whole site to crawlers (`SITE_INDEXABLE` is off outside production; member pages are `noindex` in every environment); every other SEO audit passes.

### After prompt 08

369. At the owner's request the home page hero sits on a pastel "Aurora" gradient (violet, butter, pink and sky washes over a lavender-to-blush base), a step away from the design file's white hero. It is a class in `index.css` drawn by `GradientBackground`, not an inline style, and a dimmed version applies in the dark appearance. On it the lead is in the text colour: the muted grey measures as low as 2.7:1 on the violet and pink washes.

## Prompt 09

### Navigation and pages

370. "Membership" takes Journal's place in the header, on desktop and in the phone menu, for everyone. Journal moves to the footer beside Membership and Privacy; its pages, the home page strip and the feed's club posts are unchanged.
371. The "Join" button stays, reads "Join" for everyone (it no longer turns into "Membership" for members, since Membership is now in the navigation beside it) and opens `/membership`. Other general join links (Become a Member on the home page, Join to RSVP, the paywall's Join, the account's Become a member and Join again) also go to `/membership`; `/join` is the flow behind each plan's Choose button.
372. `/membership` is a page of its own, so the old site's `/membership → /join` redirect is removed from `redirects.yaml`, and a data migration deletes that row from any database that loaded it (it would otherwise hide the page). The old plan pages (`/plans-pricing`, `/first-friday`, `/community-membership` and the others) and the old membership form PDF now redirect to `/membership`.
373. The membership page has no design of its own. The cards are Join step 1's, extracted into `TierCard` and now used by both pages, so Join step 1 also shows the featured tier with the rose border and a "Most popular" tag. Rows: four to a row from 1264px (the 1264px `wide` breakpoint), two from 768px, one on phones. The compare table appears from 1024px; below that each tier gets its own short list, so nothing scrolls sideways. The member's own card says "Your plan" (in place of "Most popular" when it is Rose) and its button is "Manage".
374. A signed-out visitor who chooses a plan goes to `/join?tier=<slug>`, which sends them to create an account first and brings them back to the agreement with that tier chosen.
375. The page's newsletter line ("Occasional news, never more than monthly.") labels the existing email sign-up form in the closing section.

### Tier rules

376. The tier rules (included events, events per month, guests) apply only to members-only events. Anyone with a verified account can RSVP to the other events, so a membership neither limits them nor counts them. Community and First Fridays are therefore members-only tiers limited by tag to members-only events tagged Community or First Friday.
377. A month is the calendar month of the event (Chicago time), not of the RSVP: booking in October for a November evening uses a November event. Cancelling gives back the month it took.
378. Every RSVP status change goes through one function, `memberships.usage.sync`, used by RSVPs, cancellations (including from the email link and when an account is deleted), waitlist promotions, staff edits in the admin and door desk walk-ins. Each RSVP records whether it was counted, so a cancellation only gives back an event that was taken. Changing the party size of an RSVP is not another event.
379. A member already going (or waitlisted) keeps their place when their month fills up and can still change it. A waitlisted member whose month has filled up since is passed over when a place opens, and stays on the waitlist.
380. "Any allowance the event permits" is a new event field, Guest allowance: extra guests a member may bring beyond those their tier includes. The largest party a tier allows is 1 + included guests + the event's allowance, and the event's own party size still caps it. The party size cap stays at 2.
381. Door desk walk-ins: "Check in tonight" on a running membership lists today's members-only events. It applies the same tier rules as an RSVP, uses one of the month's events and marks them checked in; someone already on the list is just checked in. Capacity is not enforced at the door (staff are there to decide). The audit entry names the membership, never the event.
382. `perks` replaces the earlier `benefits` field (renamed, data kept); the existing `description` is the card's one-line summary. A tier also has `premium_discord`, because the compare table has a Premium Discord row and every row comes from the tier.
383. Tiers are ordered by price, then `sort_order`, everywhere (the model's default ordering), and React keeps the API's order.
384. `renews` is a display and lifecycle fact. A one-time pass cannot renew. A free tier that renews (Community) stays open: the lifecycle starts a new period when one ends, with no reminder emails. Paid tiers renew as before, at the door or through an online subscription.

### Free tiers

385. Joining a free tier needs no payment method: the agreement leads straight to the reference code. The membership waits for the first-visit ID check like an online payment does (`paid_awaiting_id_check`), staff press Activate at the door desk, and no payment row is written. The account page and API call it "Waiting for ID check". Someone with an ID check already on file (an earlier membership) starts at once.
386. An unused free code lapses after `MEMBERSHIP_PENDING_EXPIRY_DAYS` like an unpaid one, and can be cancelled from the account page before it starts. A time-limited free tier (First Fridays, 7 days) simply ends at the end of its week, with no grace period and no email.

### Defaults needing the club's confirmation

387. **(needs club confirmation)** Member community (feed) access: on for Rose, Limited, Rose +, Limited + and Trial; off for Community and First Fridays.
388. **(needs club confirmation)** Events per month: Limited, Limited + and First Fridays 1; Rose, Rose +, Trial and Community unlimited (Community within its tag). Guests included: Limited + and Rose + 1, the others 0. Guest discount: Rose and Rose +. Premium Discord: Rose, Rose +, Limited and Limited +. Featured: Rose.
389. **(needs club confirmation)** Prices are inferred from the old page, which shows doubled digits ("$4040"): Community $0, First Fridays $0, Limited $20 a month, Trial $20 for two weeks, Limited + $35 a month, Rose $40 a month, Rose + $55 a month. Community is drafted as renewing (open until cancelled), Trial and First Fridays as one-time.
390. **(needs club confirmation)** The refund and cancellation wording on the page follows the old page: cancel by emailing management or through the Discord ticket feature, and a full refund if cancelled before 9 pm on the night of the first event.

### Privacy

391. **(privacy)** `MembershipUsage` stores a count per membership per month and nothing else, is not in the admin, and is deleted after 13 months by a daily task. The only figure any endpoint returns is a member's own events left this month (their membership and their RSVP state); the door desk shows it to staff.

### After prompt 09

392. The development `runserver` (`apps/core/management/commands/runserver.py`) applies unapplied migrations before it starts and again on every reload after a code change, prints a red WARNING naming any it could not apply, and warns when no membership tiers are on offer. The cause was the dev API container, which migrated only when it started: after prompt 09's models loaded through the code reloader, `/api/membership/tiers/` failed on a missing column until someone ran `migrate` by hand. `apps.core` now sits before `django.contrib.staticfiles` in `INSTALLED_APPS` so this `runserver` is the one Django uses; it still serves static files. `--skip-migrate` turns it off; nothing changes with DEBUG off.
393. `/membership` shows "Membership plans are not online yet" when no tiers are on offer, rather than an empty page; "did not load" is kept for a failed request.
394. The Plan Your Visit hero shows the owner's photograph (`photos/Plan.jpeg`), turned 90° counter-clockwise at the owner's request (a clockwise turn was tried first), which makes it a 3:2 landscape that fills the design's 3:2 frame. It was processed by `scripts/fetch_images.py` into `visit-plan.webp` (metadata stripped, 640 to 1920px wide) and recorded in the manifest with `faces_visible` false, since no face shows. As on every page hero, the picture shows from 1024px; phones show the title alone. The Guests page keeps its own placeholder. The original is not committed (`/photos/` is ignored).
395. Plan Your Visit's Directions shows "Address:" and "Phone Number:" in a small display-font heading size, then a "Directions:" label and the directions in smaller text, as the owner laid it out. The phone number is a new staff-editable site setting (`phone_text`, a tap-to-call link). The address is the existing `address_text`, so it also shows in the footer and on Contact. The club's address, phone and directions are in the gitignored draft `content/site.yaml`, not in the repository.

## Prompt 10

### Reaching the member app

396. **Root cause.** The app answered only people who had already joined the feed. Everyone else saw the site's ordinary 404 at `/members` ("This room is not on the map"): members whose tier includes the feed but who had not joined, staff (no entitlement at all), and members without it. The only way in was a "Join the member feed" link deep in `/account`; the header's account menu had no app entry. From the owner's side the app did not exist.
397. The session now says where the app stands for each person (`member_app`: open, join, paused or none). `/members` routes on it: open goes to the feed, join to joining, paused (a feed suspension or ban) to a short note pointing at the account's notices, and anyone else signed in gets a short explanation with a link to `/membership`. Signed out, `/members` is still the 404, and so is every deeper `/members` address for people without access, as before.
398. The account menu has "Member app" (and "Staff" for the team); the account page's feed card is now "Member app" with "Open the member app". After logging in with no particular page to return to (or from the home page), members whose app is open land on `/members/feed`.
399. Every staff account (`is_staff`) is entitled to the feed, so the team can always reach the app. They still join it once (accepting the guidelines) like anyone else.
400. `seed_demo` gives every demo account one password, `DEMO_PASSWORD` (default `rose-demo-only`), with DEBUG on, and prints the logins last; the README lists them. With DEBUG off the passwords stay random and nothing is printed, and `seed_demo` still refuses to run in staging or production. It also adds team accounts (moderator, staff, admin, already joined to the app), saved posts and notifications for the demo member, and sample casework.

### Staff section

401. Roles are the groups Moderator, Staff and Admin; a superuser counts as an admin. Holding a role sets the staff flag (the two-step login needs it) and taking the last role away clears it unless other groups or permissions need it. Door desk volunteers are staff without a role, so the staff section is a 404 for them.
402. The two-step requirement reuses the admin's django-otp login: an unverified team member sees "Confirm it is you", which goes to the admin login and comes straight back (the admin login now allows returning to the site's own host). Every `/api/staff/` path answers 404 without a role and a verified session, before CSRF, like the feed.
403. The staff screens live inside the member-app shell, so a team member uses the app (joined) to reach them. The phone has no menu, so Staff is a row in Settings; on tablets and desktops it is in the sidebar.
404. Reports keep their model in the feed app and gain a status (open, in review, resolved, dismissed), assignment, notes and a new type for something at an event or the club. Concerns from the website have no reporter; their optional email is used only for "received" and "reviewed" and is cleared when the report closes. The Django admin's feed moderation queue leaves concerns to the staff inbox.
405. Small numbers: any count below 5 is withheld as "fewer than 5", including 0, as the brief says. A money total is withheld when it comes from fewer than 5 payments or gifts, because a small total can point to someone. The dashboard lists tiers on offer or still with running members, events in the period and the next 60 days with their RSVP and check-in counts, the feed counts, open reports and the confirmed email list. Charts are weekly for 30 and 90 days and monthly for 12 months, and withheld periods are drawn as short hatched bars.
406. A member's staff view shows their restrictions, the number of reports about them and the actions taken, never their activity. Removing content is offered only from a report about that post or comment.
407. Actions: a warning is a notice and an email; removing content keeps the previous status so reversal restores it; suspensions take 7 or 30 days or an end date; an event suspension pauses RSVPs (new reason "restricted") and flags the door desk but leaves existing RSVPs for the door to handle; a ban cancels any open membership at once (online renewals stopped, no refund changes), releases upcoming RSVPs, closes the feed, flags "Do not admit" (the desk refuses activation, renewal, comps, guest visits and check-ins) and can block the email by a keyed hash. Reversing a ban does not restore the membership or the released places.
408. Notices and appeals live on the website at `/account/notices`, not in the app, because a suspended or banned member cannot open the app. Emails say only "An update about your account" with that link.
409. Appeals are assigned to the team member, other than the one who acted, with the fewest open appeals. The one who acted may decide only if nobody else is on the team.
410. Reporters learn "received", then "reviewed" (an in-app notice for members, an email for website concerns that left one). "Report a concern" is in the website footer, on the account page and in the app's Settings.
411. The shared `Modal` no longer lets a dialog's content shrink under its buttons when the dialog is taller than the screen; it scrolls as a whole (the action dialog showed it).
412. **(privacy)** Everything above keeps the existing rules: 404 rather than 403 for the staff API, reporter identity only through a logged admin reveal, aggregates only in the metrics and their export, discreet email, and every action and reversal in the append-only audit log.

### After prompt 10: the owner's superuser

413. **Why the superuser saw nothing.** `createsuperuser` leaves the email unconfirmed and the account outside the member app, so: `/members` explained that the app "comes with membership"; the feed, the join flow and the staff section (which sits in the member-app shell) all answered 404 (`/api/members/me/` and `/api/members/home/` failed in the console); there was no authenticator for the staff two-step login; login landed on `/account`; and a fresh development database had too few rows for any metric to show.
414. **(needs no club decision; access rule)** A superuser is the Admin role everywhere (staff section, metrics, reports, team, the door desk through Django's superuser permissions) and holds every entitlement through one rule in `memberships/access.py` (`entitlements()`), with no membership record. On first login (and on the next session check for anyone already signed in) the account is prepared: the email is treated as confirmed, because only someone with server access can make a superuser, and it joins the member app quietly, hidden from the directory, with no bio, picture or posts. The display name is the account's own; no public persona is invented.
415. Without an authenticator, the staff section shows "Set up your two-step login" with the three steps, and its button runs the existing admin enrolment, which returns to the dashboard. `DEV_SKIP_STAFF_2FA` lets the team skip the second step in development only: it is ignored unless DEBUG is on outside staging and production, and the deployment check (rose.E012) refuses to start a deployed site with it set.
416. The admin's content security policy allows its forms to return to the site's own origin (`SITE_URL`), so the two-step login can come back to the staff section in development, where the site runs on Vite and the admin on the API port. In production both are one origin and nothing changes.
417. After logging in with no particular page to return to, the team and superusers land on `/members/staff`. The account menu shows a Staff badge with the role and links to the dashboard, reports, the door desk (for those who may use it), the member app, the website and the Django admin.
418. `seed_demo` adds a year of club life (`apps/pages/demo_activity.py`, run once per database): 44 members across the seven tiers with twelve months of payments, ten past evenings with check-ins, RSVPs on what is coming, gifts, a year of posts and comments, five open and six closed reports, and thirty confirmed email subscribers, so a fresh dashboard shows numbers and charts. The browser tests' fixtures run the same function. `manage.py make_owner <email>` creates or upgrades the owner's superuser, gives it the Admin role, prepares it and prints the next steps.


## Prompt 11

### The account page moves into the member app

419. The old account page is gone. Everything on it now lives in the member app: `/members/home` and `/members/settings/*`, in the app's shell. After logging in with no page to return to, the team and superusers land on `/members/staff`, people whose feed is open on `/members/feed`, and everyone else on `/members/home`.
420. The sign-in pages (`/account/login`, `register`, `verify`, `forgot`, `reset`) stay where they are: they are for people who are not signed in, and every emailed link points at them. Only the signed-in pages moved. `/account`, `/account/notices`, `/account/export` and `/account/receipts/<id>` answer with a 301 to their new addresses (in `pages/content.py`, before the redirect table), and the app does the same for links followed inside it. Settings maps the old page's anchors (`#password`, `#delete`…) to their sections.
421. Home, Settings, Report a concern and the staff section open in the app's shell for anyone signed in, with or without the feed. Without the feed the sidebar and tab bar show only Home, Settings and, for the team, Staff, and every feed page is still the website's ordinary 404. Signed out, those screens ask the person to log in and come back.
422. Settings has seven sections: Membership, Profile, Privacy, Notifications, Security, Community guidelines, and Leave the community. Phones show the list, then one section per screen; wider screens keep the list on the left beside the open section, Membership first. Report a concern, Staff (for the team) and Log out sit under the list.
423. Notices and appeals moved from `/account/notices` into Settings > Community guidelines, beside the current guidelines and the date you accepted them, and the reports you sent. A suspended or banned member still reaches them: the account screens open without the feed (this replaces decision 408's reason for keeping them on the website). Emails link there.
424. Payment history shows dates and amounts only, with a receipt for each payment that has one; the method is on the receipt. "Change plan" goes to `/membership`. "Cancel" runs the existing cancel flow where it applies, and otherwise explains the state and points to the contact page.
425. Appearance (light or dark) sits in Settings > Profile. The sign-in email sits in Settings > Security, still marked "Only you can see this".
426. Pronouns are optional, stored on the profile, and shown on the member's feed profile only when filled in.
427. **(privacy)** Calendar files stay generic ("Rose - Evening", no place) by default. Settings > Privacy can change where the event page's checkbox starts; it is never on unless the person turns it on.
428. Notification switches: event reminders and membership reminders by email, and likes and comments in the app. Turned off, nothing is sent; a reminder that was due is marked handled so it does not arrive later. Discreet subject lines are always on and shown as a locked switch. Account emails (sign-in links, receipts, notices from the team) always go out.
429. **(privacy)** Where you are signed in: a row per signed-in browser with a SHA-256 hash of the session key, a short label from the browser string ("Safari on iPhone") and two times. No IP address and no full browser string is stored. Rows go at logout, at "Log out everywhere", when the password changes (for every other device), with the account, and daily once older than the session lifetime.
430. Two-step login is optional for members and uses the same django-otp authenticator and backup codes as the admin. Once on, the website's login stops after the password and asks for the code (or a backup code) within 5 minutes; wrong codes count towards the same lockout as wrong passwords. Staff cannot turn it off. A website login with the code also marks the session as through the second step, so the team no longer takes the detour through the admin's login.
431. **(privacy)** The data export is now for every account, from Settings > Privacy: `data.json` gains an `account` part (display name, pronouns, appearance, preferences, RSVPs, memberships and payments with dates and amounts) beside the feed data. It still holds no email address, legal name or phone number, because a zip travels; those are visible in Settings. The export endpoints moved from `/api/account/feed/export/` to `/api/account/export/`, and the emailed link now opens `/members/settings/privacy/export`, which works signed in or out because the single-use token is the credential.
432. "Leave the community" lists what is removed and what is kept, for both leaving the feed (Leave and erase) and deleting the account, and offers stepping away as the gentler choice. Stepping away (opting out of the feed) is in Settings > Privacy.

### Prompt 11b: Notices, and no feed request without the feed

433. Notices get their own Settings row, between Security and Community guidelines, at `/members/settings/notices`: decisions about the account with one appeal each, and the reports you sent. Community guidelines keeps only the current guidelines, the date you accepted them and Report a concern. `/account/notices`, the old `#safety` anchor, emails, the RSVP panel's "restricted" note and the paused-app page all point at Notices.
434. The row shows a count of unseen notices: decisions made, appeals decided and reversals since the person last opened the section (`Profile.notices_seen_at`, compared in `safety.services.unread_notices`; the session carries the count). Opening the section marks them seen and refreshes the session, which clears the badge. Reports you sent are listed there but do not count towards the badge.
435. In-app notifications about warnings, suspensions, bans, reversals, appeal outcomes and a reviewed report have their own kind, `notice`, and open Settings > Notices. Other moderation notifications (a post approved or taken down) keep linking to the post.
436. The app decides from the session's `feed_access` whether to ask the feed anything. Without it, no `/api/members/` request is made at all: the shell renders the account-only screens or the website's 404 straight away. The boot-time prefetch for a direct visit to `/members/feed` now waits for the session check it shares with the rest of the app, and starts the feed requests only when the feed is open (this refines decision 320). The feed endpoints still answer 404 to anyone without access.
437. The session is refreshed whenever access changes in the person's own hands: after joining the feed or accepting new guidelines (before the app opens), and after stepping away or leaving and erasing. Changes made elsewhere (a membership started at the door, an appeal upheld, a staff grant) reach an open tab because the shell re-reads a session older than 30 seconds once when someone without the feed comes into the app. A full page load always reads it.
438. The feed and the account-only screens share one shell tree, so losing or gaining the feed swaps the navigation without remounting the open screen (for example, "Erasing everything you shared" stays in view after Leave and erase).

## Prompt 13

### The admin in Rose's look

439. The admin uses django-unfold 0.108.0 (pinned) for every registered model, replacing the photo-app style of decisions 218 to 220. All `ModelAdmin` and inline classes come from `unfold.admin`. The user and group admins combine Django's auth admins with Unfold's, and django-otp's authenticator and backup-code admins are registered again the same way (`apps/accounts/admin.py`). `apps/core/admin_site.RoseAdminSite` is Unfold's site plus the two-step login. `unfold.apps.BasicAppConfig` is installed so the project's own site stays `admin.site`.
440. **(security)** Nothing in the admin loads from another site, and the content security policy is unchanged apart from three style hashes. Unfold's Inter stylesheet, its inline colour `<style>` and its Alpine build are replaced in `templates/unfold/layouts/skeleton.html`. Manrope and Fraunces (OFL) are served from `core/fonts/`. Alpine is the official CSP build (`@alpinejs/csp` 3.16.1, vendored in `core/vendor/`, with a README), and the few Unfold helpers it cannot evaluate are registered as `Alpine.data` components in `core/rose-admin.js`. Templates whose expressions the CSP build cannot run, or that bind a style string, are overridden: the sidebar, change form, actions and the small file input. htmx's injected indicator style is turned off by its meta setting. The only exception is three `sha256` hashes in `style-src` for the fixed `<style>` elements Trix adds (`TRIX_STYLE_HASHES`); `script-src` is still `'self'` alone, with no `unsafe-inline` or `unsafe-eval`.
441. Colours, fonts and radii live in `core/rose-admin.css`, as CSS variables on `:root` and `.dark`, rather than in Unfold's `COLORS` setting (which is written as an inline style). The variables are:
    - Unfold's primary scale is the rose accent.
    - Its blue is mapped to the same rose, so no stock blue appears.
    - Base neutrals are soft greys.
    - Radii are 8px.
    - Dark mode uses the member app's dark tokens.

    The wordmark is "Rose" in oxblood Fraunces. Titles are Fraunces; everything else is Manrope. Chart.js, which Unfold serves, asks for "Inter", so an `@font-face` named Inter points at the Manrope file. The light theme is the default; Unfold remembers each person's choice in their browser.
442. The sidebar (`apps/core/admin_nav.py`) has eight groups: Today, Members, Events, Content, Community, Money, Outreach and Settings, with Lucide icons from `core/icons.svg`.
    - Each item shows only to people with the permission its page checks: `view_` for a model, the queue permission for Reports, `events.view_rsvp` for RSVP counts, editing a page with images for Image review, and superuser for the audit log. A group with nothing in it disappears.
    - Badges are waiting counts and never names: online payments waiting for an ID check, open reports plus first posts, unanswered messages.
    - Only one item is highlighted at a time: the one whose address is the longest match. So the door desk is not also highlighted as Memberships.
    - Unfold's own app list stays under "All applications" for anything not in a group.
443. The dashboard (`apps/core/dashboard.py`, Unfold's `DASHBOARD_CALLBACK`) follows the staff metrics' rules (`apps.safety.metrics`): counts and totals only, and any number under 5 shows as "fewer than 5".
    - KPIs, each needing the permission of the page behind it: active members, new this month, revenue this month, open reports and ID checks needed.
    - Charts, drawn in the browser by Unfold's local Chart.js: revenue for 12 months and active members by tier, where a withheld month or tier has no bar.
    - The next three events, each with "going" as a count.
    - Quick actions for New event, New journal post, Open door desk and Open reports.

    The sidebar badges stay exact, because they are a to-do list for people who can already open the list behind them.
444. Lists and forms:
    - Status chips come from `apps/core/admin_display.py` (`chip`, `flag`), and image previews show whether the image is shown or why it is hidden.
    - Events, tiers and members have tabs. Unfold's form tabs are buttons with `aria-pressed` (`templates/unfold/helpers/fieldsets_tabs.html`), because its own are links without an address that the keyboard cannot reach.
    - Every field uses an Unfold widget; `tests/test_admin_theme.py` checks every registered form and inline. Django's filter-horizontal and autocomplete widgets count, because Unfold's stylesheet styles them.
    - The breadcrumb shows an object's name as written, so display names stay lowercase.
    - Journal posts and classes say "Button label" and "Button link".
    - Editable published flags in list views stay checkboxes, because Django requires them to be form fields.
445. The rich-text editor for event bodies, the agreement and newsletters is Unfold's Trix. Its toolbar is cut down to what `apps.core.text.RICH_TEXT_TAGS` keeps. Unfold's paragraph block was grouped, so Trix joined neighbouring paragraphs into one `<p>` and would have merged them on save. `core/rose-trix.js` makes each paragraph its own block, loaded after Unfold's settings. The sanitiser also turns Trix's `<div>` blocks into paragraphs and drops empty spacer blocks.
446. Every custom page uses the same templates and classes:
    - the dashboard and the door desk
    - Reports (the moderation queue)
    - image review, the membership summary and the staff guide
    - repeat weekly and the door lists
    - the rental pipeline and confirm pages
    - the newsletter preview and send tools
    - loading site content
    - the volunteer export and donation acknowledgement

    The old per-page stylesheets are deleted. A new **RSVPs (counts only)** page lists going, waitlist and checked-in numbers per event, with a link to each door list, and never names.
447. **(security)** Image review and its file view are limited to superusers and staff who can change events, journal posts, staff profiles or classes. A door volunteer no longer sees it.
448. **(security)** `OTP_ADMIN_HIDE_SENSITIVE_DATA` is on, so the authenticator admin never shows a secret key, its QR code or backup codes, even to a superuser.
449. The sign-in, two-step code, authenticator set-up and backup-code screens share one plain template (`admin/rose/sign_in.html`). It holds the wordmark, the form, a line of help and "Return to site", and nothing describing the club.

### The door desk in the staff section

450. The door desk is also at `/members/staff/door`, in the member app's shell, made for a 1024×768 tablet and a phone. It has:
    - a large search box and a Scan QR button, decoded on the device by jsQR, which loads only when scanning
    - one card per person: display name, tier, status, ID verified or ID check needed, events left this month, guests included, and a Do not admit banner that removes every action
    - large buttons for Check in, ID check, Record payment and activate, Guest visit and Renew, with comp, suspend and reinstate below
    - a dialog per action, including "Photo ID checked, 18+" where an ID check is needed
    - Show signature name, payments with refunds, and recording a donation
451. Both desks run the same code. `apps/memberships/desk.py` holds the search, the card and `perform()`, which carries out every action. The admin view and `/api/staff/door/` (`apps/memberships/door_api.py`) only call it, so permissions, refusals, audit entries and the logged signature reveal are identical. Tests run the same actions through both and compare the results.
452. **(security)** The API answers only to active staff with `memberships.change_membership` who have passed the two-step login (`roles.can_use_door_desk`). Everyone else gets the same 404 as an unknown address, before CSRF is checked. Writes need the CSRF token and count towards the account write limit.
453. Door volunteers hold the desk permission without a team role. The session's `staff` block now covers them: `role` is null and `door_desk` is true. Their two-step link returns to `/members/staff/door`, they land there after logging in, and their staff menu has only the Door desk tab. In the member app's menus the desk comes first for volunteers and beside Staff for the team. The admin desk links to the tablet one ("Open the tablet door desk").
454. **(privacy)** `Permissions-Policy: camera=(self)` is sent for the admin desk and for `/members/staff/door` only. Links to the tablet desk load the page afresh (`reloadDocument`), so the browser applies that header; every other page still denies the camera.

## Prompt 12: the age check for the member feed

Prompt 12 was stopped before prompt 13 began and was done afterwards, so its decisions follow prompt 13's.

455. **(privacy)** Nobody sees, posts or comments on member images until staff have checked their age in person. The check is the door desk's existing `IdCheck`: a valid photo ID showing 18+ was seen, by whom and when. Nothing else is taken:
    - no ID number, date of birth, photo, scan or selfie
    - no document storage or biometric processing
    - no upload path of any kind, not even a disabled one

    Reasons:
    - Stored ID images are a breach risk that would outweigh anything they protect.
    - Illinois' Biometric Information Privacy Act makes face matching and selfie checks a legal liability.
    - A person at the door holding the ID is more reliable than any automated check.
456. One rule (`apps.memberships.access.is_age_verified`): true only when the person has a valid `IdCheck` with `verified_18_plus`. `can_join_feed`, `can_view_feed` and `can_post` all require it, whatever the feed entitlement came from: paid tier, free tier, comp, staff grant, staff account or superuser. Every feed endpoint, the media views (signed URLs and watermarked copies), stories, Explore, search, profile grids and notifications sit behind `FeedAPIView`, so the unverified get the same 404 as anyone without access. The team's pictures follow the same rule: the staff section's media path and the admin's moderation images answer 404 to staff without their own check, the report shows "pictures hidden" instead, and the owner is not exempt (`prepare_owner` joins them only once checked).
457. `IdCheck` now belongs to the person (`user`), so one check carries over to every later membership. `membership` records where it was taken, and is empty for an account with no membership. Checks never expire. A check can be revoked with a reason (`revoked_at`, `revoked_by`, `revoke_reason`): the feed closes at once, and the row stays as the record. Migrations: memberships 0004 to 0006 add the fields and backfill `user` (a deleted account's check is dropped, since it verifies nobody).
458. **(security)** A team account's own check needs two people. Either another team member records it, or the person records it with a second team member named as witness (`witnessed_by`). Both are logged: `id_check` by the recorder and `id_check_witnessed` by the witness.
459. Bypasses closed:
    - **A staff grant** with no check shows "Granted, awaiting ID check": in the admin's feed-access column, on the staff section's member page and on the door desk. It gives nothing until the check. The staff section has no grant switch of its own; it shows the state.
    - **`import_members`:** `id_checked=no` rows still import as "paid, waiting for ID check" (the existing pending state, which is not active and gives nothing). The door desk flags them "ID check needed". The dry run now counts both kinds of row.
    - **Comp, guest visit and first activation** already needed the check.
    - **Renewing an expired membership, or reinstating a suspended one,** now needs a valid check on file or the box ticked. Without this, either could switch on a membership whose check was missing or revoked.
    - **An online payment** with no check stays "paid, waiting for ID check" and grants nothing.
    - **The free-tier join and the webhook** start a membership only when the person is verified.
460. Members-only events and classes are unchanged: they follow an active membership, and every way of activating one needs a valid check (tested).
461. Accounts that had the feed before the rule: memberships migration 0007 found the active accounts with feed access and no check (18 on the development database) and stamped `Profile.age_check_notice_at`. Their grants and opt-ins are kept, so the feed reopens the moment the check is recorded. Home and Settings explain why it closed. `apps.memberships.tasks.send_age_check_notices` (every 15 minutes) emails each of them once, with the neutral subject "A note about your account", rather than sending mail from inside a migration.
462. The verify card (Home and Settings > Membership) shows while the check is missing and would unlock something (`age_check.needed` on the session): "Verify your age at your next visit."
    - what to bring: a valid photo ID showing 18+
    - the door code and its QR (the display name for someone without a membership)
    - "We never copy or store your ID."

    The join flow says so before anything else. It lets the person accept the guidelines in advance (`/api/account/feed/guidelines/`), then shows "You are ready". Once checked, someone who accepted in advance goes straight to the profile step. The session has a new `member_app` state, `verify`.
463. Recording a check notifies the person in the app (a new notification kind, `age_verified`, when the feed is theirs) and sends a neutral email: "You're all set", which never says what was checked. The feed opens without logging out, because access is read on every request and the app reads the session again.
464. Door desk, in both the admin and the staff section:
    - every card shows "ID verified" or "ID check needed"
    - a "Needs ID check" list covers current memberships and accounts with no membership (team members and staff grants)
    - "Record ID check" records the check on its own, without activating anything
    - "Revoke ID check" needs a reason
    - the dialog is unchanged: "Photo ID checked, 18+" and the staff member, nothing else
465. **(security)** Signed media URLs must expire within 60 seconds: settings refuse a longer `S3_SIGNED_URL_SECONDS`. Every request to the media view checks access again, so a revocation (or a ban) also stops URLs already handed out within a minute.
466. Create's consent box now reads "Everyone identifiable in these photos is 18 or older and agreed to them being posted here.", and Share stays disabled until it is ticked. "May involve someone under 18" was already a report reason that hides the content at once. It now goes to the top of the staff inbox and of the admin's Reports, marked "Possibly under 18".

### Prompt 12 addendum: a switch for the age check

467. The age check is a club setting: `SiteSettings.require_age_verification_for_feed`, on by default (new databases and `seed_demo` included). Every feed, media and staff-picture check calls `age_gate_passes(user)` in `apps/memberships/access.py`. It is true when the setting is off, or when `is_age_verified(user)` is true. Nothing reads the setting directly except `age_check_required()`. `is_age_verified` is unchanged.
468. **(security)** Only the Admin role and superusers can change it. They do so from Settings › Site settings in the admin (its own page) or from the staff section (the age verification card on the dashboard, or the banner). Moderators and Staff see its state: the card on the dashboard or under Reports, the admin page, and the banner. A change needs:
    - a confirmation explaining the effect, including how many people turning it on would affect
    - a typed reason
    - a fresh code from the person's own authenticator app, which django-otp refuses if it was already used

    Each change writes an `AuditLog` entry in the new `settings` category: who, when, "Changed from On to Off" and the reason.
469. The setting is cached for 5 seconds (`AGE_CHECK_CACHE_SECONDS`), and the cache entry is deleted when it changes, both at once and again after the transaction commits. A switch therefore reaches every request, including media URLs, within moments. Signed URLs already handed out expire within 60 seconds (decision 465).
470. While it is off:
    - every staff page shows an amber banner, "Age verification for the member feed is off": the admin under its header, and the staff section above each page. Admins can open it to change the setting.
    - the verify card is hidden, `member_app` is never `verify`, and the join flow does not mention the check
    - staff grants show as "Granted", not "awaiting ID check"
    - the door desk still shows ID verified and ID check needed, and still records checks

    No weekly staff metrics email exists, so there is none to mention it in.
471. These hold whatever the setting:
    - the door desk's ID check before any paid, comp or guest activation, or a renewal or reinstatement
    - `import_members` with `id_checked=no` waiting for a check
    - the upload promise that everyone pictured is 18 or older
    - "possibly under 18" reports hiding content at once and going first

    Tests run each of these with the setting off.
472. This replaces decision 461. Memberships migration 0007 changes nothing and only prints how many active accounts have feed access and no ID check (18 on the development database), so the club knows the effect before turning the check on in production. Accounts migration 0010 drops the email timestamp and clears the notices the first version of 0007 had stamped (nobody had been emailed about them). The scheduled notice task is gone.
473. Switching it on tells each person it closes the feed to: one neutral email ("A note about your account") and the notice on their verify card. That happens at most once per person per switch-on. `SiteSettings.age_verification_switched_on_at` records the switch-on, and `Profile.age_check_notice_at` records the switch-on each person was told about; `apps.memberships.tasks.notify_age_check_switched_on` runs once the change is committed and skips anyone already told. Switching it off and on again tells them again.

## One dashboard, one door desk, one set of numbers

474. The admin dashboard (Unfold, `apps/core/dashboard.py`) is the only dashboard. The staff section's dashboard, its metrics API (`/api/staff/metrics/`, its export and `/api/staff/overview/`) and its age verification card and API are removed. The staff section keeps the hands-on tools: the door desk, the reports inbox, members and the team (admin). Its tabs have a **Dashboard** link that opens the admin dashboard, shown to every team role.
475. Every number comes from `apps/core/metrics.py` (moved from `apps/safety/metrics.py`):
    - the dashboard's cards, charts and tables
    - the sidebar badges
    - the membership summary, the RSVP counts page and the events list's Going column
    - the export

    Each metric is defined once and documented in `docs/ops/metrics.md`. "Open reports" is open plus in review everywhere. The old Reports badge also counted posts waiting for approval, which is why it said 11 where the dashboard said 9; those posts are now their own metric, on the Feed posts badge. "ID checks needed" is memberships pending payment with `paid_awaiting_id_check`, on an active account. The admin Reports page no longer shows item counts that could be mistaken for the report count.
476. **(privacy)** Suppression happens in the service, so no screen can skip it. A count from 1 to 4 is withheld; zero shows as 0. Zero identifies nobody, and a badge saying "<5" when nothing is waiting would mislead. This changes decision 405, which withheld zero too, as that brief said. Withheld figures show as "<5", with "fewer than 5" as their tooltip and for screen readers, through `admin/rose/metric.html`. That keeps every KPI card readable at 390 to 1920 pixels wide: the cards wrap rather than clip. Badges show the same "<5". The membership summary and RSVP counts pages now withhold small numbers too, where they used to show them exactly.
477. On the dashboard, the Admin and Staff roles (and superusers) see everything:
    - the KPI cards and the 30-day, 90-day and 12-month range switch
    - charts of revenue, payments, RSVPs and feed posts
    - the tier table (active, new, renewing, lapsing, expired, and all tiers)
    - revenue this month and last, feed activity and the events in the period
    - Coming up and Quick actions
    - the aggregate CSV export (`admin:metrics_export`, POST, logged)
    - the age verification card, which only admins can use to change the setting

    Moderators see only open reports, posts awaiting approval and ID checks needed. Door volunteers see ID checks needed; other staff accounts see the waiting cards their permissions cover.
478. After logging in, the Admin and Staff roles (superusers included) land on the admin dashboard, moderators on the reports inbox, and door volunteers on the door desk. `/members/staff` itself sends the team to the inbox and volunteers to the door desk.
479. One door desk: the staff section's (`/members/staff/door`). The admin's door desk view, templates, script and vendored jsQR copy are removed. Its address (`admin:memberships_door_desk`) redirects to the staff desk and keeps `?q=`. The sidebar's **Door desk**, a membership's **Open** link and the **ID checks needed** card (`?needs_id=1`) all open the staff desk. Every action the admin desk had is in the staff one, tested action by action. Only the staff desk is allowed the camera now. The session's `staff.door_desk_url` is gone, and the banner links admins to the setting's admin page (`staff.age_check_url`).

## The way into the member app

480. Home (`/members/home`) shows "What's missing": the steps between the account and the member feed, in order. They are verify email, choose a plan, get activated at the door, the age check (only while the club has it switched on) and join the community. `apps/feed/path.py` works them out from the same rules the feed uses, so the list is complete exactly when the feed opens. Each step is done, current or upcoming, and only the current one carries its action. Feed access that comes with the account (the team, or a staff grant) counts as the plan and the door, "Included with your account". Once every step is done it offers "Open the community".
481. The checklist takes over the verify card's job on Home: what to bring, that nothing is stored, and the door code. The code shows once on the page, in the door step while that step is still to come and on the membership card after. Settings > Membership keeps the verify card.
482. **(privacy)** Accounts without the feed see a preview of it on Home: a lightly blurred grid and one post card. The server builds it (`/api/account/feed/teaser/`) only from the club's own posts: journal photos, the latest journal post (posted as "Rose") and the titles of current announcements. Announcement bodies and links stay out, as they are written for members. No member's post, profile, avatar, display name or count is ever in it, and the journal author's name is left out too. `tests/test_feed_path.py` checks this with member content present.
483. `make_feed_member <email> [--tier rose]` gives an account the whole feed in one step, for local testing. It creates and confirms the account and starts a membership through the door desk's own activation, recorded by an inactive system account `system_dev`, which also records the ID check. It accepts the guidelines, joins the feed and sends a link to choose a password, which lands in Mailpit. It is idempotent and prints each step. It refuses to run unless DEBUG is on, and never in staging or production. It writes the demo seed marker, so a deployed site refuses to start on a database it touched (rose.E010).
484. `import_members` and `make_feed_member` share `apps.memberships.system.system_user`. Each keeps its own inactive account (`system_import`, `system_dev`), so the audit log says which one acted.
485. The browser tests run `make_feed_member` in the app container with DEBUG on for that one process (`E2E_MANAGE_CMD`); the app itself keeps DEBUG off.

## Admin: real actions on Members

486. The admin's Members list (Accounts › Users) and each person's page offer the same actions, from `apps.accounts.member_actions`. Moderators can warn, suspend from the feed or from events, lift suspensions and remove all feed content. Staff can also send a password reset and log out everywhere. Admins can also ban, unban, give or take back the staff feed grant, mark an email verified, deactivate, reactivate, export as CSV and erase. Each action calls the existing service: moderation in `apps.safety.services`, the account in `apps.accounts.services`. Each opens a confirmation page naming the people by display name. Each needs a reason, plus the rule broken for moderation, except the password reset (nothing to ask) and the export. Afterwards it says who it was done for and who was skipped, and why. There is no action for ID checks: they happen in person at the door desk.
487. The rules shared by every action: at most 50 people at once, refused as a whole with a message; never your own account. Staff and superuser accounts are skipped and listed for ban, both suspensions, erasure and also deactivation, so no bulk action locks out a team member: their role changes in Team and roles first. Ban, unban and erase need a fresh code from the actor's authenticator app (`two_step.fresh_code`, moved from the age-check setting), checked once per batch.
488. **(privacy)** Django's delete is gone from Members, for everyone: no "Delete selected", no Delete button, and the delete view answers 403. Profiles cannot be deleted either. **Erase account** (type ERASE, a reason and a fresh code) runs `apps.accounts.erasure.erase_account` as a Celery task. It is the same routine the member's own Delete account now uses: event places freed, everything in the feed and its files deleted (posts, images in storage, comments, likes, follows, blocks, notifications, watermarked copies, exports), memberships and payments detached, contact messages, volunteer offers and rental contacts forgotten, then the account deleted. The closing email says it was done "by our team".
489. **(privacy)** Moderation records outlive an erased account. `MemberAction.member` is now nullable (`SET_NULL`), and the record shows "Erased member". The audit log replaces the erased person's display name with "Erased member" in its target, reference and actor labels (`AuditLog.forget_person`), the one change the append-only log allows: what happened, when, who else acted and why stay as written. Free-text reasons written by staff are not scanned. A blocked email from a ban stays blocked.
490. "Remove all feed content" is a new action kind (`remove_all_content`). It takes down every post and comment of theirs still up and records what each was, so reversing it (from the staff section, like any action) puts back exactly those.
491. Every action that changes an account or its access tells the member: the moderation notice and the "An update about your account" email, with the details only in the app. That covers the feed grant, a confirmed email, logging out everywhere, deactivation and reactivation too. The password reset's own email is its notice; the export changes nothing for them; erasure sends the closing email.
492. **(privacy)** Email addresses on Members are for admins only: the column, searching by email, and the email, private details and permissions tabs on a person's page. Moderators and Staff see the display name, when they joined, the moderation history and the membership. The history tab hides who sent each report; an admin's **Reveal** asks first, then logs it through `safety.services.reveal_reporter`. The Profiles page now only shows suspensions, bans, the door flag and the feed grant: they change only through the actions, which log them and tell the member.

## Admin: archive past events

493. One definition of where an event stands, from its own times (`apps.events.models.Timing`). It is *upcoming* while it has not started, *happening now* from its start until its end, and *past* once its end is before now. Nothing is stored, so nothing goes stale: editing the dates moves an event between the lists. The queryset's `upcoming()`, `happening()`, `not_past()`, `past()` and `overlapping()`, and `Event.timing`, are the only places this is decided. That covers the public list, the calendar and `?past=1`; the event API's `timing`; the RSVP rules (a past event refuses with `past`) and the "my RSVPs" list; the RSVP reminders and the retention purge; the dashboard's next events and check-ins; the stories tray; rental conflicts; and the admin. Times compare as instants and show in Chicago time.
494. An event's end time is now optional. With none, it counts as over 6 hours after it starts (`DEFAULT_LENGTH`). The site and the reminder email then show only the start, and the calendar file has no end, rather than an invented one.
495. The admin's Events list shows what is still to come or happening now, soonest first, with Upcoming, Happening now, Draft and Private hold badges and a link to the archive. **Past events** is the same table through a proxy model (`PastEvent`, whose manager returns only past events), newest first. Its going and checked-in figures come from `apps.core.metrics.event_figures`, with the "<5" rule. Past events open read-only. "Edit anyway" opens the form, and saving writes `edit_past_event` to the audit log with what changed; a past event opened from the main list goes to the archive. "Duplicate as new event" copies everything except the RSVPs, counts and slug into an unpublished draft at a chosen time, moving its end and RSVP window with it; "Repeat weekly" now shares that copy, so it also keeps tags and the guest allowance. "Unpublish" is logged too. Only the Admin role may delete from the archive, through Django's confirmation page.
496. **(privacy)** A past event's page still loads, so old links and journal posts work. It says the event has passed, has no RSVP panel and links to what is coming up in the same category. Search engines are asked not to list it: a `noindex` robots meta tag in the page, and an `X-Robots-Tag: noindex` header from the server for crawlers that do not run the app.

## Public Events page: image card grid

497. The owner's override (noted at the top): `/events` is a grid of image cards, 3 across from 1024px, 2 from 640px and 1 below, 15 at a time at every width. The views are "Grid · Month"; the old list rows (`EventCard`'s row layout) are gone, and Home keeps the boxed card. Each card shows the picture (4:3, covered, rounded top) with the date and, for members-only evenings, "Members only" over it. Under it come the category and time, the title (two lines at most) and the summary (two lines, plain text), then the RSVP status. The whole card is one link, with a focus ring and a small lift on hover that reduced motion turns off.
498. The list API is now paginated for every caller: `count`, `next`, `previous` and `results`, 15 a page, `page_size` up to 50. Home, the member app's Home and side rail, and the concern form ask for the few they show. The grid's `?page=N` means "the first N pages": "Load more" adds the next 15 as its own history entry (Back returns to fewer), a shared link opens with those pages, and asking past the last page stops there. The page numbers are plain links for keyboards and screen readers, and the first card of a newly shown page takes focus. A filter or view change goes back to page 1. The site is a single-page app, so there is no no-JavaScript fallback; the links are the accessible fallback.
499. Event pictures get WebP copies at 400, 800 and 1200 px (`HERO_WIDTHS`, against 640 and 1280 for other public pictures), with the original's size recorded so cards reserve their space; never scaled up. Migration `events.0008` makes the missing copies for pictures uploaded before. The first row's pictures load at once, the rest lazily. **(privacy)** A missing picture, or one showing faces without confirmed consent, shows the category's fallback: a soft gradient in the site's washes with a Lucide icon (education, social, workshop, member night, special). The withheld picture never reaches the browser. The API sends `image_fallback` (the category), and the title stands in for missing alt text, which the event's admin page also warns about.
500. The list costs the same number of queries however many events it shows, for visitors and members alike. Within a list, a person's membership and each month's use are looked up once (`memberships.access.remembered`), and event tags are prefetched. The memo never spans a change, so an RSVP always sees fresh numbers.
501. One event at a time can be featured ("Feature at the top of the Events page", `Event.is_featured`). Ticking it on another event first asks, naming the event that would lose it; saving then moves the feature, and a database constraint keeps it to one. Featuring ends by itself once the event is over (`Event.objects.featured()` is built on the shared timing helper), so nobody has to untick it; an expired feature is replaced without asking. Copies never take the feature. While a featured event is visible to the person, it appears as one large banner at the very top of `/events` (above the filters) and of Home's "Coming up". The picture takes about 60% at 16:10 from 768px, beside the date, category, time, title, three lines of summary, the RSVP status and "View event", and sits on top below 768px, with a "Featured" badge on it. The list API leaves the featured event out, so the grid never repeats it and still shows 15. `/api/events/featured/?category=` gives null when the category leaves it out, which hides the banner.

## The club's name

502. The name is configuration, not code, and shows only where people read the site. `SITE_DISPLAY_NAME` and `SITE_SHORT_NAME` (environment; "Rose" when unset, the short form defaulting to the full one) are the defaults, and Admin > Site settings > Club name and Short club name override them, through one helper (`apps.core.branding`). The website (the logo's alt text, page titles, Open Graph titles), the member app and staff section, the admin header, sign-in page and page titles, the club's account in the feed and the demo tiers read the full name; the story viewer uses the short form. Page copy and FAQs write `{display_name}` or `{short_name}` and the API fills them in, so no copy hard-codes the name. The server writes both into the page (`rose-site-display-name` and `rose-site-short-name` meta tags, plus `<title>` and `og:` tags on public pages), so the app knows them before the age gate makes any request; the Vite dev server uses `VITE_SITE_DISPLAY_NAME` and `VITE_SITE_SHORT_NAME`. **(privacy)** The real name stays out of the repository and the image, like `/content` (decision 265). Discreet places keep the neutral "Rose" and never read these settings: email sender names and subjects (`EMAIL_SENDER_NAME`), calendar files ("Rose - Evening"), receipts and billing descriptors (`MERCHANT_DISPLAY_NAME`), the authenticator app (`OTP_ISSUER`), member-app tab titles, and the name under a home-screen icon (`apple-mobile-web-app-title`, `application-name`), as decisions 162, 163 and 191 require. `tests/test_branding.py` sets a name containing "Chicago" and checks none of those places carries it.

## The logo

503. At the owner's request, the club's neon emblem replaces the Claude Design wordmark (the club's name set in Fraunces) everywhere a logo appears: the website header, footer and age gate; the member app and staff section sidebar and the Home top bar; the club's avatar on posts and stories; the admin's sidebar header and sign-in pages; the tab icons, home-screen icons and link previews. `scripts/build_brand_assets.py` makes every size from the owner's PNG; that 1.8 MB source stays out of the repository (`photos/` is ignored) and no page loads it. Only the generated files are committed, and none of them carries the name as text: the alt text comes from the name setting (decision 502). There are two variants, the full emblem and the rose head alone. The rose's leaves cross the neon line and the lettering, so the mark leaves them out. The mark is used below 36px and for every icon. The glow reads on white, `#FAFAFA`, blush and the dark canvas, so the emblem sits on the page without a box. The emblem is now the largest thing on the age gate, so the server preloads it for visitors who have not passed the gate, and every logo reserves its height before it loads. **(privacy)** `/exit` stays an unbranded white page (decision 15), and emails, receipts, calendar files, notifications and member-app tab titles carry no logo. The `wordmark` colour token, now used only by the paywall and photo-ID icons, is renamed `ink`. Sizes and placements are in `docs/design-system.md` (Logo).

## Events: the featured banner without a layout shift

504. On its first load, `/events` holds the filters and the events back until it knows whether there is a featured event (the two requests run side by side), with a skeleton in their place. The banner arriving after the grid had pushed the whole page down (layout shift 0.52 on a phone, performance 73; now 0 and 95). Changing the category afterwards is the visitor's own action and is not held back. Lighthouse must see the age gate accepted (decision 205) with the `age_ok` cookie set in the browser itself: the gate reads it in the page, so a Cookie request header measures the gate instead.

## Page images

505. Every fixed picture on a public page is a `SiteImage` slot (`home.hero`, `about.hero` and the other page headers; `docs/page-images.md` lists every picture on every page), edited in Admin > Content > Page images by Staff and Admin, not Moderators. A slot uses the consented image pattern (decision 4's rule, now enforced on save: a picture showing faces needs confirmed consent, and alt text is required), so uploads are checked by their bytes, stripped of metadata and stored as WebP with 640 and 1280 copies. This replaces `frontend/public/images`, `docs/image-manifest.json`, `scripts/fetch_images.py` and `review_images` (decisions 4, 40, 52 and 280's list, now `docs/old-site-images.txt` for reference). The pictures the slots started with are kept in `backend/apps/pages/site_image_seeds/` and stored by `pages` migration 0009 under fixed names, so a new environment starts with them.
506. Replacing, removing or restoring a slot's picture keeps the one before as a `SiteImageVersion`; the five newest are kept and older ones are deleted with their files, unless another slot or version still uses the file. Every change, removal and restore is in the audit log (Site content). Size and shape are warnings, never refusals: a picture under the slot's recommended width, or more than 35% wider or taller than its shape, saves with a message.
507. Each slot has a focal point (0 to 1 across and down), set by clicking the picture in the admin with crop previews at the slot's computer and phone shapes; the site applies it as `object-position`. The server writes the slot map into every page (a JSON data block, which the content security policy allows because it never runs) and preloads the page's own picture with the sizes the page uses, so a page image starts loading with the HTML, as the static files did. `/api/site-images/` serves the same map for the Vite dev server; it is cached until a slot changes and sent with `no-cache`, so a change shows within seconds.
508. Uploads also accept AVIF, recognised by its `ftyp` brand like HEIC (decision 195).

## Staging preview mode

509. Staging can run before object storage and an email provider exist: `PREVIEW_MODE=true` with `STORAGE_BACKEND=local` and `EMAIL_PROVIDER=console` turns `rose.E006` and `rose.E007` into the warnings `rose.W006` and `rose.W007` on staging, and changes no other check. Production refuses the flag (`rose.E013`) and still refuses local storage and console email whatever it says. Public uploads are served from `/media/` only in a preview; private media keeps its access-checked view. Because the worker cannot see the web container's disk, tasks run in the web process in a preview with local storage. **(privacy)** Django's console email writes raw to stdout, past the log scrubber, which would put addresses and live sign-in links in Render's logs. A preview instead writes one scrubbed log line per message with its subject only, and staff get a fresh verification or password-reset link on demand with `manage.py show_email_link` in the Render shell (preview only, staff only, audited). That was chosen over relying on the admin's "Mark email verified", which covers neither password resets nor non-admin staff. The service logs a warning at start, and the admin and staff section show a thin "Preview mode" strip.
