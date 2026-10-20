# Email

Every message the site sends is neutral: subjects never name the organisation,
an event or its category, and bodies say "your account", "your plans" or
"membership". All mail goes through `apps.core.email.send_neutral_mail`.

## Provider

`EMAIL_PROVIDER` picks the backend; the transactional providers go through
django-anymail, so switching is one setting and one key:

| `EMAIL_PROVIDER` | Needs |
| --- | --- |
| `postmark` (the blueprint's default) | `POSTMARK_SERVER_TOKEN` |
| `amazon_ses` | `SES_ACCESS_KEY_ID`, `SES_SECRET_ACCESS_KEY`, `SES_REGION` |
| `resend` | `RESEND_API_KEY` |
| `mailgun` | `MAILGUN_API_KEY`, `MAILGUN_SENDER_DOMAIN` (and `MAILGUN_API_URL` for the EU region) |
| `smtp` | `EMAIL_URL`, for example `smtp+tls://user:password@host:587` |
| `console` | Development only: prints mail. Refused in staging and production |

Open and click tracking are switched off for every provider
(`ANYMAIL.SEND_DEFAULTS`): they would tie a member's reading to their address.
Also switch tracking off in the provider's own dashboard, and turn off any
"message archive" or "content retention" it offers, or set it to the shortest
period.

`EMAIL_SENDER_NAME` (default: the site's name, `SITE_NAME`) and `EMAIL_SENDER_ADDRESS` set the From
header. Message-IDs use the sender's domain, never the server's host name.

## Sending domain

Send from a **dedicated subdomain** with a neutral name, for example
`mail.<your-domain>` or `notify.<your-domain>`, and a neutral sender such as
`Rose <hello@mail.<your-domain>>`. A subdomain keeps the main domain's
reputation separate and lets you rotate providers without touching the website.

## DNS records

Your provider shows the exact values; these are their shapes. Add them at your
DNS host for the sending subdomain.

| Record | Name | Value (shape) | Purpose |
| --- | --- | --- | --- |
| TXT (SPF) | `mail.<your-domain>` | `v=spf1 include:<provider's include> -all` | Which servers may send for the subdomain |
| TXT or CNAME (DKIM) | `<selector>._domainkey.mail.<your-domain>` | the provider's public key or CNAME target | Signs each message |
| CNAME (Return-Path / bounce) | for example `pm-bounces.mail.<your-domain>` | the provider's bounce host | Bounces go to the provider, aligned with SPF |
| TXT (DMARC) | `_dmarc.<your-domain>` | `v=DMARC1; p=quarantine; adkim=s; aspf=s; rua=mailto:dmarc@<your-domain>` | Tells receivers to reject unauthenticated mail; start with `p=none` for a week, then `quarantine`, then `reject` |

Use a DMARC report address you control, and send reports to a mailbox only
staff with a reason can read: they list sending IPs, not recipients.

## Bounces and complaints

The site does not receive bounce or complaint webhooks, and nothing in it logs
recipient addresses: the log scrubber removes any address that reaches a log
line. In the provider's dashboard, review bounces and complaints there rather
than exporting them, and never paste recipient addresses into tickets, chats or
shared documents. If you later add the provider's webhooks (for example to
suppress hard bounces), store only a hash of the address, never the address.

## Testing

```sh
python manage.py send_test_email you@example.org --staff your-staff-login@example.org
```

Sends "Test message" through the configured backend. Only an active staff
account may send it, and each send is written to the audit log without the
recipient's address.
