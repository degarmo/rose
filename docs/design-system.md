# Design system

The visual design lives in **[`docs/design/`](design/)**. It is the source of truth for
how the website and the member app look (prompt 08); it replaces every earlier visual
spec.

| File | What it holds |
| --- | --- |
| [`design/source/`](design/source/) | The design files: `Rose Design System.dc.html` (tokens and every component state), `Rose Public Site.dc.html`, `Rose Member App.dc.html` and `Post Card.dc.html`. Open them in a browser; they load fonts and React from public CDNs to render, which the app itself never does. |
| [`design/reference/`](design/reference/) | A screenshot of every screen in the designs, named from its `data-screen-label`, plus the whole design-system page and the post card. |
| [`design/tokens.md`](design/tokens.md) | Every colour, type size, space, radius, shadow and icon size, its light and dark value, and where the designs use it. |
| [`design/screen-map.md`](design/screen-map.md) | Each designed screen with its route, React component and viewport; routes with no design and the screen they follow; tablet widths. |
| [`design/gap-report.md`](design/gap-report.md) | The app before the redesign against the designs, and the functional breaks found and fixed first. |
| [`design/before/`](design/before/), [`design/after/`](design/after/), [`design/compare/`](design/compare/) | Captures of the app before and after, and design / built side-by-sides. |

**The privacy, access and security rules in `docs/architecture.md` win over the
designs.** Where a design shows something those rules forbid, the rule is followed and
the conflict is recorded in `docs/decisions.md` (prompt 08).

## Tokens

`frontend/src/index.css`. The palette is a set of `--ui-*` variables on `:root`, redefined
under `:root[data-appearance='dark']`; Tailwind's `@theme` reads them, so `bg-surface` or
`text-fg-muted` follow the appearance. Tailwind's own colour palette is switched off:
only the design's colours exist (plus `white`, `black`, `transparent`). The names match
[`design/tokens.md`](design/tokens.md):

- Neutrals: `canvas`, `surface`, `blush`, `fg`, `fg-muted`, `fg-muted-tint` (muted text on
  `blush` or `tint`), `fg-faint` (disabled text only), `border`, `control`, `field`, `dot`.
- Rose: `primary` and `primary-hover` (fills), `link` (rose text, lighter in dark), `tint`
  and `tint-fg`, `wordmark` (the "Rose" wordmark only), `oxblood` and `on-oxblood` (the home
  values band), `tier-selected`.
- Status: `danger`, `wait`/`wait-fg`, `full-fg`; badges combine them (`Badge`).
- Pictures: `wash-rose` and `wash-warm` (the striped placeholder under every picture),
  `story`, `scrim`.
