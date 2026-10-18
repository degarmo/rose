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

- Variants: `primary` (oxblood pill, one per view where possible), `ghost` (outlined pill, secondary action), `link` (underlined text with a brass underline).
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
- `remote` takes an API image, which the server has already checked against the same rule.
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
- **Header / Footer / Layout**: shared chrome. Navigation items live in `navigation.ts`. The desktop nav appears from `xl`; below that the menu sheet is used.
- **AccountMenu**: "Log in" (with a `next` back to the current page), or the display name with a Lucide `User` icon and a small menu (My account, Log out). Closes on outside click, Escape and navigation.
- **AuthProvider / useAuth**: session state from `/api/account/session/`. `applySession()` takes the session returned by login, logout and account changes. Nothing is stored in browser storage.

## Content components (`components/content`)

### EventCard and DateBlock

```tsx
<EventCard event={event} headingLevel="h2" />
```

A card with a brass-edged date block (weekday, day, month in Chicago time), category and RSVP-state badges, time range, location and, only when staff enable it, the "N going" count. The whole card is clickable through the title link. Use `DateBlock` alone wherever a compact date is needed.

### MonthCalendar

```tsx
<MonthCalendar month={{ year: 2026, month: 10 }} events={events} onMonthChange={setMonth} />
```

A Sunday-first, six-week grid. On phones each event is a rose dot, and from `sm` it is a truncated title chip. Always pair it with a list of the same events underneath, which is what phone and screen-reader users read. Month maths lives in `lib/calendar.ts`.

### RSVPPanel

```tsx
<RSVPPanel event={event} onChange={(rsvp) => setRsvp(rsvp)} />
```

Covers every state: signed out (log in or register, returning to this page), unverified (resend link), open, waitlist, full, closed, opens soon, members only (disabled button), going and waitlisted (update, cancel with confirmation, and "Add to calendar" with an unticked "include details" box). The submit button disables and relabels while saving. Errors go to a toast.

### Carousel

```tsx
<Carousel images={post.images} label="Post images" />
```

One square image at a time. Previous and next buttons, arrow keys when focused, and touch swipe (a 40 px threshold). Slides are announced as "Image 2 of 3" through a polite live region. It holds no autoplay and no timers.

### PostView and JournalTile

`PostView` is the shared layout for the journal modal and the permalink page: the carousel, then author and relative date, the sanitised caption, and an RSVP button (linked event) or the post's CTA. `JournalTile` is a square, Instagram-style grid tile with a Lucide `Layers` icon on multi-image posts. Use them in a `grid-cols-3` grid with tight gaps (`gap-0.5` on phones, up to `gap-2`).

## Testing

Component tests live next to their components (`*.test.tsx`) and use `renderWithProviders()` from `src/test/render.tsx`, which supplies the router, auth context and toasts. Run them with `npm test`.
