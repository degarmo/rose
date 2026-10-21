# Site copy and content

The words on the public pages live in the database (`PageContent`), not in the React
code, so staff can change them in the admin without a deploy. The site shows a loading
skeleton while copy arrives and nothing for a key that has no value yet.

## Where copy comes from

| Source | Used for | In git? |
| --- | --- | --- |
| `content/*.yaml` | The club's real copy, drafted from the previous website. One file per page or section, each starting with `status:` and `source_url:`. | No: the folder names the organisation, like `prompts/`. Only `content/redirects.yaml` (paths only) is committed. |
| `backend/apps/pages/demo_content/*.yaml` | Placeholder copy for development and the browser tests. Loaded by `seed_demo` and `e2e_fixtures`. Never used in production. | Yes |
| Admin > Pages > Page copy | Every later edit. | n/a |

## The file format

```yaml
status: draft - needs club approval      # or "approved" once the club signs it off
source_url:
  - https://www.example.org/directions   # the old pages it was drafted from
notes: Anything the approver should know (conflicts, guesses, gaps).
page: visit                             # the page this copy belongs to
copy:
  hero:
    title: Plain text keeps its line breaks.
    lede:
      rich: <p>Formatted text: paragraphs, lists, bold, italics and links.</p>
  steps:                                # numbered items become steps.1.title, steps.2.title
    - title: First
      body: ...
site_settings: {hours_text: ..., directions_text: ...}  # only the fields given change
social_links: [{label: Discord, url: https://...}]
faqs: [{slug: parking, question: ..., answer: ...}]
staff: [{slug: wren, display_name: Wren, role_title: Host, bio: ..., is_published: false}]
tiers: [{slug: rose, name: Rose, interval: month, price_cents: 4000}]  # only the fields given change
redirects: [{from: /old-path, to: /new-path}]                          # "/old/*" covers all under it
```

A tier takes `name`, `description` (one line), `perks` (a list), `price_cents`, `interval`
(`month`, `year` or `once`), `duration_days`, `renews`, `events_per_month` (`null` for
unlimited), `guests_included_per_event`, `guest_discount`, `premium_discord`, `event_access`
(`all` or `tagged`), `allowed_event_tags` (event tag slugs, such as `community` and
`first_friday`), `grants_feed_access`, `grants_members_events`, `grants_members_education`,
`is_featured`, `is_guest_pass`, `is_active` and `sort_order`. The membership page lists
tiers by price, lowest first, with `sort_order` breaking ties; a price of 0 makes a tier
free.

Loading matches rows by slug (or page and key, or old path) and updates them. It never
deletes anything, and if any file has a problem nothing at all is written.

## Approving and loading

1. A board member reads each draft and its `notes`, fixes anything wrong, and changes
   `status:` to `approved`.
2. Load it:
   - **Production:** a superuser opens Admin > Pages > Page copy > **Load site content**,
     uploads the files, runs it once without "Write the changes" to see what would change,
     then again with it ticked.
   - **Anywhere with the files on disk:** `python manage.py load_site_content` (a dry run),
     then `--commit`. `--dir` points at another folder; naming files loads only those.
3. In production, a file still marked as a draft is refused. Ticking "Allow drafts" (or
   `--allow-draft`) loads it anyway, and that is written to the audit log. Every committed
   load is logged.

## Keys each page reads

| Page | Keys |
| --- | --- |
| `home` | `hero.title/lede`, `who.title/lede`, `week.title`, `education.title`, `journal.title`, `involved.title` and `involved.1..3.title/body`, `closing.title/lede` |
| `values` | `values.1..4.title/short/long` (home band and About) |
| `about` | `hero.*`, `mission.title/lede`, `nonprofit.title/body`, `volunteer.title/body`, `values.title`, `people.*` |
| `staff` | `hero.*`, `team.*`, `roles.*` and `roles.N.title/body`, `cta.title/lede` (profiles come from Staff profiles) |
| `visit` | `hero.*`, `expect.title`, `steps.N.title/body`, `id.title/body`, `hours.title`, `directions.title`, `faq.title` |
| `faq` | `hero.*`, `cta.title/lede` (questions come from FAQ items) |
| `rules` | `hero.*`, `intro`, `rules.N.title/body`, `help.title/lede` |
| `guests` | `hero.*`, `who.*`, `id.title/body`, `price.*`, `steps` |
| `join` | `hero.title/lede`, `note`, `benefits.*` and `benefits.N.title/body` |
| `membership` | `hero.title/lede`, `compare.title`, `good_to_know.title` and `good_to_know.N` (formatted), `tip`, `cta.title/body/button`, `newsletter` (tiers come from `tiers:`) |
| `events`, `education`, `journal` | `hero.*` |
| `contact` | `hero.title/lede`, `concern` |
| `privacy` | `hero.*`, `blocks.N.title/body` |
| `rentals` | `hero.*`, `spaces.*`, `uses.title` and `uses.N`, `included.title` and `included.N`, `form.*` |
| `volunteer` | `hero.*`, `why.*`, `roles.*` and `roles.N.title/body`, `form.*` |
| `donate` | `hero.*`, `funds.*` and `funds.N.title/body`, `ways.*`, `ways.door/check/online.title/body`, `form.*` |

A `*` group is `title` and `lede`. Older files may still hold `eyebrow` keys; the redesigned pages (prompt 08) no longer show them.

## Images

Images are never part of the copy: a page's pictures are in Admin > Content > Page images
(each page group links to that page's copy), listed in `docs/page-images.md`. The previous
site's images are listed in `docs/old-site-images.txt`; once the club confirms it may reuse
one and has consent from anyone recognisable, upload it there or on its record.
