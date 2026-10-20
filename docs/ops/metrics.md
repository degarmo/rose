# Metrics

Every number staff see comes from one module, `backend/apps/core/metrics.py`:
- the admin dashboard's cards, charts and tables
- the sidebar badges
- the membership summary and RSVP counts pages
- the Going column in the events list
- the CSV export

Nothing else counts, so the same metric shows the same value everywhere.
`tests/test_metrics.py` checks this through the service and through the rendered pages.

The admin dashboard is the only dashboard. The staff section in the member app
(`/members/staff`) has no figures. It keeps the hands-on tools: the door desk, the
reports inbox, members and the team.

## Suppression

Suppression happens inside the service, so no screen can skip it.

- **Counts.**
  - From 1 to 4: withheld. Shown as **<5**, with "fewer than 5" as the tooltip and for screen readers.
  - Zero: shown as **0**. It identifies nobody, and a badge that read "<5" when nothing is waiting would mislead.
  - 5 or more: shown exactly.
- **Money.** A total is withheld when it comes from fewer than 5 payments or gifts, since a small total can point to someone.
- **Badges** use the same values. With nothing waiting there is no badge.
- **Totals across tiers** are added up before suppression, so "All tiers" is a real number even when each tier's own count is "<5".

Each figure carries `display` (the text shown) and `spoken` (the words for screen readers and the tooltip).
Templates show it through `admin/rose/metric.html`.

## Definitions

### Waiting for staff

These are the dashboard's to-do cards, and the same counts are the sidebar's badges.

| Metric | Definition | Function | Where it shows |
| --- | --- | --- | --- |
| Open reports | Reports whose status is open or in review (resolved and dismissed ones do not count) | `open_reports()` | card, Reports badge, Feed table, export |
| Posts awaiting approval | A member's first posts held for review: status pending and processed (`is_processing` false) | `posts_awaiting_approval()` | card, Feed posts badge, Feed table, export |
| ID checks needed | Memberships that would be active but for a missing ID check: status pending payment with `paid_awaiting_id_check` set (paid online, a free plan, or imported paid-up), on an active account | `id_checks_needed()` | card, Door desk badge, export |
| Unanswered messages | Contact messages not yet marked handled | `unanswered_messages()` | Contact messages badge |

### Members

| Metric | Definition | Function | Where it shows |
| --- | --- | --- | --- |
| Active members | Memberships in active or grace, every tier | `membership_section()["total_active"]` | card, tier table, summary, export |
| Active by tier | The same, per tier (tiers on offer or with running members, cheapest first; no guest passes) | `membership_section()["tiers"][].active` | tier table and chart, summary, export |
| New this month | Memberships whose first successful payment fell this month, plus comps that started this month | `membership_section()` new, totals.new | card, tier table, summary, export |
| Renewing this month | Memberships paid this month whose first payment was earlier | `membership_section()` renewing | tier table, summary, export |
| Lapsing this month | In grace, or active, not renewing automatically and ending this month | `membership_section()` lapsing | tier table, summary, export |
| Expired this month | Expired with an end date this month | `membership_section()` expired | tier table, summary, export |
| By status | Memberships in each status, guest passes aside | `memberships_by_status()` | summary |
| Feed access without an ID check | Active accounts with feed access from any source and no valid ID check | `feed_access_without_id_check()` | age verification card and page |
| Email list | Confirmed newsletter subscribers | `email_list()` | card, export |

### Money

| Metric | Definition | Function | Where it shows |
| --- | --- | --- | --- |
| Revenue this month | Membership and guest payments this month, not failed, no comps, refunds subtracted, plus donations (not failed, refunds subtracted) | `revenue_for(today)["total"]` | card, revenue table, export |
| Revenue by tier, guest passes and donations | The same, split | `revenue_for()["rows"]` | revenue table, export |
| Revenue by month and method | Membership and guest payments per month and method, refunds subtracted, no comps | `revenue_by_method()` | summary |
| Guest visits | Successful guest pass payments per month | `guest_visits_by_month()` | summary |

### Activity, over the chosen range (30 days, 90 days or 12 months)

| Metric | Definition | Function | Where it shows |
| --- | --- | --- | --- |
| Revenue and payments over time | Successful payments per week (30 and 90 days) or month (12 months), no comps | `series()` | charts |
| RSVPs over time | Party sizes of going RSVPs, by the event's date | `series()` | chart |
| Feed posts over time | Posts out of review, by the date posted | `series()` | chart |
| Posts and comments | In the range | `feed_section()` | Feed table, export |
| Active posters this week | Distinct authors of posts in the last 7 days | `feed_section()` | Feed table, export |

### Events

| Metric | Definition | Function | Where it shows |
| --- | --- | --- | --- |
| Going | Party sizes of going RSVPs (the stored final count after RSVPs are purged) | `event_counts()` | Coming up, events table, RSVP counts page, events list, export |
| Waitlist | Waitlisted RSVPs | `event_counts()` | RSVP counts page |
| Checked in | Party sizes checked in (the stored final count after the purge) | `event_counts()` | events table, RSVP counts page, export |

## Who sees what

| Who | What they see on the admin dashboard |
| --- | --- |
| Admin and Staff roles; superusers count as admins | Everything: the cards, the range switch, the charts, the tables, Coming up, the export and the age verification card. Only admins can change the setting. |
| Moderators | Open reports, posts awaiting approval and ID checks needed. No revenue and no membership figures. |
| Door volunteers (the desk permission, no role) | ID checks needed. |
| Other staff accounts (permissions only) | The waiting cards their permissions cover. |

## The export

**Export** (`admin:metrics_export`, POST only, Admin and Staff roles) downloads the
dashboard's figures for the chosen range as CSV. It follows the same suppression, and
each download goes in the audit log.
