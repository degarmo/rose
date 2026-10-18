"""The contract every payment provider implements.

Adding a real processor means writing one subclass of PaymentProvider and
adding its key to PAYMENT_PROVIDERS. Nothing else changes: the service applies
normalised ProviderEvents, whatever the processor calls them.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ProviderError(Exception):
    """A provider refused or failed an operation."""


class WebhookVerificationError(Exception):
    """The webhook signature is missing or wrong. The request is rejected."""


@dataclass(frozen=True)
class CheckoutSession:
    redirect_url: str
    provider_ref: str


CHECKOUT_COMPLETED = "checkout_completed"
PAYMENT_SUCCEEDED = "payment_succeeded"
PAYMENT_FAILED = "payment_failed"
SUBSCRIPTION_CANCELLED = "subscription_cancelled"
REFUNDED = "refunded"

EVENT_TYPES = frozenset(
    {CHECKOUT_COMPLETED, PAYMENT_SUCCEEDED, PAYMENT_FAILED, SUBSCRIPTION_CANCELLED, REFUNDED}
)


@dataclass(frozen=True)
class ProviderEvent:
    """A provider event, normalised. `membership_ref` is our reference code,
    passed to the provider at checkout and echoed back in its events."""

    event_id: str
    type: str
    membership_ref: str | None = None
    customer_ref: str | None = None
    subscription_ref: str | None = None
    payment_ref: str | None = None
    amount_cents: int | None = None
    payload: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.type not in EVENT_TYPES:
            raise ValueError(f"Unknown event type {self.type!r}")


class PaymentProvider(ABC):
    key: str = ""
    label: str = ""
    #: Online providers take payment through a hosted checkout and send webhooks.
    online: bool = True

    @abstractmethod
    def create_checkout(self, membership, success_url, cancel_url) -> CheckoutSession:
        """Start a hosted checkout for the membership's tier price."""

    @abstractmethod
    def parse_webhook(self, request) -> list[ProviderEvent]:
        """Verify the signature (raise WebhookVerificationError) and normalise events."""

    @abstractmethod
    def cancel_subscription(self, membership) -> None:
        """Stop future renewals. Access continues to the end of the paid period."""

    @abstractmethod
    def resume_subscription(self, membership) -> None:
        """Turn renewals back on for a subscription stopped with cancel_subscription."""

    @abstractmethod
    def refund(self, payment, amount_cents) -> str | None:
        """Refund some or all of a payment. Returns the provider's refund reference."""
