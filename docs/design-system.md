# Design system

Private members' club after dark: near-black, oxblood, blush, cream, a touch of brass.
Quiet, slow and confident. Dark is the only theme, but every colour is a token.

Tokens live in `frontend/src/index.css` inside `@theme`, which exposes them both as CSS
variables (`var(--color-fg)`) and as Tailwind utilities (`text-fg`, `bg-surface`).
Components use the **semantic** tokens; primitives exist so the palette can change in one place.

## Colour

| Semantic token | Primitive | Hex | Use |
| --- | --- | --- | --- |
| `canvas` | `ink-950` | `#0D0A0B` | Page background |
| `surface` | `ink-900` | `#151012` | Cards, panels |
| `surface-raised` | `ink-800` | `#1E1719` | Toasts, image wells |
| `surface-sunken` | | `#090708` | Footer, form fields |
| `border` | `ink-600` | `#3A2C2F` | Decorative dividers |
| `border-strong` | `ink-500` | `#6B5A57` | Form field and ghost button outlines |
| `fg` | `cream-100` | `#F2E8DA` | Primary text |
| `fg-muted` | `cream-300` | `#BFB1A3` | Body copy, secondary text |
| `fg-subtle` | `cream-500` | `#8F8279` | Captions, small print |
| `primary` | `oxblood-700` | `#7B1E2E` | Primary buttons |
| `primary-hover` | `oxblood-600` | `#922638` | Primary hover |
| `primary-deep` | `oxblood-900` | `#4A1019` | Pressed state, tinted callouts |
| `on-primary` | `cream-100` | `#F2E8DA` | Text on primary |
| `accent` | `blush-200` | `#E6BDB5` | Links, emphasis, italics |
| `rose` | `rose-300` | `#D4848F` | Concern notices, rose badges |
| `highlight` | `brass-400` | `#C29B62` | Eyebrows, icons, focus rings, rules. Small doses only. |
| `danger` | `red-300` | `#F08C8C` | Errors |
| `success` | `green-300` | `#9CC5A1` | Confirmations |

### Contrast (WCAG 2.1)

Measured against `canvas`; ratios against `surface-raised` are 5 to 10 percent lower and still pass.

| Pair | Ratio | Passes |
| --- | --- | --- |
| `fg` on `canvas` | 16.3 : 1 | AAA |
| `fg-muted` on `canvas` | 9.4 : 1 | AAA |
| `fg-subtle` on `canvas` | 5.3 : 1 | AA (4.7 : 1 on `surface-raised`) |
| `accent` on `canvas` | 11.6 : 1 | AAA |
| `rose` on `canvas` | 7.0 : 1 | AAA |
| `highlight` on `canvas` | 7.7 : 1 | AAA |
| `danger` on `canvas` | 8.3 : 1 | AAA |
| `on-primary` on `primary` | 8.4 : 1 | AAA |
| `on-primary` on `primary-hover` | 6.8 : 1 | AA |
| `border-strong` on `canvas` (non-text) | 3.0 : 1 | AA for UI components |

Do not put `fg-subtle` text on anything lighter than `surface-raised`.

## Type

- **Display:** Fraunces Variable (`font-display`), optical sizing on, weight 400, slight negative tracking, balanced wrapping. Use for every heading and for large numerals. Italic (`<em>`) in `accent` for single-word emphasis.
- **Body:** Manrope Variable (`font-sans`), the default everywhere else. Common ligatures are off (see decisions).
- **Eyebrows:** `text-xs font-semibold uppercase tracking-[0.28em] text-highlight`, usually with a short brass rule. `SectionHeading` does this for you.
- Scale: page titles `text-5xl` to `text-7xl`, section titles `text-4xl` to `text-5xl`, card titles `text-2xl`, body `text-base` to `text-lg` with `leading-relaxed`.

Both fonts are bundled from `@fontsource-variable`; nothing loads from a font CDN.

## Motion

- Easing `ease-velvet` (`cubic-bezier(0.22, 0.61, 0.36, 1)`), slow duration 900 ms, base 300 ms.
- `.reveal`: fade up 18 px when scrolled into view (`useReveal` adds `.is-visible`). Stagger with `delay` 0 to 3 on `Reveal`.
- `.reveal-image`: a slow 1.4 s clip-and-fade for images.
- `prefers-reduced-motion: reduce` shows everything immediately and cuts transitions and animations to near zero.

## Layout