- Type: `font-display` (Fraunces; the system face inside the app), `font-sans` (Manrope),
  `font-app` (system UI), `font-serif` (Fraunces everywhere, for the wordmark and the
  club's name in the app). Sizes `text-display`, `text-h1`, `text-h2-lg`, `text-h2`,
  `text-card-title`, `text-lead`, `text-body`, `text-label`, `text-meta`, `text-app`.
- Shape: `rounded-app` (8), `rounded-field` (12), `rounded-sheet` (12), `rounded-card` (16),
  `rounded-panel` (20); `shadow-modal`, `shadow-sheet`, `shadow-panel`.
- Widths: `rail:` (1160px, the member app's right rail) and `wide:` (1264px, the labelled
  sidebar). The website switches to its desktop navigation at `xl` (1280px).

Fonts are self-hosted through `@fontsource-variable` (Fraunces with its optical-size axis,
italic for the signature field; Manrope), imported in `main.tsx`. Nothing is fetched from
another site.

`cn()` (`lib/cn.ts`) joins classes with `tailwind-merge`, so a `className` passed to a
component overrides that component's own size, spacing or display. The design's token
names are registered with it.

### Appearance

`lib/appearance.ts`. `main.tsx` applies the `appearance` cookie before the first paint (no
request is made for it). Once the session loads, the account's saved choice wins and is
written back to the cookie. Changing it (account page, member app Settings or the More
menu) applies at once, sets the cookie and, when signed in, saves it on the account.

### Contrast

Every text colour passes WCAG AA (4.5:1) on the background it is used on; the ratios are in
`design/tokens.md`. Two places differ from the drawings for that reason: muted text on
`blush` and `tint` uses `fg-muted-tint` (`#6B6B6B`), and the member app's 11px footer links
use `fg-muted` rather than `#A3A3A3` (2.5:1).

## Website components

`frontend/src/components/ui` (exported from `ui/index.ts`):

| Component | Design | Notes |
| --- | --- | --- |
| `Button`, `ButtonLink` | Buttons, public site | Pills. Variants `primary`, `secondary` (1px border), `outline` (text-coloured border), `dark` (text-coloured fill), `link` (rose text). Sizes `sm` 36, `md` 40, `lg` 48. Disabled turns grey. External `to` addresses become plain links. |
| `Badge`, `Chip` | Status badges, chips | `Badge` tones `open`, `wait`, `full`, `members`, `going`. `Chip` is the 11px caps category or level chip, `outline` on the page and `solid` on a picture. |
| `Card` | Cards | White, 1px border; `shape="card"` (16px) or `"panel"` (20px). Callers pad. |
| `Input`, `Select`, `Textarea`, `FormField` | Inputs | 48px fields, 12px corners; focus and errors draw a 1.5px border. `FormField` wires the 14/600 label, a 13px hint and a 13px error. |
| `Checkbox`, `CheckboxBox` | Checkbox | 22px, 6px corners, rose when ticked; `tone="required"` draws the empty box in rose. |
| `Toggle`, `Switch` | Toggle | 40×22, rose when on. `Toggle` adds the label and hint. |
| `Segmented`, `FilterChips` | Site tabs and filters | The bordered pill switch (List / Month) and the 34px chip row; the chosen one is filled with the text colour. |
| `Section`, `SectionHeading`, `GUTTER` | Page sections | 1440px wide with the 20 / 32 / 48px gutter; `rule` adds the 1px top line. The heading is Fraunces 300 with an optional rose link on the right. |
| `ImageFrame` | Pictures | Manifest or API pictures over the `wash-*` placeholder; refuses any picture without face consent. |
| `Modal`, `ToastProvider` | Sheets | Native `<dialog>`; 20px panel, modal shadow. |
| `GradientBackground` | (not in the designs; decision 369) | The home hero's pastel "Aurora" glow (`.gradient-aurora`), dimmed in dark. Decorative; inside a `relative isolate` parent. Text on it uses `fg`. |

`frontend/src/components/layout`: `Header` (72px; a quiet version with the step indicator
on `/join`), `Footer` (the full footer on the home page, the one-row footer elsewhere),
`QuickExit` (the Leave pill), `AgeGate`, `NavDropdown`, `AccountMenu`, `SubscribeForm`,
`Wordmark`, and `SiteFrame` (header, main and footer around any content, also used for the
member app's 404).

`frontend/src/components/content`: `PageHero` (title block, optional picture column and
right-hand control), `Copy` and `CopyHeading` (staff-editable copy, see `docs/content.md`),
`EventCard` (`layout="card"` or the desktop list `row`, with `DateColumn`),
`OpportunityCard` (3:2 picture with the level chip; the paywall when locked), `RSVPPanel`
(every RSVP state: badge, party-size stepper, note to hosts, calendar file), `MonthCalendar`,
`FAQAccordion`, `JournalStrip`, `JournalTile`, `ValuesStrip`, `PostView`, `Carousel`,
`StaffCard`, `DetailItem`, `States`. `components/membership`: `PaywallPanel` (the blush
"For members" panel), `ReferenceCode` (the door reference card with its QR code) and
`TierCard` (Join step 1's tier card: the featured tier has the rose border, tinted card and
"Most popular" tag; also used, four to a row from 1264px, on the membership page).

## Member app components

`frontend/src/components/members/app`. The app is wrapped in `.member-app` (system face,
14/18, weights 400 and 600).

| Component | Design | Notes |
| --- | --- | --- |
| `AppShell` | App shell | Access check, sidebar or tab bar, the Search and Notifications panels (the page behind fades), the post modal and Create. |
| `Sidebar`, `TabBar`, `PhoneBar`, `HomeBar`, `LeaveButton`, `BackButton` (`Nav.tsx`) | Sidebar, top bar, bottom tabs | 245px sidebar with labels from 1264px, a 72px rail below that; 50px phone tab bar. Every page renders its own 44px `PhoneBar`, and the quick exit is always its last icon. |
| `PostCard` | `Post Card.dc.html` | One component for member and club posts: 56px header, full-bleed media with dots below, 44px action row, likes line (the author sees the count; others see only "Liked by you"), caption, two comments, the caps timestamp and the comment row. |
| `MediaCarousel`, `SensitiveBlur` | Post card, sensitive post | Swipe, keys or arrows; double-tap likes. Sensitive photos are blurred and `inert` until View. |
| `StoriesTray`, `StoryViewer` | Story circles, story viewer | 64px circles with a rose ring until seen. |
| `ActionSheet` | Action sheet | 400px, 48px rows. Another member's post: Report to hosts, Hide this post, Mute, Block, Save, Go to post, Cancel. No Share, Send or Copy link. |
| `RightRail`, `SearchContent`, `NotificationsContent`, `PostGrid`, `PostDetail`, `CreatePost` | Home, Search, Notifications, Profile, Post detail, Create | |
| `AppButton` (`primitives.tsx`) | Buttons, member app | 32px, 8px corners; `primary`, `secondary` (grey), `outline`, `plain`. |

`components/members`: `Avatar` (picture, or a soft wash chosen by handle), `RedactionEditor`
(cover-ups and crop, applied on the device before upload), `ReportDialog`, `ConfirmDialog`,
`EditPostDialog`, `ProfileSettings`, `GuidelinesText`.

Member images block the context menu, dragging and the iOS long-press callout. It is a
deterrent, not a control; the server's viewer watermark is what traces leaks, so the
design's on-screen watermark overlay is not drawn a second time.

## Checking a change against the designs

- `node e2e/scripts/capture-design-reference.mjs` re-captures `design/reference/` from the
  design files.
- `node e2e/scripts/design-sweep.mjs --base <app> --out after --accounts <seed_demo output>
  --backend backend` captures every route and designed state at 390×844 and 1440×900 and
  reports console errors, failed or third-party requests, sideways overflow, the Leave
  control and serious or critical axe findings (`sweep.json`). `--only <regex>` limits it.
- `backend/.venv/bin/python scripts/design_compare.py` writes the side-by-sides.

Component tests live next to their components (`*.test.tsx`) and use `renderWithProviders()`
from `src/test/render.tsx`.

## Staff admin

The admin (Django) keeps its own look, in `backend/apps/core/static/core/ig-admin.css` and
`templates/admin/base_site.html`: a photo-app style with a white (or black) canvas, the
system font, hairline borders and outline icons, a 245px sidebar with Settings at the bottom
left, and no inline styles or scripts, so the strict CSP stays as it is. The prompt 08
designs do not cover the admin.
