# Payments

Membership payments go through a small provider-agnostic layer in
`backend/apps/memberships/providers/`. Two providers ship:

| Key | Class | Online | Where it runs |
| --- | --- | --- | --- |
| `manual` | `ManualProvider` | No | Always. Payment in person at the door, recorded by staff on the door desk. |
| `sandbox` | `SandboxProvider` | Yes | Development and tests only. A fake hosted checkout at `/dev/checkout/<token>` with Pay, Fail and Cancel buttons that post signed fake webhooks to the real webhook endpoint. Constructing it with `DEBUG` off raises `ImproperlyConfigured`. |

A real processor is one more class and one more key in `PAYMENT_PROVIDERS`.

## The interface (`providers/base.py`)

```python
class PaymentProvider(ABC):
    key: str            # used in settings and in /api/payments/webhook/<key>/
    label: str          # shown on the join page's payment step
    online: bool        # True: hosted checkout and webhooks

    def create_checkout(self, membership, success_url, cancel_url) -> CheckoutSession: ...
    def parse_webhook(self, request) -> list[ProviderEvent]: ...
    def cancel_subscription(self, membership) -> None: ...
    def resume_subscription(self, membership) -> None: ...
    def refund(self, payment, amount_cents) -> str | None: ...
```

- `create_checkout` starts a hosted checkout for `membership.tier.price_cents`. Pass
  `membership.reference_code` to the processor as metadata (or client reference), so its
  events can be matched back. Return `CheckoutSession(redirect_url, provider_ref)`.
- `parse_webhook` verifies the signature using the processor's own scheme and raises
  `WebhookVerificationError` if it is missing or wrong. It returns normalised
  `ProviderEvent`s (below). It must not change any data.
- `cancel_subscription` and `resume_subscription` stop or restart renewals. Access always
  continues to the end of the paid period.
- `refund` refunds part or all of a payment and returns the processor's refund reference.
  The door desk records the refund row; a later `refunded` webhook for the same refund is
  harmless.
- Raise `ProviderError` for anything the processor refuses; the user sees its message.

### Adding a processor

1. Write `providers/<name>.py` with a `PaymentProvider` subclass. Read its secrets from
   settings (add them to `config/settings.py` through `env(...)`, `.env.example` and
   `render.yaml`).
2. Add the class to `AVAILABLE` in `providers/registry.py`.
3. Set `PAYMENT_PROVIDERS=manual,<key>` in the environment. Startup fails if `manual` is
   missing or a key is unknown.
4. Point the processor's webhook at `https://<site>/api/payments/webhook/<key>/`.
5. Configure the processor's billing descriptor and receipt name (below).
6. Run the checklist at the end of this page against the processor's test mode.

Nothing outside the adapter changes. `providers/service.py` is the only code that applies
provider events.

## Event normalisation

The adapter maps each processor event onto one of five types. The service finds the
membership by `membership_ref` (our reference code) or, failing that, by
`subscription_ref`, so events may arrive in any order.

| `ProviderEvent.type` | Typical processor event | What the service does |
| --- | --- | --- |
| `checkout_completed` | checkout session completed | Marks the membership as online (`source=provider`, `provider`), stores customer and subscription references, turns auto-renew on for subscriptions. |
| `payment_succeeded` | invoice paid, charge succeeded | Stores the references, records a succeeded `Payment` (method `online`), then activates or extends. A first activation needs an ID check on file; without one the membership stays `pending_payment` with `paid_awaiting_id_check` and the door desk activates it after the check. |
| `payment_failed` | invoice payment failed, charge failed | Records a failed `Payment`. Status does not change; the lifecycle handles lapsing. The member sees "Payment did not go through" and can try again. |
| `subscription_cancelled` | subscription deleted or set to cancel | Turns auto-renew off and sets `cancel_at_period_end`. |
| `refunded` | charge refunded | Records a refund `Payment` pointing at the original (found by `payment_ref`). |

