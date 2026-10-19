# Design system

Two experiences share one light palette (prompt 07): the **website**, a calm editorial
site in Fraunces and Manrope, and the **member app** under `/members/*`, a light,
photo-app style shell in the system font. A neutral near-black **dark** appearance is
available to both through Appearance; light is the default whatever the device prefers.

Tokens live in `frontend/src/index.css`. The palette is a set of `--ui-*` variables on
`:root`, redefined under `:root[data-appearance='dark']`; the `@theme` semantic colours
read them, so they work both as CSS variables (`var(--color-fg)`) and as Tailwind
utilities (`text-fg`, `bg-surface`). Components use the **semantic** tokens only. The
`dark:` variant follows the Appearance setting, not the device.

### Appearance

`lib/appearance.ts`. `main.tsx` applies the `appearance` cookie before the first paint
(no request is made for it). Once the session loads, the account's saved choice wins and
is written back to the cookie, so it also applies after logging out. Changing it (account
page, member app Settings or More menu) applies at once, sets the cookie and, when signed
in, saves it on the account (`PATCH /api/account/session/ {appearance}`).

## Website

The public site: every page outside `/members/*`, including the account and sign-in pages and the age gate. Its layout, structure, navigation, components and content are those of prompts 01 to 06; prompt 07 changed its colours only, plus the "My feed" header item.

### Colour

| Semantic token | Light | Dark | Use |
| --- | --- | --- | --- |
| `canvas` | `#FFFFFF` | `#0C0C0C` | Page background |
| `surface` | `#FAFAFA` | `#161616` | Cards, panels, alternate sections (the secondary surface) |
| `surface-raised` | `#FFFFFF` | `#1F1F1F` | Menus, toasts, image wells |
| `surface-sunken` | `#FAFAFA` | `#121212` | Footer, form fields |
| `border` | `#DBDBDB` | `#363636` | Borders and dividers |
| `border-strong` | `#8E8E8E` | `#8E8E8E` | Form field and ghost button outlines (3:1 for UI components) |
| `fg` | `#262626` | `#F5F5F5` | Primary text |
| `fg-muted`, `fg-subtle` | `#737373` | `#A8A8A8` | Secondary text |
| `primary` | `#E0245E` | `#E0245E` | The rose accent: buttons, active states, the liked heart |
| `primary-hover` | `#CE2156` | `#CE2156` | Hover, 8% darker |
| `primary-deep` | `#FDF2F5` | `#2A1219` | Tinted callouts |
| `on-primary` | `#FFFFFF` | `#FFFFFF` | Text on the accent |
| `accent`, `rose`, `highlight` | `#CE2156` | `#FF5C8A` | Rose text: links, eyebrows, icons, focus rings |
| `danger` | `#C62A3A` | `#FF6B78` | Error text |
| `error-mark` | `#ED4956` | `#FF6B78` | Error icons and borders (not text) |
| `success` | `#1E7E34` | `#5FD068` | Confirmations |
| `wordmark` | `#7B1E2E` | `#D4848F` | The "Rose" wordmark only (the existing deep oxblood) |
| `hover` | `#EFEFEF` | `#262626` | Neutral hover and grey buttons in the app |

Images keep their own colours. Dark scrims over photographs (`ink-950`) and controls drawn
on them (`cream-100`, white) are fixed colours, the same in either appearance.

#### Contrast (WCAG 2.1)

| Pair | Light | Dark |
| --- | --- | --- |
| `fg` on `canvas` / `surface` | 15.1 / 14.5 | 17.9 / 16.6 |
| `fg-muted` on `canvas` / `surface` | 4.74 / 4.54 | 8.23 / 7.61 |
| `accent` (text) on `canvas` / `surface` | 5.28 / 5.06 | 6.66 / 6.16 |
| white on `primary` / `primary-hover` | 4.58 / 5.28 | 4.58 / 5.28 |
| `danger` on `canvas` / `surface` | 5.54 / 5.30 | 7.10 / 6.57 |
| `success` on `canvas` | 5.14 | 9.98 |
| `wordmark` on `canvas` | 10.16 | 6.98 |
| `border-strong` on `canvas` (non-text) | 3.28 | 5.97 |

