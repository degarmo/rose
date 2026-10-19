# Design tokens

Every value the Rose designs use, read from the inline styles in `source/`. The **Token**
column is the name in `frontend/src/index.css`: the colour is a `--ui-*` variable, and in
Tailwind it is `bg-<token>`, `text-<token>` or `border-<token>`. **Used in** gives the design
file and the place it appears: DS is `Rose Design System.dc.html`, Site is
`Rose Public Site.dc.html`, App is `Rose Member App.dc.html`, Card is `Post Card.dc.html`.

Contrast ratios are WCAG 2.1 ratios, measured on the background named.

## Colour

### Neutrals

| Token | Light | Dark | Used in |
| --- | --- | --- | --- |
| `canvas` | `#FFFFFF` | `#0A0A0A` | Page background everywhere: site pages, app pages, cards, inputs, sheets. Dark is the App "Home dark" screens. |
| `surface` | `#FAFAFA` | `#141414` | Site: "This week" band, "Get involved" cards, the Join step 2 tier summary. App: nav hover, search-row hover. DS: "Surface, alternate sections". |
| `blush` | `#FAF7F8` | `#1A1416` | Site: age gate backdrop, paywall panel, Visit photo-ID callout, Contact success panel, Join step 3 door reference. DS: "Blush surface, paywall, confirmation". |
| `fg` | `#262626` | `#FAFAFA` | All body text, the outline-button border, active tab underline, active filter chip, "Members only" badge, the text cursor in phone search. 14.7:1 on white. |
| `fg-muted` | `#737373` | `#A3A3A3` | Secondary text: leads, meta, timestamps, inactive tabs, Leave text, placeholders, footer copy. 4.7:1 on white, 4.5:1 on `surface`. |
| `fg-muted-tint` | `#6B6B6B` | `#A3A3A3` | Secondary text placed on `blush` or `tint` (paywall note, photo-ID callout, door reference): `#737373` measures 4.45:1 on `#FAF7F8`, below AA, so these take a step darker (5.1:1). |
| `fg-faint` | `#A3A3A3` | `#737373` | App right-rail footer links and copyright (11px; decorative small print, also links reachable elsewhere). Disabled button text. |
| `border` | `#DBDBDB` | `#262626` | Every 1px divider, card and input border, secondary button border, unseen-story ring when seen, carousel dots. |
| `control` | `#F0F0F0` | `#262626` | App secondary button ("Edit profile", "Settings"), the "Full" badge background, disabled buttons (DS "Disabled"). |
| `field` | `#EFEFEF` | `#262626` | App search field (Explore, Search panel, phone search). |
| `dot` | `#DBDBDB` | `#404040` | Card: inactive carousel dots. |

### Rose

| Token | Light | Dark | Used in |
| --- | --- | --- | --- |
| `primary` | `#CE2156` | `#CE2156` | Primary button fill (Site 48px pill, App 32px), Join, RSVP CTA, checked checkbox, toggle on, "Going" badge, active Join step, unseen story ring, active carousel dot. White on it: 5.2:1. |
| `primary-hover` | `#A3123F` | `#A3123F` | DS "Rose deep": link and button hover. |
| `link` | `#CE2156` | `#E0527D` | Text links ("All events", "See roles →", "Edit", "Clear all", "Post", "Next", "Done", "Required"), the date name over event cards, the step number "01" on Visit. Dark `#E0527D` is DS "Rose (dark), links on dark", 5.4:1 on `#0A0A0A`. |
| `tint` | `#FDEEF2` | `#2A1218` | "Open" badge, App right-rail date tiles, today in the month calendar. |
| `tint-fg` | `#A3123F` | `#F1A6BD` | Text on `tint`: 6.9:1 (light), 9.1:1 (dark). |
| `wordmark` | `#5A0F23` | `#F1D9DF` | The "Rose" wordmark only (Site header and footer, App sidebar and top bar, age gate), and the paywall and photo-ID icons. |
| `oxblood` | `#5A0F23` | `#5A0F23` | Fixed oxblood: the values band (Site home) and the club's "R" avatar in the app. |
| `on-oxblood` | `#F1D9DF` | `#F1D9DF` | Text on `oxblood` (10.3:1). |
| `tier-selected` | `#FFFBFC` | `#1A1416` | Site Join step 1: the highlighted tier card. |