- Mobile first. Side padding `px-5` on phones and `px-8` from `sm`. Content widths come from `Section` (`narrow` 48rem, `default` 72rem, `wide` 80rem, `full`).
- Section rhythm `py-20 sm:py-28`. Use `tone` to alternate `canvas`, `surface` and `sunken` for editorial breaks.
- Heroes are full-bleed with an image (or texture) under a gradient to `canvas`.
- Touch targets are at least 44 px (`min-h-11`).

## Components (`frontend/src/components/ui`)

Import from `@/components/ui`.

### Button and ButtonLink

```tsx
<Button onClick={save}>Save</Button>
<Button variant="ghost" size="lg">Cancel</Button>
<ButtonLink to="/visit">Plan a Visit</ButtonLink>
<ButtonLink to="https://example.org" variant="link">External</ButtonLink>
```

- Variants: `primary` (oxblood pill, one per view where possible), `ghost` (outlined pill, secondary action), `secondary` (filled with `primary-deep`; the grey button of the members area), `link` (underlined text with a brass underline).
- Corners come from the `--radius-control`, `--radius-card` and `--radius-field` tokens (`rounded-control` and so on). They are pills, 1 rem and 0.75 rem on the public site; the members area squares them off.
- Sizes: `md` (44 px) and `lg` (48 px).
- `ButtonLink` uses the router for paths starting with `/` and a plain anchor with `rel="noopener noreferrer"` for `https:` and `mailto:` links.
- Disabled buttons use the native `disabled` attribute. Add `aria-disabled` when the label explains why (see Join).

### Card

```tsx
<Card as="article" interactive>...</Card>
```

A rounded `surface` panel with a hairline border. `interactive` adds a subtle lift and stronger border on hover and focus-within. Put padding on the children so images can run edge to edge.

### Section

```tsx
<Section tone="surface" width="narrow" spacing="tight" aria-labelledby="faq">...</Section>
```

Full-width band with a centred container. Give every section an accessible name, through `aria-labelledby` pointing at its heading or through `aria-label`.

### SectionHeading

```tsx
<SectionHeading id="faq" eyebrow="Questions" title="Things people often ask" lede="..." />
```

Eyebrow, display heading and optional lede. `as` picks the heading level (default `h2`), and `align="center"` centres it.

### ImageFrame

```tsx
<ImageFrame image="home-hero.webp" alt="" ratio="16/9" placeholder="velvet" />
<ImageFrame remote={opportunity.hero_image} alt="" fill placeholder="candle" />
```

The only way to render imagery.

- `image` is a filename from `docs/image-manifest.json`. A missing entry, or one with `faces_visible: true` and `consent_confirmed: false`, renders the placeholder texture instead. This rule cannot be bypassed from a page.
- `remote` takes an API image, which the server has already checked against the same rule. Public uploads come with `width`, `height` and a `srcset` (640, 1280 and the original), which the frame passes to the browser with `sizes`.
- Manifest images load from the public bucket in production (the server puts its address in a `rose-site-images` meta tag) and from `/images` in development.
- `placeholder` sets the texture used until a real image exists: `velvet`, `candle`, `silk`, `leather`, `shadow`, `architecture` or `rose`.
- `ratio` (`1/1`, `4/5`, `4/3`, `3/2`, `16/9`, `21/9`) reserves space so nothing shifts on load. `fill` makes it cover its positioned parent instead.
- Use `alt=""` for decorative imagery, which is almost all of it.
- `priority` loads eagerly; use it only above the fold. `reveal={false}` turns off the scroll reveal.

### Badge

```tsx
<Badge tone="brass">Beginner</Badge>
<Badge>Workshop</Badge>
```

Small uppercase pill. Tones: `neutral`, `rose`, `brass`. Use it for metadata, not actions.

### Input, Textarea, Select

```tsx
<Input name="email" type="email" invalid={Boolean(error)} />
<Textarea name="message" rows={6} />
<Select options={[{ value: 'general', label: 'General' }]} />
```

Sunken fields with a 3:1 outline. `invalid` switches to the danger outline and sets `aria-invalid`. Always wrap them in `FormField`.

### FormField

```tsx
<FormField label="Email" hint="We only use it to reply." error={errors.email} required>
  {(field) => <Input {...field} name="email" />}
</FormField>
```

Generates the id and wires up the label, hint and error with `aria-describedby`. The render prop passes `id`, `invalid`, `aria-describedby` and `aria-required`. Fields are optional unless marked `required`. Optional fields show an "Optional" tag; pass `optionalLabel=""` to hide it (as the filters do).

