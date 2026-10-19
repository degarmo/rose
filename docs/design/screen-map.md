# Screen map

Each screen in the designs (its `data-screen-label`), the route that shows it, the React
component that draws it and the viewport it is drawn for. Desktop is 1440×900 and phone is
390×844. Reference images are in `reference/`, named `<file>--<label>.png`. Before and after
captures use the same names in `before/` and `after/`, and `compare/` holds the side-by-side
images.

Component paths are relative to `frontend/src/`.

## Public website (`Rose Public Site.dc.html`)

| Screen | Route | Component | Viewport |
| --- | --- | --- | --- |
| Age gate · desktop | any page, before the `age_ok` cookie | `components/layout/AgeGate.tsx` | 1440×900 |
| Age gate · phone | same | same | 390×844 |
| Home · desktop | `/` | `pages/HomePage.tsx` with `components/layout/Header.tsx`, `Footer.tsx`, `components/content/EventCard.tsx`, `OpportunityCard.tsx`, `JournalStrip.tsx`, `ValuesStrip.tsx` | 1440 wide, full page |
| Home · phone | `/` | same | 390 wide, full page |
| Events · desktop | `/events` (List) | `pages/EventsPage.tsx`, `components/content/EventCard.tsx` (row) | 1440×900, full page |
| Events · phone (month view) | `/events?view=month` | `pages/EventsPage.tsx`, `components/content/MonthCalendar.tsx` | 390×844 |
| Event detail · desktop | `/events/:slug` | `pages/EventPage.tsx`, `components/content/RSVPPanel.tsx` | 1440 wide, full page |
| Event detail · phone | `/events/:slug` | same | 390 wide, full page |
| Education · desktop | `/education` | `pages/EducationPage.tsx`, `components/content/OpportunityCard.tsx`, `components/membership/PaywallPanel.tsx` | 1440×900, full page |
| Education · phone | `/education` | same | 390 wide, full page |
| Plan Your Visit · desktop | `/visit` | `pages/VisitPage.tsx`, `components/content/FAQAccordion.tsx` | 1440 wide, full page |
| Plan Your Visit · phone | `/visit` | same | 390 wide, full page |
| Contact · desktop | `/contact` (an invalid email entered) | `pages/ContactPage.tsx` | 1440×900 |
| Contact · phone (success) | `/contact` (after sending) | same | 390×844 |
| Join step 1 · desktop | `/join` | `pages/join/JoinPage.tsx` (`TierCards`) | 1440×900 |
| Join step 1 · phone | `/join` | same | 390×844 |
| Join step 2 · desktop | `/join` after choosing a tier | `pages/join/AgreementStep.tsx` | 1440×900 |
| Join step 2 · phone | same | same | 390×844 |
| Join step 3 · desktop | `/join` once active, and `/join/confirming` | `pages/join/JoinConfirmation.tsx`, `ConfirmingPage.tsx`, `components/membership/ReferenceCode.tsx` | 1440×900 |
| Join step 3 · phone | same | same | 390×844 |

## Member app (`Rose Member App.dc.html`)

All member screens sit inside `components/members/app/AppShell.tsx`, which draws the
sidebar (`Nav.tsx` `Sidebar`) from 768px, and the phone top bar and tab bar (`TopBar`,
`TabBar`) below it.

| Screen | Route | Component | Viewport |
| --- | --- | --- | --- |
| Home · desktop | `/members/feed` | `pages/members/FeedPage.tsx`, `Stories.tsx` (`StoriesTray`), `PostCard.tsx`, `RightRail.tsx` | 1440×900 |
| Home · phone | `/members/feed` | same, without the rail | 390×844 |
| Post detail · desktop modal | any app page with `?post=<id>` | `AppShell.tsx` (`PostModal`), `PostDetail.tsx` (`layout="modal"`) | 1440×900 |
| Post detail · phone | `/members/p/:id` | `pages/members/PostPage.tsx`, `PostDetail.tsx` (`layout="page"`) | 390×844 |
| Story · desktop | `/members/feed`, a story circle opened | `Stories.tsx` (`StoryViewer`) | 1440×900 |
| Story · phone | same | same | 390×844 |
| Profile (own) · desktop | `/members/u/<own handle>` | `pages/members/MemberProfilePage.tsx`, `PostGrid.tsx` | 1440×900 |
| Profile (own) · phone | same | same | 390×844 |
| Profile (other member) · desktop | `/members/u/:handle` | same | 1440×900 |
| Profile (other member) · phone | same | same | 390×844 |
| Explore · desktop | `/members/explore` | `pages/members/ExplorePage.tsx`, `PostGrid.tsx` | 1440×900 |
| Explore · phone | `/members/explore` | same | 390×844 |
| Search · desktop slide-out | any app page, Search in the sidebar | `AppShell.tsx` (`SidePanel`), `SearchContent.tsx` | 1440×900 |
| Search · phone | `/members/search` | `pages/members/SearchPage.tsx`, `SearchContent.tsx` | 390×844 |
| Notifications · desktop slide-out | any app page, Notifications in the sidebar | `AppShell.tsx` (`SidePanel`), `NotificationsContent.tsx` | 1440×900 |
| Notifications · phone | `/members/notifications` | `pages/members/NotificationsPage.tsx`, `NotificationsContent.tsx` | 390×844 |
| Create · step 1 Select (desktop modal) | Create in the sidebar | `CreatePost.tsx` (step `select`) | 1440×900 |
| Create · desktop (step 2 in context) | same, after choosing a photo | `CreatePost.tsx` (step `redact`), `components/members/RedactionEditor.tsx` | 1440×900 |
| Create · step 3 Details (desktop modal) | same | `CreatePost.tsx` (step `details`) | 1440×900 |
| Create · step 4 Share (desktop modal) | same, after sharing | `CreatePost.tsx` (step `share`) | 1440×900 |
| Create · phone step 1 Select | Create in the tab bar (full screen) | `CreatePost.tsx` (`fullScreen`) | 390×844 |
| Create · phone step 2 Crop & redact | same | same, `RedactionEditor.tsx` | 390×844 |
| Create · phone step 3 Details | same | same | 390×844 |
| Create · phone step 4 Share | same | same | 390×844 |
| Settings · desktop | `/members/settings` | `pages/members/SettingsPage.tsx` | 1440×900 |
| Settings · phone | `/members/settings` | same | 390×844 |
| Home dark · desktop | `/members/feed` with Appearance set to Dark | `FeedPage.tsx` under `html[data-appearance='dark']` | 1440×900 |
| Home dark · phone | same | same | 390×844 |

