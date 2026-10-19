# Gap report

The app as it stood on the `design-system` branch before the redesign, measured against the
designs in `source/`. Captures are in `before/`, references in `reference/`, both named as in
`screen-map.md`. The sweep script is `e2e/scripts/design-sweep.mjs`. It was run against a
local stack (Django, a Celery worker with beat, Vite) on a fresh database loaded with
`seed_demo`, at 390×844 and 1440×900. Its raw results are in `before/sweep.json`.

## Functional breaks

These were found by the sweep and fixed before the "before" captures were taken.

| # | Break | Cause | Fix |
| --- | --- | --- | --- |
| 1 | Journal pictures were missing in development: the home page strip, `/journal`, journal posts, and journal posts in the member feed and its right rail. The console showed `ERR_BLOCKED_BY_RESPONSE.NotSameOrigin`, and the sweep counted the same images as third-party requests. | Vite's proxy shorthand (`'/api': target`) turns on `changeOrigin`, so Django saw the backend's own host (`localhost:8000`) and built absolute image URLs on that port. Media responses carry `Cross-Origin-Resource-Policy: same-origin`, so the browser refused them on the dev server's origin. Production serves one origin and was not affected. | `frontend/vite.config.ts`: the `/api` and `/media` proxies keep the browser's Host (`changeOrigin: false`), so image URLs are built on the page's own origin. |
| 2 | `/members/*` for anyone without access showed a bare 404: no header, no footer and **no Leave control**. That breaks "quick exit on every page", and it did not look like the site's ordinary 404. | `AppShell` rendered `NotFoundPage` on its own, outside the website `Layout`. | `Layout.tsx` gained `SiteFrame` (the header, main area and footer around any content), and `AppShell` renders the denied 404 inside it. The `AppShell` test now checks for the website navigation and a Leave link. |
| 3 | axe `aria-hidden-focus` (serious) on every feed with a sensitive post, in light and dark. | `SensitiveBlur` put `aria-hidden` on the blurred photo, but the carousel inside it still had focusable buttons. | The blurred content is now `inert`: it cannot be focused or read until View is pressed. |
| 4 | `/account` for anyone without feed access made a request that failed with a 404, and logged it as a console error. | `FeedSection` always fetched `/api/account/feed/`, which answers 404 to anyone without access (by design). | The session payload gained `feed_controls` (entitled or with feed history). The page fetches the controls only when it is true, and otherwise shows the membership panel straight away. The 404 endpoint is unchanged. Backend and Vitest tests cover both cases. |
| 5 | Local image processing never finished: posts stayed "Processing". | Environment, not the app. The sweep's worker was started with Celery's default prefork pool, which fails on macOS (`not enough values to unpack`). The README already says `--pool=threads`. | The worker was restarted with `--pool=threads`. No code change. |

The sweep also found that a login request with a wrong password, and member paths for people
without access, each log a console error. These are the intended responses (a 400, and the
404 the privacy rules require), and the browser logs any failed response. The sweep counts
them as expected. Nothing else failed: there were no broken internal links (every one seen
was followed, signed out and signed in), and the footer sign-up, contact and login forms all
worked. No page overflowed sideways at either width.

## Overall

- **Website:** the structure and copy follow the earlier prompts (eyebrow labels, long heroes
  with a rose wash, a four-column footer, the "R" mark beside the wordmark). The designs are
  flatter, more editorial and denser:
  - a 72px header with a plain wordmark, nav at 14/500, then "Log in", a filled "Join" and a
    bordered Leave pill;
  - page titles in Fraunces 300 at 52px with a muted lead and no eyebrow;
  - 1px `#DBDBDB` dividers in place of washes;
  - 16px cards with 24px padding;
  - status badges as filled pills (Open tint, Waitlist amber, Full grey, Members only black,
    Going rose);
  - a compact two-row footer (address and email, email sign-up, Privacy and Leave).
