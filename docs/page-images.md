# Page images

Every picture on the public site and the member app's non-member teaser, at every width:
where it sits, where it comes from, how big it is drawn, and whether staff change it in
**Admin > Content > Page images**. The logo, the age gate's emblem, favicons and the
link-preview picture come from the brand assets (`frontend/public/brand`,
`scripts/build_brand_assets.py`) and are not listed.

Three kinds of picture appear:

- **Page image (slot):** a fixed picture on a page. Staff replace, remove or restore it
  in Page images, set its focal point, and the site shows it through `<SiteImage slot>`.
  An empty slot, or one showing faces without confirmed consent, shows the page's
  texture instead. These were `frontend/public/images/*.webp` and the image manifest
  until the slots replaced them.
- **Record image:** the picture of one event, education item, journal post or staff
  profile, changed on that record's own admin page (its image fields).
- **Design background:** a gradient or texture that is part of the design. It never
  stood in for a photograph, so it is not a slot.

## Page image slots

| Page | Slot | Label | Position | Drawn at | Shape | Started with |
| --- | --- | --- | --- | --- | --- | --- |
| Home `/` | `home.hero` | Home: top banner | Hero: beside the headline from 1024px; under the buttons on phones and tablets | half the page (to 640px) on computers, full width on phones | 5:4 computers, 4:5 phones | The dance floor (supplied by the club) |
| About `/about` | `about.hero` | About: header picture | Beside the page title, 1024px and wider only | half the page (to 640px) | 5:4 | The pride flag (Pexels) |
| Plan your visit `/visit` | `visit.hero` | Plan your visit: header picture | Beside the page title, 1024px and wider only | half the page (to 640px) | 3:2 | A hand on a bare back (supplied by the owner) |
| Guests `/guests` | `guests.hero` | Guests: header picture | Beside the page title, 1024px and wider only | half the page (to 640px) | 3:2 | The red archway (Pexels) |
| Rentals `/rentals` | `rentals.hero` | Rentals: header picture | Beside the page title, 1024px and wider only | half the page (to 640px) | 3:2 | The red archway (Pexels) |
| Volunteer `/get-involved/volunteer` | `volunteer.hero` | Volunteer: header picture | Beside the page title, 1024px and wider only | half the page (to 640px) | 3:2 | The pride flag (Pexels) |
| Donate `/get-involved/donate` | `donate.hero` | Donate: header picture | Beside the page title, 1024px and wider only | half the page (to 640px) | 3:2 | Cuffs and strawberries (Pexels) |

Each slot's source and licence is in its **Source** field. The pictures the slots started
with are kept in `backend/apps/pages/site_image_seeds/`, so a new environment starts with
them (`pages` migration 0009).

## Record images

| Page | Position | Source | Drawn at | Shape | Without a picture |
| --- | --- | --- | --- | --- | --- |
| Events `/events` | Each card in the grid | `Event.hero_image` | a third, half or all of the width | 4:3 | Category gradient with an icon |
| Events `/events` and Home ("This week") | Featured event banner | The featured `Event.hero_image` | 60% of the banner from 768px; on top on phones | at least 16:10 | Category gradient with an icon |
| Event `/events/<slug>` | Full-width band at the top | `Event.hero_image` | full width, 420px tall on computers | 4:3 on phones | Warm texture |
| Education `/education`, Home ("Learn with us") | Top of each card | `Opportunity.hero_image` | the card's width | 2:1, 3:2 on computers | Warm texture |
| Education item `/education/<slug>` | Full-width band at the top | `Opportunity.hero_image` | full width, 420px tall on computers | 4:3 on phones | Warm texture |
| Journal `/journal`, Home ("From the Journal") | Each tile | The post's first `PostImage` | 3 to 6 across | 1:1 | Rose texture |
| Journal post `/journal/<slug>` and its pop-up | Carousel | The post's `PostImage`s | the left column | 1:1 | One rose-texture slide |
| Our staff `/about/staff`, About (staff strip) | Each person's card | `StaffProfile.photo` | 56px circle | 1:1 | The person's initial |
| Member home (accounts without feed access) | Community teaser, a blurred 3×3 grid | Recent journal pictures and announcement notes | 160px tiles | 1:1 | An empty square |

## Pages with no picture

| Page | What is there instead |
| --- | --- |
| Home, apart from the hero | "Who we are", "Your week", values, "Get involved" and the closing call are words only; the hero's colour wash is a design background (`GradientBackground`, `.gradient-aurora`). |
| Membership `/membership`, Join `/join`, FAQ `/faq`, House rules `/house-rules`, Privacy `/privacy`, Contact `/contact` | Words only. Notices sit on flat blush panels (`bg-blush`), a design colour. |
| Our staff `/about/staff`, Events, Education, Journal | Their page titles have no picture; their pictures are the record images above. |
| Age gate | The emblem (brand asset) on a flat blush background. |
| Leaving page `/exit`, Not found (404) | Words only, the 404 on a blush panel. |
| Footer | The logo (brand asset) and words. |

No page draws a CSS background image. The wash textures (`.wash-rose`, `.wash-warm`) only
show where a picture is missing or still loading.