### Modal

```tsx
<Modal open={open} onClose={() => setOpen(false)} title="Before you go" footer={<Button>OK</Button>}>
  ...
</Modal>
```

Built on native `<dialog>`, so focus trapping, focus return and Escape come built in. `variant="sheet"` makes it full screen (the mobile menu uses this). `size="wide"` widens a dialog for media (the journal post modal). `hideTitle` keeps the title for screen readers only. Clicking the backdrop closes it.

### Toast

```tsx
const toast = useToast()
toast.show({ tone: 'error', title: 'Your message was not sent', message: 'Please try again.' })
```

`ToastProvider` wraps the app in `App.tsx`. Tones: `info`, `success`, `error`. Toasts announce through a polite live region, stack up to three, and dismiss after 7 seconds or on close. Use them for transient feedback; keep persistent errors inline.

## Layout components (`components/layout`)

- **QuickExit**: the Leave control. Variants `floating` (large screens), `compact` (phone header) and `inline` (footer, menu). It must appear on every page.
- **AgeGate**: renders instead of the app until age is confirmed.
- **Header / Footer / Layout**: shared chrome. Navigation items live in `navigation.ts`. The desktop nav appears from `xl`; below that the menu sheet is used. "Join" reads "Membership" for anyone whose account has, or has had, a membership (`Account.has_membership`). Header, footer and the Leave control are hidden when printing, so a receipt prints alone.
- **AccountMenu**: "Log in" (with a `next` back to the current page), or the display name with a Lucide `User` icon and a small menu (My account, Log out). Closes on outside click, Escape and navigation.
- **AuthProvider / useAuth**: session state from `/api/account/session/`. `applySession()` takes the session returned by login, logout and account changes. Nothing is stored in browser storage.

## Content components (`components/content`)

### EventCard and DateBlock

```tsx
<EventCard event={event} headingLevel="h2" />
```

A card with a brass-edged date block (weekday, day, month in Chicago time), category and RSVP-state badges, time range, location and, only when staff enable it, the "N going" count. The whole card is clickable through the title link. Use `DateBlock` alone wherever a compact date is needed.

### DetailItem

```tsx
<dl className="grid gap-5 sm:grid-cols-3">
  <DetailItem icon={CalendarDays} label="Date">Friday, October 23</DetailItem>
</dl>
```

One term and value with a Lucide icon, for the details row on event and class pages. The icon sits inside the `<dt>`, so every `<dt>`/`<dd>` pair is a direct child of its group and screen readers read the list correctly.

### HeroLoading

`<HeroLoading label="Loading event" />` stands in for a page hero's badges, heading and summary while they load: about the same size, so nothing jumps when the content arrives. Pair it with a minimum height on the section below while loading, so the footer stays out of view.

### MonthCalendar

```tsx
<MonthCalendar month={{ year: 2026, month: 10 }} events={events} onMonthChange={setMonth} />
```

A Sunday-first, six-week grid. On phones each event is a rose dot, and from `sm` it is a truncated title chip. Always pair it with a list of the same events underneath, which is what phone and screen-reader users read. Month maths lives in `lib/calendar.ts`.

### RSVPPanel

```tsx
<RSVPPanel event={event} onChange={(rsvp) => setRsvp(rsvp)} />
```

Covers every state: signed out (log in or register, returning to this page), unverified (resend link), open, waitlist, full, closed, opens soon, members only (an inline `PaywallPanel`), going and waitlisted (update, cancel with confirmation, and "Add to calendar" with an unticked "include details" box). The submit button disables and relabels while saving. Errors go to a toast.

### Carousel

```tsx
<Carousel images={post.images} label="Post images" />
```

One square image at a time. Previous and next buttons, arrow keys when focused, and touch swipe (a 40 px threshold). Slides are announced as "Image 2 of 3" through a polite live region. It holds no autoplay and no timers.

### PostView and JournalTile

`PostView` is the shared layout for the journal modal and the permalink page: the carousel, then author and relative date, the sanitised caption, and an RSVP button (linked event) or the post's CTA. `JournalTile` is a square, Instagram-style grid tile with a Lucide `Layers` icon on multi-image posts. Use them in a `grid-cols-3` grid with tight gaps (`gap-0.5` on phones, up to `gap-2`).

## Membership (`components/membership`)

### PaywallPanel

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

### ReferenceCode

```tsx
<ReferenceCode code="R7K-42Q" size="lg" />
```