Every text pair passes AA. Two rules keep it that way: rose text uses `accent`
(`#CE2156`), never `primary` (`#E0245E` is 4.39:1 on `#FAFAFA`); and `fg-muted` sits
only on `canvas` or `surface`, never on `hover` or a tint. `#ED4956` (3.69:1) is for
icons and borders, so error text uses `danger`.

### Type

- **Display:** Fraunces Variable (`font-display`), optical sizing on, weight 400, slight negative tracking, balanced wrapping. Use for every heading and for large numerals. Italic (`<em>`) in `accent` for single-word emphasis.
- **Body:** Manrope Variable (`font-sans`), the default everywhere else. Common ligatures are off (see decisions).
- **Eyebrows:** `text-xs font-semibold uppercase tracking-[0.28em] text-highlight`, usually with a short rule. `SectionHeading` does this for you.
- Scale: page titles `text-5xl` to `text-7xl`, section titles `text-4xl` to `text-5xl`, card titles `text-2xl`, body `text-base` to `text-lg` with `leading-relaxed`.

Both fonts are bundled from `@fontsource-variable`; nothing loads from a font CDN.

### Motion

- Easing `ease-velvet` (`cubic-bezier(0.22, 0.61, 0.36, 1)`), slow duration 900 ms, base 300 ms.
- `.reveal`: fade up 18 px when scrolled into view (`useReveal` adds `.is-visible`). Stagger with `delay` 0 to 3 on `Reveal`.
- `.reveal-image`: a slow 1.4 s clip-and-fade for images.
- `prefers-reduced-motion: reduce` shows everything immediately and cuts transitions and animations to near zero.

### Layout

- Mobile first. Side padding `px-5` on phones and `px-8` from `sm`. Content widths come from `Section` (`narrow` 48rem, `default` 72rem, `wide` 80rem, `full`).
- Section rhythm `py-20 sm:py-28`. Use `tone` to alternate `canvas`, `surface` and `sunken` for editorial breaks.
- Heroes are full-bleed with an image (or texture) under a gradient to `canvas`.
- Touch targets are at least 44 px (`min-h-11`).

### Components (`frontend/src/components/ui`)

Import from `@/components/ui`.

#### Button and ButtonLink

```tsx
<Button onClick={save}>Save</Button>
<Button variant="ghost" size="lg">Cancel</Button>
<ButtonLink to="/visit">Plan a Visit</ButtonLink>
<ButtonLink to="https://example.org" variant="link">External</ButtonLink>
```

- Variants: `primary` (rose pill, one per view where possible), `ghost` (outlined pill, secondary action), `link` (underlined rose text).
- Corners come from the `--radius-control`, `--radius-card` and `--radius-field` tokens (`rounded-control` and so on). They are pills, 1 rem and 0.75 rem on the website; the member app squares them off to 8px.
- Sizes: `md` (44 px) and `lg` (48 px).
- `ButtonLink` uses the router for paths starting with `/` and a plain anchor with `rel="noopener noreferrer"` for `https:` and `mailto:` links.
- Disabled buttons use the native `disabled` attribute. Add `aria-disabled` when the label explains why (see Join).

#### Card

```tsx
<Card as="article" interactive>...</Card>
```

A rounded `surface` panel with a hairline border. `interactive` adds a subtle lift and stronger border on hover and focus-within. Put padding on the children so images can run edge to edge.

#### Section

```tsx
<Section tone="surface" width="narrow" spacing="tight" aria-labelledby="faq">...</Section>
```

Full-width band with a centred container. Give every section an accessible name, through `aria-labelledby` pointing at its heading or through `aria-label`.

#### SectionHeading

```tsx
<SectionHeading id="faq" eyebrow="Questions" title="Things people often ask" lede="..." />
```

Eyebrow, display heading and optional lede. `as` picks the heading level (default `h2`), and `align="center"` centres it.