Fields: `event_id` (the processor's unique id; required), `membership_ref`,
`customer_ref`, `subscription_ref`, `payment_ref`, `amount_cents`, and `payload` (a small
dict of non-sensitive fields kept for staff to read in Admin > Webhook events; never card
data).

### Idempotency and storage

`handle_events` stores every event in `WebhookEvent` first, under a unique
`(provider, event_id)` constraint. An event id seen before is skipped, so retries and
duplicates are never applied twice. The event is then applied in its own transaction. If
applying fails (for example, no membership matches), the error is stored on the row for
staff and the endpoint still answers 200, because the event is safely recorded; the
processor would otherwise retry an event that will never apply. A bad signature is
rejected with 400 and nothing is stored. Unknown or offline provider keys are 404.

## Settings

| Setting | Default | Notes |
| --- | --- | --- |
| `PAYMENT_PROVIDERS` | `manual,sandbox` with DEBUG on, `manual` with DEBUG off | Comma-separated keys. `manual` is required. `sandbox` refuses to start with DEBUG off. |
| `MERCHANT_DISPLAY_NAME` | `Rose` | The merchant name on receipts. Set the processor's billing descriptor to match. |
| `MEMBERSHIP_GRACE_DAYS` | `7` | Days of continued access after a period ends. |
| `MEMBERSHIP_PENDING_EXPIRY_DAYS` | `30` | How long an unpaid reference code stays open. |
| `MEMBERSHIP_REMINDER_DAYS` | `(14, 3)` | In code. Renewal reminders for active memberships that do not renew automatically. |
| `PAYMENT_WEBHOOK_RATE_LIMIT` | `120/m` | In code. Per hashed client IP. |

## Billing descriptor and receipt names

What appears on a bank statement or an emailed receipt can be seen by anyone who shares
the account. Keep it neutral.

- **Statement descriptor**: the same as `MERCHANT_DISPLAY_NAME` (for example "ROSE
  MEMBERSHIP"). Never the organisation's full name, its address or anything describing its
  activities.
- **Product name** at the processor: "Membership". Tier names are not sent as product
  names.
- **Processor receipts and invoices**: turn off processor-sent receipt email if it cannot
  be made neutral; the site's own receipt (`/account/receipts/<id>`) shows only the merchant
  name, date, amount, reference and "Membership".
- **Customer records** at the processor: email only. Do not send display names or typed
  signature names.

## Test checklist

Run against the sandbox in development, and against the processor's test mode before
switching a real processor on.

- [ ] Join with the online method; the browser goes to the hosted checkout.
- [ ] Coming back to `/join/confirming` alone changes nothing (try opening it before paying).
- [ ] A successful payment activates the membership for someone with an ID check on file,
      and leaves someone without one as "Paid, awaiting ID check".
- [ ] The door desk "Activate" completes the second case after ticking "Photo ID checked".
- [ ] A failed payment shows "Payment did not go through" with "Try again", and records a
      failed payment row.
- [ ] Cancelling at the checkout returns to `/join?cancelled=1` and records nothing.
- [ ] Sending the same webhook twice changes nothing the second time.
- [ ] A webhook with a wrong signature gets 400 and is not stored.
- [ ] `payment_succeeded` before `checkout_completed` still ends in the right state.
- [ ] A renewal webhook naming only the subscription extends the period.
- [ ] Turning auto-renew off, then on, reaches the processor; cancelling keeps access to the
      period end.
- [ ] A door desk refund of an online payment reaches the processor and adds a refund row.
- [ ] The statement descriptor and any processor email are neutral.
- [ ] With DEBUG off, the sandbox is absent: `/api/payments/sandbox/...` and
      `/api/payments/webhook/sandbox/` are 404 and the join page offers only the in-person
      method (`tests/test_payment_webhooks.py`, `tests/test_membership_join.py`).
