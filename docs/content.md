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
    eyebrow: Plan your visit
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
tiers: [{slug: rose, name: Rose, interval: month, price_cents: 4000}]  # price only if given
redirects: [{from: /old-path, to: /new-path}]                          # "/old/*" covers all under it
```

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
| `home` | `hero.eyebrow/title/lede`, `who.*`, `week.*`, `education.*`, `journal.*`, `involved.*` and `involved.1..3.title/body`, `closing.title/lede` |
| `values` | `values.1..4.title/short/long` (home strip and About) |
| `about` | `hero.*`, `mission.*`, `nonprofit.title/body`, `volunteer.title/body`, `values.eyebrow/title`, `people.*` |
| `staff` | `hero.*`, `team.*`, `roles.*` and `roles.N.title/body`, `cta.*` (profiles come from Staff profiles) |
| `visit` | `hero.*`, `expect.*`, `steps.N.title/body`, `id.title/body`, `hours.title`, `directions.title`, `rules.*`, `faq.*` |
| `faq` | `hero.*`, `cta.*` (questions come from FAQ items) |
| `rules` | `hero.*`, `intro`, `rules.N.title/body`, `help.*` |
| `guests` | `hero.*`, `who.*`, `expect/rules/id.title/body`, `price.*`, `steps` |
| `join` | `hero.*`, `benefits.*` and `benefits.N.title/body` |
| `events`, `education`, `journal` | `hero.*` |
| `contact` | `hero.*`, `concern`, `aside.title/note` |
| `privacy` | `hero.*`, `blocks.N.title/body` |
| `rentals` | `hero.*`, `spaces.*`, `uses.title` and `uses.N`, `included.title` and `included.N`, `form.*` |
| `volunteer` | `hero.*`, `why.*`, `roles.*` and `roles.N.title/body`, `form.*` |
| `donate` | `hero.*`, `funds.*` and `funds.N.title/body`, `ways.*`, `ways.door/check/online.title/body`, `form.*` |

A `*` group is `eyebrow`, `title` and `lede`.

## Images

Images are never part of the copy. The previous site's images are listed, commented out,
in `docs/image-sources.txt`; once the club confirms it may reuse one and has consent from
anyone recognisable, follow "Adding images" in the README.
