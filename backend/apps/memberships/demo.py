"""Development-only membership demo data. Called by seed_demo when DEBUG is on.

Tiers and the agreement are flagged is_placeholder, so with DEBUG off they are
never offered and joining is refused while the placeholder agreement is current.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from apps.accounts.models import User
from apps.education.models import Opportunity
from apps.events.models import EventTag

from .models import (
    AgreementSignature,
    IdCheck,
    Membership,
    MembershipAgreement,
    Payment,
    Tier,
)

# The seven tiers of the membership page, with the same slugs, prices and rules as the
# club's draft in /content/membership.yaml (prices and rules await the club's approval),
# plus the door guest pass offered on the Guests page.
TIERS = [
    {
        "slug": "community",
        "name": "Community",
        "description": "Education nights and open community events.",
        "perks": ["Education nights", "Open community events"],
        "price_cents": 0,
        "interval": Tier.Interval.MONTH,
        "renews": True,
        "event_access": Tier.EventAccess.TAGGED,
        "allowed_event_tags": ["community"],
        "grants_feed_access": False,
        "sort_order": 10,
    },
    {
        "slug": "first-fridays",
        "name": "First Fridays",
        "description": "A first look, on the first Friday of the month.",
        "perks": ["The first Friday event of the month", "Ends on its own after a week"],
        "price_cents": 0,
        "interval": Tier.Interval.ONCE,
        "duration_days": 7,
        "events_per_month": 1,
        "event_access": Tier.EventAccess.TAGGED,
        "allowed_event_tags": ["first_friday"],
        "grants_feed_access": False,
        "grants_members_education": False,
        "sort_order": 20,
    },
    {
        "slug": "limited",
        "name": "Limited",
        "description": "One club event every month.",
        "perks": ["One club event each month", "Premium Discord access"],
        "price_cents": 2000,
        "interval": Tier.Interval.MONTH,
        "renews": True,
        "events_per_month": 1,
        "premium_discord": True,
        "sort_order": 30,
    },
    {
        "slug": "trial",
        "name": "Trial",
        "description": "Two weeks of club events before you decide.",
        "perks": ["Club events for two weeks", "One payment, no renewal"],
        "price_cents": 2000,
        "interval": Tier.Interval.ONCE,
        "duration_days": 14,
        "sort_order": 40,
    },
    {
        "slug": "limited-plus",
        "name": "Limited +",
        "description": "One club event a month, with a guest.",
        "perks": ["One club event each month", "A guest comes free", "Premium Discord access"],
        "price_cents": 3500,
        "interval": Tier.Interval.MONTH,
        "renews": True,
        "events_per_month": 1,
        "guests_included_per_event": 1,
        "premium_discord": True,
        "sort_order": 50,
    },
    {
        "slug": "rose",
        "name": "Rose",
        "description": "Every club event, as often as you like.",
        "perks": ["Unlimited club events", "Discounted guest entry", "Premium Discord access"],
        "price_cents": 4000,
        "interval": Tier.Interval.MONTH,
        "renews": True,
        "guest_discount": True,
        "premium_discord": True,
        "is_featured": True,
        "sort_order": 60,
    },
    {
        "slug": "rose-plus",
        "name": "Rose +",
        "description": "Every club event, with a guest.",
        "perks": [
            "Unlimited club events",
            "One guest free at each event",
            "Discounted entry for more guests",
            "Premium Discord access for two",
        ],
        "price_cents": 5500,
        "interval": Tier.Interval.MONTH,
        "renews": True,
        "guests_included_per_event": 1,
        "guest_discount": True,
        "premium_discord": True,
        "sort_order": 70,
    },
    {
        "slug": "guest-night",
        "name": "Guest night pass",
        "description": "Placeholder price for development. One evening, paid at the door.",
        "perks": ["One open evening", "A host to show you around"],
        "price_cents": 1500,
        "interval": Tier.Interval.ONCE,
        "duration_days": 1,
        "grants_feed_access": False,
        "grants_members_events": False,
        "grants_members_education": False,
        "is_guest_pass": True,
        "sort_order": 80,
    },
]

AGREEMENT_BODY = (
    "<p><strong>Placeholder agreement for development.</strong> The real text is "
    "written and published by the board before joining opens.</p>"
    "<p>As a member I agree to:</p>"
    "<ul><li>Follow the community agreements on every visit.</li>"
    "<li>Treat consent as ongoing, and accept a no without question.</li>"
    "<li>Keep what I see and hear here private, including who I see.</li>"
    "<li>Never photograph or record anyone inside the house.</li>"
    "<li>Speak to a host if anything feels wrong.</li></ul>"
    "<p>I understand that membership can be suspended or ended if I break these "
    "agreements, and that I must be 18 or older and show a valid photo ID.</p>"
    "<p>Dues pay for rent, utilities and supplies. Refunds are at the board's discretion.</p>"
    "<p>This agreement is kept with my account. Only staff can see the name I sign with.</p>"
)

MEMBERS_ONLY_OPPORTUNITIES = [
    {
        "slug": "members-advanced-negotiation-lab",
        "title": "Advanced Negotiation Lab",
        "summary": "A small, hands-on lab for members who want to sharpen how they negotiate.",
        "body": (
            "We work in pairs through real scenarios: renegotiating mid-evening, holding a "
            "boundary kindly, and checking in without breaking the mood.\n\n"
            "Places are limited to twelve so everyone gets time with the facilitators."
        ),
        "category": Opportunity.Category.WORKSHOP,
        "level": Opportunity.Level.INTERMEDIATE,
        "location_label": "The Library",
        "cta_label": "Reserve a place",
        "cta_url": "/events",
        "sort_order": 90,
    },
    {
        "slug": "members-mentorship-circle",
        "title": "Mentorship Circle",
        "summary": "Monthly small-group conversation with an experienced member as host.",
        "body": (
            "Bring questions, bring stories, or just listen. Circles are six people and a "
            "host, matched by interest.\n\nWhat is said in the circle stays in the circle."
        ),
        "category": Opportunity.Category.CLASS,
        "level": Opportunity.Level.ALL,
        "location_label": "The Parlor",
        "cta_label": "Ask about a circle",
        "cta_url": "/contact",
        "sort_order": 95,
    },
]

# (email, display name, tier slug, status, how the demo row is set up)
DEMO_MEMBERS = [
    ("member.pending@example.org", "demo_pending", "limited", "pending"),
    ("member.active@example.org", "demo_active", "rose", "active"),
    ("member.limited@example.org", "demo_limited", "limited", "active"),
    ("member.online@example.org", "demo_online", "rose-plus", "online"),
    ("member.awaiting@example.org", "demo_awaiting_id", "limited-plus", "awaiting_id"),
    ("member.community@example.org", "demo_community", "community", "free_pending"),
    ("member.grace@example.org", "demo_grace", "limited", "grace"),
    ("member.expired@example.org", "demo_expired", "trial", "expired"),
    ("member.cancelled@example.org", "demo_cancelled", "rose", "cancelled"),
    ("member.suspended@example.org", "demo_suspended", "rose", "suspended"),
    ("guest.first@example.org", "demo_guest", "guest-night", "pending"),
    ("guest.returning@example.org", "demo_guest_returning", "guest-night", "guest_visits"),
]


DESK_GROUP = "Door desk"
DESK_PERMISSIONS = [
    ("memberships", "view_membership"),
    ("memberships", "change_membership"),
    ("memberships", "view_payment"),
    ("memberships", "view_tier"),
]


def _desk_volunteer(password):
    """A staff account that can use the door desk and nothing else in the admin."""
    group, _ = Group.objects.get_or_create(name=DESK_GROUP)
    group.permissions.set(
        Permission.objects.get(content_type__app_label=app, codename=codename)
        for app, codename in DESK_PERMISSIONS
    )
    user = User.objects.filter(email="desk.volunteer@example.org").first()
    if user is None:
        user = User.objects.create_user(
            email="desk.volunteer@example.org", display_name="desk_volunteer", is_staff=True
        )
    user.is_staff = True
    user.set_password(password)
    user.save()
    user.mark_email_verified()
    user.groups.add(group)
    return user


def _pay(membership, staff, cents, method, when, status=Payment.Status.SUCCEEDED, **extra):
    return Payment.objects.create(
        membership=membership,
        amount_cents=cents,
        method=method,
        status=status,
        recorded_by=None if method == Payment.Method.ONLINE else staff,
        created_at=when,
        **extra,
    )


def _online(membership, label):
    membership.source = Membership.Source.PROVIDER
    membership.provider = "sandbox"
    membership.provider_customer_ref = f"sbx_cus_demo_{label}"
    membership.provider_subscription_ref = f"sbx_sub_demo_{label}"


def _build(user, tier, kind, staff, now):
    days = lambda n: timedelta(days=n)  # noqa: E731
    m = Membership(user=user, tier=tier, created_at=now - days(70))

    if kind == "pending":
        m.created_at = now - days(3)
        m.save()
        return m

    if kind == "free_pending":
        # A free tier: nothing to pay, waiting for the first-visit ID check.
        m.created_at = now - days(2)
        m.paid_awaiting_id_check = True
        m.save()
        return m

    if kind == "awaiting_id":
        m.created_at = now - days(1)
        _online(m, "awaiting")
        m.paid_awaiting_id_check = True
        m.save()
        _pay(m, staff, tier.price_cents, Payment.Method.ONLINE, now - days(1), **_ref("a"))
        return m

    m.save()
    IdCheck.objects.create(user=m.user, membership=m, checked_by=staff)

    if kind == "active":
        for months_ago in (2, 1, 0):
            _pay(m, staff, tier.price_cents, Payment.Method.CASH, now - days(30 * months_ago + 5))
        m.start_new_period(now - days(5))
        m.status = Membership.Status.ACTIVE
    elif kind == "online":
        _online(m, "online")
        m.auto_renew = True
        _pay(m, staff, tier.price_cents, Payment.Method.ONLINE, now - days(40), **_ref("o"))
        m.start_new_period(now - days(40))
        m.status = Membership.Status.ACTIVE
    elif kind == "grace":
        _pay(m, staff, tier.price_cents, Payment.Method.CARD_IN_PERSON, now - days(33))
        m.start_new_period(now - days(33))
        m.status = Membership.Status.GRACE
        m.grace_started_at = now - days(3)
    elif kind == "expired":
        paid = _pay(m, staff, tier.price_cents, Payment.Method.CASH, now - days(60))
        _pay(
            m,
            staff,
            1000,
            Payment.Method.CASH,
            now - days(58),
            Payment.Status.REFUNDED,
            refund_of=paid,
            note="Partial refund",
        )
        m.start_new_period(now - days(60))
        m.end(Membership.Status.EXPIRED, now - days(23))
    elif kind == "cancelled":
        _pay(m, staff, tier.price_cents, Payment.Method.CASH, now - days(50))
        m.start_new_period(now - days(50))
        m.end(Membership.Status.CANCELLED, now - days(20))
    elif kind == "guest_visits":
        # A returning guest: three past evenings on the same pass, closed after each night.
        for days_ago in (75, 40, 9):
            _pay(m, staff, tier.price_cents, Payment.Method.CASH, now - days(days_ago))
        m.start_new_period(now - days(9))
        m.end(Membership.Status.EXPIRED, now - days(8))
    elif kind == "suspended":
        _pay(m, staff, tier.price_cents, Payment.Method.CARD_IN_PERSON, now - days(100))
        m.start_new_period(now - days(100))
        m.status = Membership.Status.SUSPENDED
    m.save()
    return m


def _ref(label):
    return {"provider_payment_ref": f"sbx_pay_demo_{label}_{secrets.token_hex(4)}"}


def upsert_tiers(placeholder):
    """Create or update TIERS, with their event tags; returns {slug: tier}.

    Other tiers are no longer offered (their memberships keep them). Placeholder tiers
    are only ever offered with DEBUG on.
    """
    defaults = {
        "duration_days": None,
        "grants_feed_access": True,
        "grants_members_events": True,
        "grants_members_education": True,
        "renews": False,
        "events_per_month": None,
        "guests_included_per_event": 0,
        "guest_discount": False,
        "premium_discord": False,
        "event_access": Tier.EventAccess.ALL,
        "is_featured": False,
        "is_guest_pass": False,
        "is_active": True,
    }
    tiers = {}
    for data in TIERS:
        values = {**defaults, **data}
        slug = values.pop("slug")
        tag_slugs = values.pop("allowed_event_tags", [])
        tier, _ = Tier.objects.update_or_create(slug=slug, defaults=values)
        tier.allowed_event_tags.set(EventTag.objects.filter(slug__in=tag_slugs))
        if tier.is_placeholder != placeholder:
            Tier.objects.filter(pk=tier.pk).update(is_placeholder=placeholder)
        tiers[slug] = tier
    Tier.objects.exclude(slug__in=tiers).update(is_active=False)
    return tiers


def seed_memberships(password):
    """Returns {display_name: email} for the demo accounts, all with `password`. DEBUG only."""
    if not settings.DEBUG:
        raise ImproperlyConfigured("Membership demo data is for development only.")
    now = timezone.now()
    tiers = upsert_tiers(placeholder=True)

    agreement = MembershipAgreement.objects.filter(is_placeholder=True).first()
    if agreement is None:
        agreement = MembershipAgreement(title="Membership agreement", body=AGREEMENT_BODY)
        agreement.is_placeholder = True
        agreement.published_at = now
        agreement.save()

    for data in MEMBERS_ONLY_OPPORTUNITIES:
        values = dict(data)
        slug = values.pop("slug")
        Opportunity.objects.update_or_create(
            slug=slug, defaults={**values, "members_only": True, "is_published": True}
        )

    staff = _desk_volunteer(password)
    accounts = {"desk_volunteer": "desk.volunteer@example.org"}
    for email, display_name, tier_slug, kind in DEMO_MEMBERS:
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(
                email=email, display_name=display_name, password=password
            )
        else:
            user.set_password(password)
        user.save()
        user.mark_email_verified()
        accounts[display_name] = email
        AgreementSignature.objects.get_or_create(
            user=user, agreement=agreement, defaults={"typed_name": f"Demo Person {user.pk}"}
        )
        if not Membership.objects.filter(user=user).exists():
            _build(user, tiers[tier_slug], kind, staff, now)
    return accounts
