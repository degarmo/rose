# Launch checklist

Everything the club must supply or approve before the site goes live. Each item
has an owner; replace `[owner]` with a name before starting.

## Content

- [ ] **Real copy** for every page (home, about, visit, education, contact, join,
      FAQs) replaces the placeholder text. Owner: [owner]
- [ ] **Site settings**: tagline, hours, neighbourhood, directions text, public
      contact email. Owner: [owner]
- [ ] **Privacy page** reviewed and approved (what is stored, for how long, who
      can see it, how to delete). Owner: [owner]
- [ ] **Community guidelines** for the member feed written and published (Admin >
      Feed > Guidelines). Owner: [owner]
- [ ] **Image consent review**: every site image checked in Admin > Image review;
      anything with a recognisable face has written consent on file, or is kept
      hidden. Owner: [owner]
- [ ] **Quick-exit destination** chosen (default: a weather site) and set in Site
      settings. Owner: [owner]

## Membership and payments

- [ ] **Tier names and prices** (replace the placeholder tiers; set descriptions
      and benefits). Owner: [owner]
- [ ] **Membership agreement** text approved by the board and published.
      Owner: [owner]
- [ ] **Payment processor decision**: in person only for launch, or which online
      processor (docs/payments.md lists what adding one involves). Owner: [owner]
- [ ] **Merchant name** for receipts and bank statements (neutral). Owner: [owner]
- [ ] **Existing member list** prepared as CSV for `import_members`, if any.
      Owner: [owner]

## Domain, email and accounts

- [ ] **Domain** registered, and who controls its DNS. Owner: [owner]
- [ ] **Sender name and address** for email (neutral, on a sending subdomain), and
      the provider account. Owner: [owner]
- [ ] **Private staff inbox** for contact notifications. Owner: [owner]
- [ ] **Staff accounts**: list of people, which need door desk only and which
      need full admin; each has an authenticator app ready. Owner: [owner]
- [ ] **Backup key holders**: two named people keep the offline backup key.
      Owner: [owner]
- [ ] **Incident lead** named, and who decides about notifying members.
      Owner: [owner]

## Before going live

- [ ] Staging walked through by two volunteers on a phone (register, RSVP, join,
      door desk, feed). Owner: [owner]
- [ ] Production deployed (docs/ops/deploy.md), first superuser enrolled in
      two-step login, test email received. Owner: [owner]
- [ ] Restore drill done once on production backups (docs/ops/restore.md).
      Owner: [owner]
- [ ] Staff guide (docs/staff-guide.md) read by every volunteer with an account.
      Owner: [owner]