## Design system and post card

| Screen | Where it lives in the app | Reference |
| --- | --- | --- |
| Design system page (colour, type, spacing, buttons, inputs, badges, tabs, story circles, cards, RSVP panel states, post card, action sheet, sensitive post) | `components/ui/*`, `components/content/RSVPPanel.tsx`, `components/membership/PaywallPanel.tsx`, `components/members/app/ActionSheet.tsx`, `PostCard.tsx`, `Stories.tsx` | `reference/design-system-page.png` |
| Post card | `components/members/app/PostCard.tsx`, one component for member and club posts | `reference/post-card.png` |

## Screens with no route of their own

Each of these is a state of a route above, not a separate page:

- **Contact · desktop** shows the inline error state, and **Contact · phone (success)**
  shows the sent state. Both states are on `/contact`, and each viewport is captured in
  both.
- **Events · phone (month view)** is the Month tab of `/events`. The List tab is captured
  on phones too.
- **Create**, **Search · desktop slide-out**, **Notifications · desktop slide-out**,
  **Story** and **Post detail · desktop modal** are layers over an app page and have no URL
  of their own (the modal uses `?post=`).

## Routes with no design

The designs do not draw these routes. Each one uses the shared header, footer, type,
buttons, inputs and cards, laid out like the nearest designed screen (in brackets).

| Route | Component | Nearest design |
| --- | --- | --- |
| `/about` | `pages/AboutPage.tsx` | Home ("Who we are", values band) |
| `/about/staff` | `pages/StaffPage.tsx` | Education (card grid) |
| `/guests` | `pages/GuestsPage.tsx` | Plan Your Visit |
| `/faq` | `pages/FAQPage.tsx` | Plan Your Visit ("Questions we get") |
| `/house-rules` | `pages/HouseRulesPage.tsx` | Join step 2 (agreement text) |
| `/rentals` | `pages/RentalsPage.tsx` | Contact (form) |
| `/get-involved/volunteer` | `pages/VolunteerPage.tsx` | Contact (form) |
| `/get-involved/donate` | `pages/DonatePage.tsx` | Join step 1 (choice cards) |
| `/subscribe/confirm`, `/unsubscribe` | `pages/SubscriptionPages.tsx` | Contact · phone (success) |
| `/events/cancel` | `pages/CancelRSVPPage.tsx` | Contact · phone (success) |
| `/education/:slug` | `pages/OpportunityPage.tsx` | Event detail |
| `/journal` | `pages/JournalPage.tsx` | Home ("From the Journal") |
| `/journal/:slug` | `pages/JournalPostPage.tsx` | Event detail (hero and body) |
| `/privacy` | `pages/PrivacyPage.tsx` | Join step 2 (long text) |
| `/account`, `/account/login`, `/account/register`, `/account/verify`, `/account/forgot`, `/account/reset`, `/account/receipts/:id`, `/account/export` | `pages/account/*` | Contact (form) and Join step 3 (card) |
| `/members/join-feed` | `pages/members/JoinFeedPage.tsx` | Join step 2 (agreement) |
| `/members/saved` | redirects to the own profile's Saved tab | Profile (own) |
| `/exit` | `pages/ExitPage.tsx` | none: a blank, unbranded page by design (decision 15) |
| any unknown path, and every `/members/*` path without access | `pages/NotFoundPage.tsx` | Contact · phone (success) |

## Tablet widths (768–1263px)

The designs draw only 390 and 1440. In between:

- **Website:** phone layout up to 1023px (menu button, stacked sections, 20px gutter
  growing to 32px from 640px); desktop header and grids from 1024px, with the gutter at
  32px until 1280px and 48px from there. Three-column card grids drop to two columns from
  640px to 1023px.
- **Member app:** from 768px the sidebar replaces the tab bar, collapsed to its 72px icon
  rail until 1264px, where the labels and wordmark appear at 245px. The right rail appears
  from 1160px. The feed column stays 470px wide; profile and Explore grids fill up to 935px.