#### ImageFrame

```tsx
<ImageFrame image="home-hero.webp" alt="" ratio="16/9" placeholder="velvet" />
<ImageFrame remote={opportunity.hero_image} alt="" fill placeholder="candle" />
```

The only way to render imagery.

- `image` is a filename from `docs/image-manifest.json`. A missing entry, or one with `faces_visible: true` and `consent_confirmed: false`, renders the placeholder texture instead. This rule cannot be bypassed from a page.
- `remote` takes an API image, which the server has already checked against the same rule. Public uploads come with `width`, `height` and a `srcset` (640, 1280 and the original), which the frame passes to the browser with `sizes`.
- Manifest images load from the public bucket in production (the server puts its address in a `rose-site-images` meta tag) and from `/images` in development.
- `placeholder` sets the texture used until a real image exists: `velvet`, `candle`, `silk`, `leather`, `shadow`, `architecture` or `rose`.
- The texture always sits under the image, so a frame whose picture is still loading (or waiting lazily below the fold) shows the texture, never a blank square the colour of the page.
- `ratio` (`1/1`, `4/5`, `4/3`, `3/2`, `16/9`, `21/9`) reserves space so nothing shifts on load. `fill` makes it cover its positioned parent instead.
- Use `alt=""` for decorative imagery, which is almost all of it.
- `priority` loads eagerly; use it only above the fold. `reveal={false}` turns off the scroll reveal.

#### Badge

```tsx
<Badge tone="brass">Beginner</Badge>
<Badge>Workshop</Badge>
```

Small uppercase pill. Tones: `neutral`, `rose`, `brass` (the names are historical; `rose` and `brass` both render in the rose accent now). Use it for metadata, not actions.

#### Checkbox

```tsx
<Checkbox name="photoshoot_acknowledged" label="Everyone photographed will consent..." checked={value} error={error} required onChange={...} />
```

A native checkbox with its label, an optional hint and an error, wired with `aria-describedby`. Use it for promises and opt-ins; checkbox groups (the volunteer form) are a `fieldset` with a `legend`.

#### Input, Textarea, Select

```tsx
<Input name="email" type="email" invalid={Boolean(error)} />
<Textarea name="message" rows={6} />
<Select options={[{ value: 'general', label: 'General' }]} />
```

Sunken fields with a 3:1 outline. `invalid` switches to the danger outline and sets `aria-invalid`. Always wrap them in `FormField`.

#### FormField

```tsx
<FormField label="Email" hint="We only use it to reply." error={errors.email} required>
  {(field) => <Input {...field} name="email" />}
</FormField>
```

Generates the id and wires up the label, hint and error with `aria-describedby`. The render prop passes `id`, `invalid`, `aria-describedby` and `aria-required`. Fields are optional unless marked `required`. Optional fields show an "Optional" tag; pass `optionalLabel=""` to hide it (as the filters do).

#### Modal

```tsx
<Modal open={open} onClose={() => setOpen(false)} title="Before you go" footer={<Button>OK</Button>}>
  ...
</Modal>
```

Built on native `<dialog>`, so focus trapping, focus return and Escape come built in. `variant="sheet"` makes it full screen (the mobile menu uses this). `size="wide"` widens a dialog for media (the journal post modal). `hideTitle` keeps the title for screen readers only. Clicking the backdrop closes it.

#### Toast

```tsx
const toast = useToast()
toast.show({ tone: 'error', title: 'Your message was not sent', message: 'Please try again.' })
```

`ToastProvider` wraps the app in `App.tsx`. Tones: `info`, `success`, `error`. Toasts announce through a polite live region, stack up to three, and dismiss after 7 seconds or on close. Use them for transient feedback; keep persistent errors inline.

### Layout components (`components/layout`)