The reference code in large monospaced type next to a QR code generated on the device
(the `qrcode` package, loaded on demand). Nothing about the code is sent to a third party.
Codes use an alphabet without look-alikes (no 0, O, 1, I or L) so they survive being read
aloud.

### Join flow and account card

`pages/join/` holds the three-step join (Choose, Agreement, Payment), the confirmation with
what to bring, the "Confirming" page that polls after an online checkout, and the
development-only sandbox checkout. The agreement box must be scrolled to the end before the
"I have read and agree" box enables, and the typed name enables the button. The account
`MembershipCard` shows tier, status badge, period line, code and QR, the auto-renew switch
(online memberships only), payments with Receipt links, and Cancel behind a
`ConfirmDialog`. Receipts (`/account/receipts/:id`) are a print-friendly page.

## Members area (`components/members`)

The logged-in members area (`/members/*`) has a photo-app look of its own; the public site and `/account` keep the site's design.

- **Scope.** `MembersLayout` puts `.ig-app` on its root. `index.css` redefines the colour, font and corner tokens inside `.ig-app` only: white or black canvas, the system font, blue `primary` (#0067d1), grey `primary-deep`, hairline borders, 8 px corners. The shared components (Button, Card, Modal, fields) pick this up through the tokens, so no component forks. Image placeholders turn plain grey there.
- **Appearance.** Light or dark follows the device. Settings > Appearance cycles Automatic, Light and Dark, kept in this browser only (`members-appearance` in localStorage, via `components/members/appearance.ts`), and set as `data-theme` on the same root.
- **Sidebar** (`MembersSidebar`, nav "Members"). It is fixed on the left at every width: 245 px with labels from the `wide` breakpoint (79 rem, 1264 px), a 73 px icon rail from `md`, and 56 px on phones. From the top: the "Rose" logo (an R mark on the rail), **Leave** in red (always in view), Home, Search, Create (opens the composer; disabled while posting is paused), Notifications (heart with a red unread count) and Profile (the member's avatar). **Settings** (gear) sits at the bottom left and opens upwards: Your account, Appearance, Community guidelines, Back to the website, Log out, Leave this site now. The menu closes on outside click, Escape and navigation.
- **Content** is one centred column (630 px; posts 470 px). The Feed has Following and Everyone text tabs. Search, Notifications and the post page use plain rows. A profile is a large avatar beside the handle, its buttons, bio and join month, then a Posts tab over a three-column grid.
- **Unchanged look:** while loading, and for anyone without access (who gets the site's ordinary 404), the page looks like the rest of the site, so nothing hints that the area exists.

### PostCard

```tsx
<PostCard post={post} onChange={(next) => update(post.id, next)} />
```

A borderless post with a hairline under it: avatar, handle · relative time (or "Mar 2026" for anything older than a week), the image carousel with image protection, then a heart (optimistic like) and a speech bubble (comments), the like count for the author only, the caption led by the handle in bold with a "more" toggle after two lines, and "View all N comments". The overflow menu offers Report, Mute and Block to viewers, and Edit and Delete to the author; Block and Delete confirm first. `onChange(null)` removes the card from its list.

### SensitiveBlur

Wraps sensitive images in a heavy blur with an `EyeOff` icon and a View button. The blurred content is `aria-hidden` until revealed. The API decides whether to blur (`post.blur`), honouring the viewer's "always show sensitive posts" setting.

### Composer and RedactionEditor

A full-screen sheet in four steps: choose photos, cover anything identifying, order and describe, caption and post. The step bar marks the current step with `aria-current="step"`. The footer stays pinned while the middle scrolls. Post stays disabled until the consent attestation is ticked whenever there are photos.

`RedactionEditor` has six tools: Cover (solid fill), Pixelate, Crop, Rotate, Undo and Reset. The user drags on the photo to place rectangles. The preview and the upload come from the same `renderRedacted` pipeline in `lib/redact.ts`, so what members see is exactly what gets uploaded, and the original never leaves the device.

### Toggle, OverflowMenu, ConfirmDialog, ReportDialog

`Toggle` is a labelled switch on a native checkbox. `OverflowMenu` is a small menu that closes on outside click, Escape and selection. `ConfirmDialog` is a two-button Modal for destructive actions. `ReportDialog` offers the six reasons as radios, requires detail for "Something else", and only ever answers "Thanks, our team will review this."

### Image protection

`ImageFrame` and `Carousel` take `protect`, which blocks the context menu, dragging and the iOS long-press callout on member images. It is a deterrent, not a control; the watermark is what traces leaks.

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