### Status

| Token | Light | Dark | Used in |
| --- | --- | --- | --- |
| `danger` | `#C62828` | `#F87171` | Field error border (1.5px) and message (13px), "Report to hosts", "Leave and erase". 5.6:1 on white; 7.2:1 on `#0A0A0A`. |
| Open (`Badge tone="open"`) | `tint` / `tint-fg` | same | Badge "Open". The design's "· 14 spots" is not shown (decision 349). |
| `wait` / `wait-fg` | `#FFF4DE` / `#7A4E00` | `#2B2210` / `#F5C76B` | Badge "Waitlist" (6.6:1). |
| `control` / `full-fg` | `#F0F0F0` / `#5A5A5A` | `#262626` / `#A3A3A3` | Badge "Full" (6.1:1). |
| Members (`Badge tone="members"`) | `fg` / `canvas` | same | Badge "Members only" (inverted). |
| Going (`Badge tone="going"`) | `primary` / white | same | Badge "Going", "Going · party of 2". |

### Photographs, placeholders and overlays

| Token | Value | Used in |
| --- | --- | --- |
| `wash-rose` (class; colours `wash-rose-1/2`) | `#F7EEF1` → `#FCF7F8` (dark `#1C1C1C` → `#141414`) | The striped image placeholder in every post, tile and hero. The app draws real photographs; the stripe stays only as the loading background under them. |
| `wash-warm` (class; colours `wash-warm-1/2`) | `#F3EDE6` → `#FAF7F2` (dark as above) | Education and event placeholders. Same rule. |
| `scrim` | `rgba(0,0,0,.65)` | Dialog backdrops (post modal, Create, sheets). |
| `story` | `#1A1A1A` | App story viewer backdrop (desktop). Text on stories is white. |

## Type

