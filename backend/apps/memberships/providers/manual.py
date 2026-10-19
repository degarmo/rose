from .base import CheckoutSession, PaymentProvider, ProviderError, WebhookVerificationError


class ManualProvider(PaymentProvider):
    """Payment in person at the door, recorded by staff on the door desk.

    There is no checkout and there are no webhooks: the join flow goes straight
    to a confirmation with a reference code, and staff record the payment.
    """

    key = "manual"
    label = "Pay at your first visit"
    online = False

    def create_checkout(self, membership, success_url, cancel_url) -> CheckoutSession:
        raise ProviderError("In-person payments have no online checkout.")

    def create_one_time_checkout(
        self, amount_cents, purpose, success_url, cancel_url
    ) -> CheckoutSession:
        raise ProviderError("In-person payments have no online checkout.")

    def parse_webhook(self, request):
        raise WebhookVerificationError("In-person payments do not send webhooks.")

    def cancel_subscription(self, membership) -> None:
        """Nothing to cancel remotely; the membership simply ends at period end."""

    def resume_subscription(self, membership) -> None:
        raise ProviderError("In-person memberships do not renew automatically.")

    def refund(self, payment, amount_cents) -> str | None:
        """Staff hand the money back in person; there is no remote reference."""
        return None