- **Colour:** the rose is `#E0245E` with `#CE2156` hover; the design uses `#CE2156`, with
  `#A3123F` for hover and tint text. The wordmark is `#7B1E2E`; the design uses oxblood
  `#5A0F23`. Error is `#C62A3A`; the design uses `#C62828`. Dark is `#0C0C0C` / `#161616`; the
  design uses `#0A0A0A` / `#141414` with a `#262626` border and `#E0527D` links.
- **Member app:** the shell, feed, profile and grid already follow the same model, so the gaps
  are detail:
  - the phone top bar uses a heart for notifications (the design uses a bell);
  - the Leave item is red (the design uses muted grey);
  - the sidebar's Notifications uses a heart (the design uses a bell);
  - the profile row shows an avatar initial;
  - story labels and rings differ;
  - the post card adds a separate RSVP button under club photos and a "Processing" bar;
  - Settings is grouped under headings (the design has one list of 56px rows with icons);
  - Create has a step progress bar and puts Next and Leave in the header.

## Screen by screen

| Screen | Gap |
| --- | --- |
| Age gate (both) | The design has a white card on the blush backdrop with "Rose" in oxblood, a 30px light headline, a muted note and two 48px pills ("I'm 18 or older", "Leave"). The current gate is a full-bleed photo layout with different copy. |
| Home (both) | Hero: the design has a two-column grid with a 64px headline and a 5:4 image; the current hero has an eyebrow, an italic accent word and no image. "Who we are" is a two-column text block in the design; the current one has an image and a heading. The event cards are compact in the design (date column, chip, title, time, filled badge); the current cards have icons, location and "0 going". The design shows education cards with a 3:2 image, level chip and outline RSVP pill; a six-tile Journal strip with 12px corners; an oxblood values band (the current one is a row of bordered cards); "Get involved" cards on `#FAFAFA` with "→" links; a centred closing call to action; and the compact footer. |
| Events (both) | The design has a list of rows (date column, Fraunces 26 title with chip, description, time, badge) and pill category filters. The current page has a "Show" select and a grid of cards. The phone month view in the design has a 7-column grid of 8px-radius days with dots, then the day's cards below; the current month view is a bordered table. |
| Event detail (both) | The design has a full-width 420px hero image; a chip and "Beginner friendly"; the title in Fraunces 300 at 52px; When/Where/Cost in three columns between rules; and the body at 17px. The RSVP panel is 400px wide with 20px corners: "RSVP" plus a badge, a party-size stepper in a 12px box, a 48px CTA, "Add to calendar" and a note. The current page has an eyebrow chip, a lead, icon detail items and a "RSVP for this evening" card with "0 going". The design also shows the five panel states in a row; these are states of one panel, not page content (see the decisions). |
| Education (both) | The design has category and level pill filters with a divider, and 3:2 image cards with a level chip on the image. Locked classes show the blush paywall ("For members", Join and Log in). The current page uses select filters and gradient cards with two chips and two buttons. |
| Plan Your Visit (both) | The design has a two-column hero; three numbered steps (rose "01"); a blush photo-ID callout with an ID icon; Hours rows and Directions side by side; and a "Questions we get" accordion with a chevron. The current page has an eyebrow hero, an icon grid and rose-bordered callouts. |
| Contact (both) | The design has a two-column layout: the title, lead and email on the left; the form on the right, with 48px fields, 12px corners, 1.5px error borders and 13px error text, then Send and "We only use your email to reply." The success state is a blush card with a rose check circle, "Thanks, Jules. We got it." and an outline "Back to home". The current page has a hero, a bordered form card and a contact-details aside. |
| Join step 1 (both) | The design has its own header (wordmark, a three-step indicator with numbered circles, Leave) with no site nav, a centred title, and three 320px tier cards. The highlighted tier has a 1.5px rose border and a "Most members" tag. The phone shows a three-bar progress indicator, compact tier rows and a sticky "Continue with Annual". The current page has a long marketing hero, a benefits grid and a Choose/Agreement/Payment stepper. |
| Join step 2 (both) | The design has the agreement title and the chosen tier summary in a left column, and on the right a scroll box with a fade, a 22px checkbox, a signature field in Fraunces italic, and a disabled "Agree and continue" until ready. The current page has a single column with a bordered box and a "Sign and continue" button. |
| Join step 3 (both) | The design has "You're in" in rose caps, "Welcome, <name>.", "Open the member app" and "Save to wallet", and a blush door-reference card with the code in Fraunces 44 and a QR code. The current page has a check-icon card ("You are almost a member"), the reference code next to the QR code, and a "What to bring" list. |
| App Home (both) | Phone top bar: the design has a bell and a muted Leave icon; the current bar has a heart and a red Leave. The current stories have icons inside the circles and the design shows images or colour. The design's feed tabs are left-aligned on desktop. Right rail: the design has a 44px avatar with "Edit", date tiles on the tint, rose "RSVP"/"Join list" actions, "From the club" with 44px thumbnails, and an 11px footer. The current rail has text-only events and "See all". The post card differs in detail (see the post card row). |
| Post card | The design: a 56px header with a 32px avatar, "• 2h" and a more icon; full-bleed media with no radius; dots 12px below the media; a 44px action row; "Liked by you" (or "N likes" for the author); the caption with "more"; "View all N comments" and two comments; a 10px caps timestamp; then "Add a comment…" with a rose "Post". The current card has the media in a rounded frame, club posts with a separate RSVP button, "0 likes" shown to the author, and comments that are not inline. |
| Post detail (both) | The desktop modal is close: the design has a 608px image beside a 335px column, a 4px radius and 32px avatars on every comment. The phone design is the post card under a "Post" top bar. |
| Story (both) | The design has "Rose" in the top left of a `#1A1A1A` backdrop, a 440×782 card with a 12px radius, the title in Fraunces 32, and a white 44px "RSVP" button. The current viewer uses a system title, a rose RSVP button and side arrows. |
| Profile own / other (both) | Close. The design's desktop header is a 150px avatar, then the handle at 20px with "Edit profile" and a settings button, "12 posts", and the name, bio and joined date. The tabs are 12px caps. The current page differs in avatar size and adds Follow and Mute buttons for other members; the design shows only a more icon. |
| Explore (both) | Close. The design adds a phone search field at the top (36px, `#EFEFEF`) and uses 4px gaps on desktop. |
| Search (both) | The design's desktop panel has a "Search" title at 24/600, a 40px field, a "Recent" list with "Clear all" (see the privacy conflicts), and 44px avatars. The phone has a field with Cancel and results. The current search is close in layout. |
| Notifications (both) | Close. The design has "This week" / "Earlier" sections, 44px avatars and 44px post thumbnails. |
| Create (all) | The design: a 42px modal header with a back arrow, title and rose "Next"/"Share"; step 1 shows "Drag photos here" with a 72px image icon; the redaction tools and a 1:1 / 4:5 switch sit over the photo; step 3 has a 525px preview beside a 335px details column with toggles and the required consent checkbox; step 4 is "Post shared" with a rose check circle. The current flow has a step progress bar, a Leave icon in the header, Describe-photo fields first and no aspect switch. |
| Settings (both) | The design is one list of 56px rows with 24px icons: Edit profile, Appearance (value "Light"), Always show sensitive posts, Hide me from the member directory, Step away, Export my data and Leave and erase (red). The current page has grouped sections with headings, an inline Light/Dark switch and a Blocked list. |
| Home dark (both) | The design palette is `#0A0A0A` / `#141414` / `#262626`, a `#F1D9DF` wordmark, `#E0527D` links and `#2A1218` date tiles. The current dark palette is `#0C0C0C` / `#161616` / `#363636` with `#FF5C8A` links. |

## Routes with no design

About, Staff, Guests, FAQ, House rules, Rentals, Volunteer, Donate, the subscription pages,
Cancel RSVP, the education detail, Journal and journal posts, Privacy, the account pages,
Join the feed and the 404 all share the current look (eyebrow heroes, rose washes, bordered
cards). They take the new header, footer, type scale, buttons, fields and cards, laid out
like the nearest designed screen in `screen-map.md`.