Tokens: `font-display` (Fraunces on the site; the system face inside the app),
`font-sans` (Manrope), `font-app` (system UI) and `font-serif` (Fraunces everywhere, for the
wordmark and the club's name in the app). Two families, both self-hosted from
`@fontsource-variable` (no Google Fonts request):
**Fraunces** (variable, `opsz` 9–144, weights 300–500 used, italic for the signature field)
and **Manrope** (variable, weights 400–700 used). The member app uses the system UI stack
(`system-ui, -apple-system, 'Segoe UI', sans-serif`) at weights 400 and 600, with Fraunces for
the wordmark alone.

### Public site (`font-sans` = Manrope, `font-display` = Fraunces)

| Token | Size / line | Weight | Used in |
| --- | --- | --- | --- |
| `text-display` | 64 / 1.05, −.01em | Fraunces 300 | Home hero heading (desktop). 42 on phones. |
| `text-h1` | 52 / 1.05 | Fraunces 300 | Page titles: Events, Education, Visit, Contact, Join. 36 on phones (32 on Join). Event title 52 / 36. |
| `text-h2` | 32 / 1.2 | Fraunces 300 | Section headings: Who we are, This week, Learn with us, Hours. 28 on phones (26 on Visit). |
| `text-h2-lg` | 44 / 1.1 | Fraunces 300 | Home closing call to action, Join step 2 title. 34 on phones. |
| `text-card-title` | 22 / 1.2 | Fraunces 400 | Event and education card titles. 20 on phones; 26 in the Events list rows; 24 for the Visit steps and photo-ID heading. |
| `text-date` | 36 / 1 | Fraunces 400 | Day number on event cards (40 in the Events list, 30 and 28 on phones). |
| `text-lead` | 17 / 1.6 | Manrope 400, `fg-muted` | Page intro under the title. 18 on the home hero, 16 on phones. |
| `text-body` | 15 / 1.6 | Manrope 400 | Body copy; the page base. |
| `text-small` | 14 | Manrope 400–600 | Card meta, nav links (500), footer, buttons (compact). |
| `text-caption` | 13 | Manrope 400–600 | Field errors, notes in panels, card dates, filter chip text. |
| `text-label` | 11, caps, .06em | Manrope 600 | Category and level chips, "Most members" tag. 12 caps .06em for the date name and "You're in". 13 caps .08em for section labels in the designs. |
| `text-wordmark` | 28 (header), 22 (footer), 36 / 32 (age gate), 26 (phone header) | Fraunces 400, `wordmark` | "Rose". |

### Member app (`.member-app`)

| Token | Size / line | Weight | Used in |
| --- | --- | --- | --- |
| `app-wordmark` | 28 (sidebar), 24 (phone top bar, collapsed rail "R") | Fraunces 400, `wordmark` | "Rose". |
| `app-title` | 16 | 600 | Phone top-bar titles (handle, "Post", "Notifications", "Settings", "New post"), modal headers. 20 (400) for the profile handle on desktop; 24/600 for panel titles (Search, Notifications); 20/600 for the Settings page title. |
| `app-base` | 14 / 18 | 400 and 600 | Everything else: handles (600), captions, comments, nav labels, buttons. |
| `app-meta` | 12 / 18 | 400, `fg-muted` | Story labels, comment times, rail event times, toggle sub-labels. |
| `app-time` | 10, caps, .2px | 400, `fg-muted` | The post timestamp ("2 hours ago"). |
| `app-tab` | 12, caps, .08em | 600 | Desktop profile tabs (POSTS, SAVED). |
| `app-fine` | 11 / 16 | 400, `fg-faint` | Right-rail footer links. |

## Spacing

The scale is 4, 8, 12, 16, 24, 32, 48, 64 (DS "Spacing & shape"), plus these fixed values:

| Value | Used in |
| --- | --- |
| 48px | Site page gutter on desktop (header, sections, footer). |
| 20px | Site page gutter on phones; card padding on phones. |
| 96px / 64px | Site home hero vertical padding; section padding (desktop). 40px on phones. |
| 16px | App side padding (post header, phone top bar, comment rows). |
| 245px | App sidebar width; 72px when collapsed to a rail. |
| 470px / 320px / 64px | App feed column, right rail, gap between them. |
| 935px | App profile, Explore and grid width. |
| 397px | App Search and Notifications panels. |
| 2px | App grid gap (profile grid, phone Explore); 4px on desktop Explore. |

## Shape

| Token | Value | Used in |
| --- | --- | --- |
| `rounded-pill` | 999px | Site buttons, chips, badges, filter tabs, the Leave control. |
| `rounded-field` | 12px | Site inputs, the RSVP party-size row, paywall panel, journal tiles (12, 10 on phones). |
| `rounded-card` | 16px | Site cards (event, education, Get involved, Visit callout, phone tier cards). |
| `rounded-panel` | 20px | Site RSVP panel, age gate card, Contact success, desktop Join tiers. 24 for the desktop door reference. |
| `rounded-app` | 8px | App buttons, inputs, nav rows, rail date tiles. |
| `rounded-sheet` | 12px | App action sheet, Create modal, story card. |
| `rounded-full` | 50% | Avatars, story circles, steppers, the Join step numbers. |
| Checkbox | 22px square, 6px radius (site); 20–22px, 4px radius (app) | Agreement and consent checkboxes. |
| Toggle | 40×22, radius 11, 18px knob, 2px inset | App toggles. Off `border`, on `primary`. |

## Elevation

| Token | Value | Used in |
| --- | --- | --- |
| `shadow-modal` | `0 24px 64px rgba(0,0,0,.3)` | App post modal, Create modal. |
| `shadow-sheet` | `0 12px 40px rgba(0,0,0,.18)` | Action sheet, Create step cards. |
| `shadow-panel` | `4px 0 24px rgba(0,0,0,.08)` | App Search and Notifications slide-outs. |

The site uses no shadows; it separates with 1px `border` lines and `surface` bands.

## Icons

Lucide outlines at a 24px box with a 1.8px stroke (app), 16–18px in site buttons (Leave,
Add to calendar), 22px (menu, lock) and 32px (photo ID, 1.5 stroke). Active app nav icons
take a 2.4px stroke (2.6 in the phone tab bar). The liked heart is filled `primary`.

## Motion

The designs are static. The app keeps its existing motion: 150–200ms ease-out for panels and
the like pop, linear story progress bars, and nothing at all under `prefers-reduced-motion`.
