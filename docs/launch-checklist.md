# Launch checklist

Everything the club must supply or approve before the site goes live. Each item
has an owner; replace `[owner]` with a name before starting.

## Content

- [ ] **Content approval, file by file.** Each draft in `/content` is read, corrected
      (including its `notes`) and marked `status: approved` by a board member, then loaded
      (Admin > Page copy > Load site content; docs/content.md). Owner: [owner]
  - [ ] `site.yaml`: hours, address (street address public, or "shared with confirmed
        visitors"?), directions, contact email, Discord link. Owner: [owner]
  - [ ] `home.yaml` and `values.yaml`. Owner: [owner]
  - [ ] `about.yaml`. Owner: [owner]
  - [ ] `staff.yaml`: confirm each name and role from the 2024 newsletter, add bios, then
        publish the profiles. Owner: [owner]
  - [ ] `visit.yaml` and `house-rules.yaml`: settle the phone-use conflict between the
        General Rules and the Membership Terms. Owner: [owner]
  - [ ] `faq.yaml`. Owner: [owner]
  - [ ] `guests.yaml`. Owner: [owner]
  - [ ] `membership.yaml`: tier prices, the Limited plans' one-event rule, and the refund
        policy (the old plan pages and the Membership Terms disagree). Owner: [owner]
  - [ ] `education.yaml` and `events.yaml`. Owner: [owner]
  - [ ] `rentals.yaml`: what is included, and rates if any are to be published.
        Owner: [owner]
  - [ ] `volunteer.yaml`: whether to publish the volunteer contract. Owner: [owner]
  - [ ] `donate.yaml`, plus who checks are payable to and the mailing address in Site
        settings. Owner: [owner]
  - [ ] `contact.yaml` and `privacy.yaml`. Owner: [owner]
  - [ ] `redirects.yaml` reviewed against the old site before the domain moves.
        Owner: [owner]
- [ ] **Site settings**: tagline, hours, neighbourhood, directions text, public
      contact email. Owner: [owner]
- [ ] **Privacy page** reviewed and approved (what is stored, for how long, who
      can see it, how to delete). Owner: [owner]
- [ ] **Community guidelines** for the member feed written and published (Admin >
      Feed > Guidelines). Owner: [owner]
- [ ] **Image consent review**: every site image checked in Admin > Image review;
      anything with a recognisable face has written consent on file, or is kept
      hidden. Owner: [owner]
- [ ] **Image rights and consent for the old site's images**: for each line in
      `docs/image-sources.txt`, the club confirms it owns the image (Wix stock images
      cannot be reused) and has written consent from anyone recognisable, before the line
      is uncommented and fetched. Owner: [owner]
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
- [ ] **Donation acknowledgement wording reviewed by the club's accountant**, entered in
      Admin > Acknowledgement wording, with the legal name and EIN in Site settings.
      Owner: [owner]
- [ ] **Guest night pass** price and description confirmed. Owner: [owner]
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