- **QuickExit**: the Leave control. Variants `compact` (in the header at every width), `inline` (footer, menu) and `floating` (the age gate and the member app's loading screen, which have no header). It must appear on every page. It is never floated over page content.
- **AgeGate**: renders instead of the app until age is confirmed.
- **Header / Footer / Layout**: shared chrome. Navigation items live in `navigation.ts` as single links and groups (Visit: Plan Your Visit, Guests, FAQ; Get Involved: Volunteer, Donate, Rentals). The desktop nav appears from `xl`, with each group as a `NavDropdown`; below that the menu sheet lists the groups as headed sections. "Join" reads "Membership" for anyone whose account has, or has had, a membership (`Account.has_membership`). Header, footer and the Leave control are hidden when printing, so a receipt prints alone.
- **NavDropdown**: a disclosure button and a list of links. Enter, Space or Arrow Down opens it and focuses the first link; arrows, Home and End move; Escape closes and returns focus; Tab away or a click outside closes. Tested in `NavDropdown.test.tsx`.
- **SubscribeForm**: the footer's email list sign-up. One field, a honeypot, and the same "check your inbox" answer for every address. States: idle, sending (button disabled), sent, error (inline, announced politely).
- **Footer**: wordmark, tagline and the sign-up; address, email and social links from site settings; the navigation groups; the nonprofit line, Privacy, the staff-only Staff guide link and the Leave control.
- **AccountMenu**: "Log in" (with a `next` back to the current page), or the display name with a Lucide `User` icon and a small menu (My account, Log out). Closes on outside click, Escape and navigation.
- **AuthProvider / useAuth**: session state from `/api/account/session/`. `applySession()` takes the session returned by login, logout and account changes. Nothing is stored in browser storage.

### Content components (`components/content`)

#### Copy and CopyHeading

```tsx
const copy = usePageContent('visit')
<PageHero copy={copy} image="visit-hero.webp" placeholder="shadow" />
<CopyHeading copy={copy} prefix="expect" id="expect" />
<Copy copy={copy} k="id.body" lines={3} className="mt-4 text-fg-muted" />
{copy.items('steps').map((n) => <Copy key={n} copy={copy} k={`steps.${n}.title`} as="h3" />)}
```

Every heading and paragraph on a public page is staff-editable copy (`docs/content.md`). `Copy` renders one key: formatted values (already sanitised on the server) as HTML, with prose styles on block elements and accent italics inside headings; plain values keep their line breaks. While the page's copy loads it shows a skeleton of `lines` lines; a missing key renders nothing. Pages hold no stand-in text. `CopyHeading` is a `SectionHeading` fed from `${prefix}.eyebrow/title/lede`, and `PageHero` takes `copy` the same way.

#### StaffCard

`<StaffCard person={profile} />` shows a volunteer's display name, role and bio, with their photo only when the API sent one (consent rule), otherwise a monogram. `compact` drops the bio, for the strip on About. Never an email or account detail.

#### EventCard and DateBlock

```tsx
<EventCard event={event} headingLevel="h2" />
```

A card with a rose-edged date block (weekday, day, month in Chicago time), category and RSVP-state badges, time range, location and, only when staff enable it, the "N going" count. The whole card is clickable through the title link. Use `DateBlock` alone wherever a compact date is needed.

#### DetailItem

```tsx
<dl className="grid gap-5 sm:grid-cols-3">
  <DetailItem icon={CalendarDays} label="Date">Friday, October 23</DetailItem>
</dl>
```

One term and value with a Lucide icon, for the details row on event and class pages. The icon sits inside the `<dt>`, so every `<dt>`/`<dd>` pair is a direct child of its group and screen readers read the list correctly.

#### HeroLoading

`<HeroLoading label="Loading event" />` stands in for a page hero's badges, heading and summary while they load: about the same size, so nothing jumps when the content arrives. Pair it with a minimum height on the section below while loading, so the footer stays out of view.

#### MonthCalendar

```tsx
<MonthCalendar month={{ year: 2026, month: 10 }} events={events} onMonthChange={setMonth} />
```

A Sunday-first, six-week grid. On phones each event is a rose dot, and from `sm` it is a truncated title chip. Always pair it with a list of the same events underneath, which is what phone and screen-reader users read. Month maths lives in `lib/calendar.ts`.

#### RSVPPanel

```tsx
<RSVPPanel event={event} onChange={(rsvp) => setRsvp(rsvp)} />
```

Covers every state: signed out (log in or register, returning to this page), unverified (resend link), open, waitlist, full, closed, opens soon, members only (an inline `PaywallPanel`), going and waitlisted (update, cancel with confirmation, and "Add to calendar" with an unticked "include details" box). The submit button disables and relabels while saving. Errors go to a toast.

#### Carousel

```tsx
<Carousel images={post.images} label="Post images" />
```

One square image at a time. Previous and next buttons, arrow keys when focused, and touch swipe (a 40 px threshold). Slides are announced as "Image 2 of 3" through a polite live region. It holds no autoplay and no timers.

#### PostView and JournalTile

`PostView` is the shared layout for the journal modal and the permalink page: the carousel, then author and relative date, the sanitised caption, and an RSVP button (linked event) or the post's CTA. `JournalTile` is a square, Instagram-style grid tile with a Lucide `Layers` icon on multi-image posts. Use them in a `grid-cols-3` grid with tight gaps (`gap-0.5` on phones, up to `gap-2`).

### Membership (`components/membership`)

#### PaywallPanel

```tsx
<PaywallPanel
  title="For members"
  benefit="Members-only classes come with membership."
  tiers={opportunity.paywall?.tiers}
/>
<PaywallPanel variant="inline" headingLevel="h3" title="For members" benefit="..." />
```

The one way the site says "this comes with membership". It reads the session and picks its
actions itself:

| Viewer | Actions |
| --- | --- |
| Signed out | "Log in" (returning to this page) and "Create an account" (then on to `/join`) |
| Signed in, never a member | "Become a member" to `/join` |
| Has, or had, a membership | "See my membership" to `/account#membership`, with a line that the current membership does not include this or is not active |

`tiers` adds "Included with Monthly and Annual memberships." `variant="card"` (default)
stands alone in a `Card`; `variant="inline"` sits inside another card, as in the RSVP panel.
Use it on the opportunity page for locked classes, in the RSVP panel for members-only
evenings and on `/account` where the member community would be. Never show locked content
behind it: the server withholds the body and the call to action, and the panel is only the
explanation. Copy says what membership adds; it never says what someone lacks.

#### ReferenceCode

```tsx
<ReferenceCode code="R7K-42Q" size="lg" />
```

The reference code in large monospaced type next to a QR code generated on the device
(the `qrcode` package, loaded on demand). Nothing about the code is sent to a third party.
Codes use an alphabet without look-alikes (no 0, O, 1, I or L) so they survive being read
aloud.

#### Join flow and account card

`pages/join/` holds the three-step join (Choose, Agreement, Payment), the confirmation with
what to bring, the "Confirming" page that polls after an online checkout, and the
development-only sandbox checkout. The agreement box must be scrolled to the end before the
"I have read and agree" box enables, and the typed name enables the button. The account
`MembershipCard` shows tier, status badge, period line, code and QR, the auto-renew switch
(online memberships only), payments with Receipt links, and Cancel behind a
`ConfirmDialog`. Receipts (`/account/receipts/:id`) are a print-friendly page.

## Member app

Everything under `/members/*`, shown only to people who pass `can_view_feed`, in its own
shell (`components/members/app/AppShell`). It never renders the website header or footer.
Anyone else gets the website's ordinary 404, and the loading state looks like the website,
so nothing hints that the app exists.

### Look

- **Scope.** `.ig-app` on the shell's root sets the system stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`) at 14px, weights 400 and 600 only, 8px corners on shared controls (`--radius-control`, `--radius-card`, `--radius-field`). Colours are the shared palette. Fraunces appears only in the "Rose" wordmark (`font-wordmark`, `text-wordmark`).
- **Sizes.** 14px base, 12px meta, 16px titles. Buttons are 32px tall with 8px corners (`IgButton`: `primary` rose, `secondary` grey, `plain` rose text). 1px borders. Shadows only on modals and menus (`var(--ui-shadow)`). Avatars are circles.
- **Icons.** Lucide at 24px with a 1.75 stroke (`ICON` in `app/ui.ts`); active items get a 2.5 stroke and a 600 label. Home `House`, Search `Search`, Explore `Compass`, Notifications `Heart`, Create `SquarePlus`, Profile the avatar, More `Menu`. No Instagram name, logo, gradient, glyphs or assets.
- **Motion.** 150 to 200ms ease-out; the liked heart pops (`animate-like-pop`), a double-tap shows a 600ms heart burst (`animate-heart-burst`), panels slide in (`animate-panel-in`), story bars fill linearly (`animate-story-progress`). Reduced motion stops the story timer and cuts animations.

### Shell (`app/AppShell`, `app/Nav`)

| Width | Navigation |
| --- | --- |
| 1264px and up | Fixed left sidebar, 245px: wordmark, Home, Search, Explore, Notifications, Create, Profile; More at the bottom (Settings, Appearance, Website, Log out); **Leave** last. Rows 48px, 12px between icon and label. |
| 768 to 1263px | The same sidebar collapsed to 72px, icons only, with the rose mark for the wordmark. It also collapses while the Search or Notifications panel is open. |
| Under 768px | A 44px top bar (wordmark; Notifications and the quick-exit `LogOut` on the right) and a 50px bottom tab bar plus the safe-area inset (Home, Search, Create, Explore, Profile). |

- **Panels.** On tablets and desktops Search and Notifications open as a 397px panel beside the sidebar (Escape or a click outside closes it); on phones they are pages (`/members/search`, `/members/notifications`).
- **Columns.** Feed and post pages are at most 470px, centred in the space right of the sidebar. Profile, Explore and Saved grids are at most 935px.
- **Right rail** (`app/RightRail`), Home only, from 1160px, 320px: your mini profile, "Coming up" (the next three events), "From the club" (the two latest journal posts), and Website and Privacy links. There is no "Suggested for you": suggesting members to each other would reveal who is here.
- **Quick exit** and double-Esc work on every page: the sidebar's last item, the phone top bar's `LogOut`.

### Screens

- **Home** (`pages/members/FeedPage`): the stories tray, then Following and Everyone tabs (`GET /api/members/home/`), with journal posts shown as the club's "Rose" account, interleaved by date.
- **Stories** (`app/Stories`): staff-made circles only (Tonight, This week, Journal, News), 64px with the ring on phones and 66px wider; the tabs sit 8px under their labels. Unseen circles get a rose ring, seen ones grey, tracked per member. The viewer is full screen with a progress bar per item; tap the left third or the right of the screen, or use the arrow keys; the button at the bottom (RSVP, Learn more) opens the website page.
- **Post detail** (`app/PostDetail`): on tablets and desktops a modal over the current page (`?post=<id>`), the media as large as fits on the left and a 335px panel on the right (header, scrolling caption and comments, action row, likes and time, comment box pinned at the bottom). Escape or a click outside closes it; the arrow keys step through the list it was opened from. On phones, the page `/members/p/:id`.
- **Profile** (`pages/members/MemberProfilePage`): one grid whose areas move with the width. Phones: the 77px avatar with the posts count (a number over "posts") centred beside it, then the name (600), bio and join date, then the buttons side by side filling the width. From 768px: avatar 150px on the left, the name, Edit profile and Settings (your own) or Follow, Mute and options (others), **posts count only**, the bio, then Posts and, on your own profile only, Saved (`/members/u/:handle/saved`; `/members/saved` redirects there).
- **Grids** (`app/PostGrid`): three columns of 3:4 tiles with 2px gaps, edge to edge on phones, a `Copy` icon on multi-photo posts and a soft dark overlay on hover with a mouse (never counts). Explore (`/members/explore`) shows Everyone posts this way.
- **Create** (`app/CreatePost`): a centred modal on tablets and desktops, a full-screen sheet on phones. Select, then Crop & redact, then Details (order and describe, caption, sensitive and comments toggles, the consent attestation), then Share. The header has Back (or Close), the step title and Next (Share on the last step, disabled until the attestation is ticked when there are photos).
- **Settings** (`/members/settings`): Edit profile, Appearance, Always show sensitive posts, Show me in search, Blocked, Step away from the feed, Export my data, Leave and erase, and a link to the website account page.

#### PostCard (`app/PostCard`)

```tsx
<PostCard post={post} listIds={ids} />
```

One component for member and club posts, top to bottom:

1. **Header, 54px:** 32px avatar, name (14/600), "•" and relative time, and `Ellipsis` opening the actions as a centred `ActionSheet` (Report, Mute, Block for others; Edit, Delete for the author).
2. **Media:** full column width, shaped by the first image and clamped between 4:5 and 1.91:1 (`mediaRatio`), a carousel with dots and, with a mouse, arrows on hover. Sensitive blur and watermark as before. Double-tap or double-click likes (never unlikes) with a heart burst.
3. **Action row, 46px:** `Heart`, `MessageCircle`, and `Bookmark` on the right. No share or send.
4. **Likes line:** the author sees "N likes" (plain text, no list); everyone else sees "Liked by you" if they liked it, otherwise nothing.
5. **Caption:** the name in 600, then the caption, two lines then "more".
6. **Comments:** "View all N comments" (opens the post), then the two newest.
7. **Time:** 12px secondary, months only after seven days.
8. **Comment box:** "Add a comment…" with Post, which turns rose when there is text.

Club posts have no likes, comments, saves or actions: their action row is the website link (RSVP, the post's own button, or "Read on the website"). Changes made anywhere (like, save, edit, comment, delete) go through `updatePost` in the members context, so every list and the post view agree.

#### SensitiveBlur

Wraps sensitive images in a heavy blur with an `EyeOff` icon and a View button. The blurred content is `aria-hidden` until revealed. The API decides whether to blur (`post.blur`), honouring the viewer's "always show sensitive posts" setting.

#### RedactionEditor

Six tools: Cover (solid fill), Pixelate, Crop, Rotate, Undo and Reset. The member drags on the photo to place rectangles. The preview and the upload come from the same `renderRedacted` pipeline in `lib/redact.ts`, so what members see is exactly what gets uploaded, and the original never leaves the device.

#### Toggle, ActionSheet, ConfirmDialog, ReportDialog, EditProfileDialog

`Toggle` is a labelled switch on a native checkbox. `ActionSheet` is a centred dialog of full-width rows with Cancel last. `ConfirmDialog` is a two-button Modal for destructive actions. `ReportDialog` offers the six reasons as radios, requires detail for "Something else", and only ever answers "Thanks, our team will review this." `EditProfileDialog` changes the picture and bio.

#### Image protection

Member images block the context menu, dragging and the iOS long-press callout. It is a deterrent, not a control; the watermark is what traces leaks.

## Testing

Component tests live next to their components (`*.test.tsx`) and use `renderWithProviders()` from `src/test/render.tsx`, which supplies the router, auth context and toasts. Run them with `npm test`.

## Staff admin

The admin (Django) has its own look, in `backend/apps/core/static/core/ig-admin.css` and
`templates/admin/base_site.html`: a clean photo-app style with a white (or black, in dark
appearance) canvas, the system font, hairline borders and blue primary buttons. A fixed
sidebar on the left holds outline icons (Lucide, built into
`static/core/icons.svg`) with plain labels; the current page is bold, a red number on an
icon counts what is waiting, a red dot means "something needs you". It is 245 px wide
with labels from 1264 px, a 73 px icon rail below that and a 56 px rail on phones,
always on the left. **Settings** (gear) sits at the bottom left and opens its menu
upwards. The home page is one centred column of post-style cards. Nothing uses inline
styles or scripts, so the strict CSP stays as it is. The site's own name is used; no
other brand's logo or name.

