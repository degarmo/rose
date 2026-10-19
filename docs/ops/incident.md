# If data may have leaked

Use this when anything suggests member data left the site: a screenshot of the
member feed posted elsewhere, a lost staff laptop or phone, a leaked
password or API key, a suspicious admin action in the audit log, or a report
from a member. Work in order; write down what you do and when.

## 1. Contain (first hour)

1. **Turn off the member feed if it is involved.** Render > environment group
   `rose-production-settings` > set `FEED_ENABLED` to `false` > save; the web
   service restarts. Every feed page, API path and image link then answers 404
   exactly as if it did not exist, for everyone including staff. Nothing is
   deleted; setting it back to `true` restores everything.
2. **End sessions.**
   - One person: in the admin, untick "active" on their account and save (this
     ends all their sessions at once), or ask them to use "Log out everywhere"
     in Settings > Security.
   - A staff account: untick "staff status" and "active", and delete their TOTP
     device (Admin > Django OTP > TOTP devices) so they must re-enrol.
   - Everyone: rotate `DJANGO_SECRET_KEY` (step 3). Every session, every emailed
     link (verification, reset, RSVP cancel, export download) and every signed
     image link stops working at once.
3. **Lock down the admin** if staff access is in doubt: change
   `DJANGO_ADMIN_PATH` to a new value and tell staff privately.

## 2. Rotate secrets

Rotate anything that may have been exposed. Each is changed in the
environment's `rose-production-secrets` group, then the services redeploy.

| Secret | How to rotate |
| --- | --- |
| `DJANGO_SECRET_KEY` | Generate a new one (deploy.md, step 4). Logs everyone out and voids every emailed link |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | Cloudflare R2 > Manage API tokens > create a new token for the two buckets, update Render, then **revoke the old token** |
| `POSTMARK_SERVER_TOKEN` | Postmark > server > API Tokens > generate, update Render, delete the old one |
| Database password | Render > database > rotate credentials (the connection string updates automatically for linked services) |
| Staff passwords | Ask the person to reset; reset their TOTP device |
| `STAGING_BASIC_AUTH_PASSWORD` | Set a new value |
| Backup key (`age-key.txt`) | Only if the private key itself leaked: generate a new pair, set the new public key as `BACKUP_AGE_RECIPIENT`, and delete old backups encrypted to the old key (`backups/` in the private bucket) |

Signed image links last 60 seconds, so rotating storage keys also ends any
shared image link almost at once.

## 3. Preserve evidence

1. **Logs**: Render keeps service logs for a limited time. Download them now
   (Render > service > Logs > download, or the log stream you configured) for
   web, worker and beat, covering the period in question. They contain no
   member identities (the scrubber removes them), so they can be shared with the
   people investigating.
2. **Audit log**: Admin > Core > Audit log records moderation, door desk,
   exports, signature-name reveals, two-factor events, test emails and backups,
   with who and when. It cannot be edited or deleted. Export what is relevant by
   screenshot or by copying rows into the incident notes; do not export member
   lists.
3. **Database**: take a manual backup in Render (database > Backups > create)
   so the current state is kept even if you later restore.
4. Do not delete accounts, posts or reports involved until the decision makers
   (below) agree; erasing can destroy what you need to understand the incident.

## 4. Understand

- Which data: feed images (the faint watermark names the viewing account and
  the date; raise the image's contrast in any photo editor to read it), profile
  details, RSVPs, membership status, contact messages?
- Which people: whose data, and which account viewed or exported it (audit log,
  watermark)?
- How: a member's screenshot, a compromised account, a staff mistake, a software
  fault?

## 5. Decide about telling members

The decision to notify members, and what to say, belongs to **the board** (or
whoever the launch checklist names as incident lead), not to the person
handling the technical response. Bring them: what happened, what data, how many
people, what has been contained, and what is still unknown. Consider legal
advice about notification duties in Illinois. Members affected should hear it
directly, in neutral language, from an address they recognise, never in a
public post.

## 6. Recover

1. Fix the cause (remove a leaked post, ban an account, patch the fault).
2. Turn the feed back on (`FEED_ENABLED=true`) only when the board agrees.
3. Write a short note of what happened and what changed, kept with the board's
   records, without member names.
