"""Tier rules for members-only events: included events, monthly counts, guests, free tiers."""

import json
from datetime import datetime, time, timedelta
from io import StringIO

import pytest
import yaml
from django.contrib import admin
from django.core import mail
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone

from apps.core.models import AuditLog
from apps.events import access
from apps.events.models import RSVP, Event, EventTag
from apps.events.services import RSVPError, cancel_rsvp, submit_rsvp
from apps.memberships import desk, lifecycle, usage
from apps.memberships.access import events_remaining, month_of
from apps.memberships.models import Membership, MembershipUsage, Payment, Tier
from tests.conftest import staff_login

pytestmark = pytest.mark.django_db


def on_day(months_ahead, day, hour=19):
    """A local time on a given day of a month that is still ahead."""
    first = timezone.localdate().replace(day=1)
    for _ in range(months_ahead):
        first = (first + timedelta(days=32)).replace(day=1)
    return timezone.make_aware(datetime.combine(first.replace(day=day), time(hour)))


def today_at(hour):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hour)))


@pytest.fixture
def tag():
    return EventTag.objects.get(slug="community")


@pytest.fixture
def members_event(make_event):
    def make(**kwargs):
        kwargs.setdefault("starts_at", on_day(1, 10))
        return make_event(audience=Event.Audience.MEMBERS, **kwargs)

    return make


@pytest.fixture
def limited(make_tier):
    return make_tier(name="Limited", slug="limited", price_cents=2000, events_per_month=1)


@pytest.fixture
def member_of(make_membership):
    def make(tier, **kwargs):
        return make_membership(tier=tier, **kwargs)

    return make


def rsvp_api(client, event, party_size=1):
    return client.post(f"/api/events/{event.slug}/rsvp/", {"party_size": party_size}, format="json")


# The tier itself


def test_free_is_derived_from_the_price(make_tier):
    tier = make_tier(price_cents=0)
    assert tier.is_free
    tier.price_cents = 1500
    tier.save(update_fields=["price_cents"])
    tier.refresh_from_db()
    assert not tier.is_free


def test_tiers_list_from_the_lowest_price_with_sort_order_breaking_ties(client, make_tier):
    for slug, price, order in [
        ("rose-plus", 5500, 70),
        ("trial", 2000, 40),
        ("community", 0, 10),
        ("rose", 4000, 60),
        ("limited", 2000, 30),
        ("first-fridays", 0, 20),
        ("limited-plus", 3500, 50),
    ]:
        make_tier(slug=slug, price_cents=price, sort_order=order)
    slugs = [tier["slug"] for tier in client.get("/api/membership/tiers/").json()]
    assert slugs == [
        "community",
        "first-fridays",
        "limited",
        "trial",
        "limited-plus",
        "rose",
        "rose-plus",
    ]


def test_tier_payload_carries_the_rules(client, make_tier, tag):
    tier = make_tier(
        slug="community",
        price_cents=0,
        renews=True,
        event_access=Tier.EventAccess.TAGGED,
        guests_included_per_event=0,
        premium_discord=False,
        is_featured=False,
    )
    tier.allowed_event_tags.set([tag])
    data = client.get("/api/membership/tiers/").json()[0]
    assert data["is_free"] and data["renews"] and data["event_access"] == "tagged"
    assert data["allowed_event_tags"] == [{"slug": "community", "name": "Community"}]
    assert data["events_per_month"] is None and data["perks"] == []


def test_a_one_time_pass_cannot_renew(make_tier):
    from django.core.exceptions import ValidationError

    tier = Tier(name="Pass", slug="pass", price_cents=100, interval="once", duration_days=7)
    tier.renews = True
    with pytest.raises(ValidationError, match="does not renew"):
        tier.full_clean()


# Reason codes


def test_tagged_tier_reaches_only_tagged_events(make_tier, member_of, members_event, tag):
    tier = make_tier(event_access=Tier.EventAccess.TAGGED)
    tier.allowed_event_tags.set([tag])
    user = member_of(tier).user
    untagged = members_event()
    tagged = members_event()
    tagged.access_tags.set([tag])
    assert access.can_rsvp(user, untagged) == (False, access.TIER_EVENT_NOT_INCLUDED)
    assert access.can_rsvp(user, tagged) == (True, access.OK)


def test_tier_event_not_included_is_the_panel_state(
    make_tier, member_of, members_event, tag, signed_in
):
    tier = make_tier(event_access=Tier.EventAccess.TAGGED)
    tier.allowed_event_tags.set([tag])
    client, _ = signed_in(user=member_of(tier).user)
    event = members_event()
    rsvp = client.get(f"/api/events/{event.slug}/").json()["rsvp"]
    assert rsvp["state"] == "tier_event_not_included" and not rsvp["can_rsvp"]
    response = rsvp_api(client, event)
    assert response.status_code == 409
    assert response.json() == {
        "code": "tier_event_not_included",
        "detail": "Your membership does not include this event.",
    }


def test_monthly_limit_reached(limited, member_of, members_event, signed_in):
    client, user = signed_in(user=member_of(limited).user)
    first, second = members_event(starts_at=on_day(1, 10)), members_event(starts_at=on_day(1, 20))
    before = client.get(f"/api/events/{first.slug}/").json()["rsvp"]
    assert before["events_remaining"] == 1
    assert rsvp_api(client, first).status_code == 200
    response = rsvp_api(client, second)
    assert response.status_code == 409
    assert response.json()["code"] == "monthly_limit_reached"
    assert response.json()["detail"] == "You have used this month's events on your membership."
    state = client.get(f"/api/events/{second.slug}/").json()["rsvp"]
    assert state["state"] == "monthly_limit_reached" and state["events_remaining"] == 0
    # The event already booked still shows as going and can be changed.
    assert client.get(f"/api/events/{first.slug}/").json()["rsvp"]["state"] == "going"
    assert rsvp_api(client, first).status_code == 200


def test_party_size_exceeds_tier(make_tier, member_of, members_event, signed_in):
    client, _ = signed_in(user=member_of(make_tier(guests_included_per_event=0)).user)
    event = members_event(max_party_size=2)
    assert client.get(f"/api/events/{event.slug}/").json()["rsvp"]["plan_party_limit"] == 1
    response = rsvp_api(client, event, party_size=2)
    assert response.status_code == 409
    assert response.json()["code"] == "party_size_exceeds_tier"
    assert not RSVP.objects.exists()


def test_guests_included_and_event_allowance(make_tier, member_of, members_event, make_user):
    with_guest = member_of(make_tier(guests_included_per_event=1)).user
    solo = member_of(make_tier(guests_included_per_event=0)).user
    event = members_event(max_party_size=2)
    assert access.can_rsvp(with_guest, event, party_size=2) == (True, access.OK)
    assert access.can_rsvp(solo, event, party_size=2)[1] == access.PARTY_SIZE_EXCEEDS_TIER
    generous = members_event(max_party_size=2, guest_allowance=1)
    assert access.plan_party_limit(solo, generous) == 2
    assert access.can_rsvp(solo, generous, party_size=2) == (True, access.OK)


def test_public_events_are_neither_limited_nor_counted(limited, member_of, make_event):
    membership = member_of(limited)
    for day in (10, 11, 12):
        event = make_event(starts_at=on_day(1, day), max_party_size=2)
        submit_rsvp(membership.user, event, 2)
    assert not MembershipUsage.objects.exists()
    assert not RSVP.objects.filter(counts_toward_plan=True).exists()


# Counting


def test_rsvp_and_cancel_move_the_monthly_count(limited, member_of, members_event):
    membership = member_of(limited)
    event = members_event()
    month = month_of(event.starts_at)
    result = submit_rsvp(membership.user, event, 1)
    assert result.rsvp.counts_toward_plan
    assert MembershipUsage.objects.get(membership=membership, month=month).events_used == 1
    assert events_remaining(membership, month) == 0
    cancel_rsvp(result.rsvp)
    assert MembershipUsage.objects.get(membership=membership, month=month).events_used == 0
    assert events_remaining(membership, month) == 1
    # RSVPing again counts again.
    submit_rsvp(membership.user, event, 1)
    assert events_remaining(membership, month) == 0


def test_a_party_size_change_is_not_another_event(make_tier, member_of, members_event):
    membership = member_of(make_tier(events_per_month=2, guests_included_per_event=1))
    event = members_event(max_party_size=2)
    submit_rsvp(membership.user, event, 1)
    submit_rsvp(membership.user, event, 2)
    assert events_remaining(membership, month_of(event.starts_at)) == 1


def test_months_roll_over(limited, member_of, members_event):
    membership = member_of(limited)
    this_month = members_event(starts_at=on_day(1, 10))
    next_month = members_event(starts_at=on_day(2, 10))
    submit_rsvp(membership.user, this_month, 1)
    with pytest.raises(RSVPError) as refused:
        submit_rsvp(membership.user, members_event(starts_at=on_day(1, 25)), 1)
    assert refused.value.code == access.MONTHLY_LIMIT_REACHED
    submit_rsvp(membership.user, next_month, 1)
    rows = MembershipUsage.objects.filter(membership=membership).order_by("month")
    assert [(row.month.day, row.events_used) for row in rows] == [(1, 1), (1, 1)]
    assert rows[1].month > rows[0].month


def test_waitlist_promotion_counts_and_waits_for_room(limited, make_tier, member_of, members_event):
    holder = member_of(make_tier()).user
    membership = member_of(limited)
    full = members_event(starts_at=on_day(1, 10), capacity=1)
    other = members_event(starts_at=on_day(1, 12))
    holder_rsvp = submit_rsvp(holder, full, 1).rsvp
    waiting = submit_rsvp(membership.user, full, 1).rsvp
    assert waiting.status == RSVP.Status.WAITLIST and not waiting.counts_toward_plan

    # The member uses their one event elsewhere; a freed place does not go to them.
    submit_rsvp(membership.user, other, 1)
    cancel_rsvp(holder_rsvp)
    waiting.refresh_from_db()
    assert waiting.status == RSVP.Status.WAITLIST

    # Once that evening is cancelled, the next freed place is theirs and counts.
    cancel_rsvp(RSVP.objects.get(event=other, user=membership.user))
    cancel_rsvp(submit_rsvp(holder, full, 1).rsvp)
    waiting.refresh_from_db()
    assert waiting.status == RSVP.Status.GOING and waiting.counts_toward_plan
    assert events_remaining(membership, month_of(full.starts_at)) == 0


def test_staff_status_changes_keep_the_count(limited, member_of, members_event, admin_client):
    membership = member_of(limited)
    event = members_event()
    rsvp = submit_rsvp(membership.user, event, 1).rsvp
    url = reverse("admin:events_rsvp_change", args=[rsvp.pk])
    response = admin_client.post(
        url, {"status": "cancelled", "party_size": 1, "note_to_hosts": "", "checked_in": ""}
    )
    assert response.status_code == 302
    assert events_remaining(membership, month_of(event.starts_at)) == 1


# Door desk


@pytest.fixture
def desk_client(client, desk_staff):
    staff_login(client, desk_staff)
    return client


def test_walk_in_counts_and_respects_the_limit(limited, member_of, members_event, desk_staff):
    membership = member_of(limited)
    tonight = members_event(starts_at=today_at(12), title="Secret Salon")
    also_tonight = members_event(starts_at=today_at(13))
    rsvp = desk.walk_in(desk_staff, membership, tonight, 1)
    assert rsvp.status == RSVP.Status.GOING and rsvp.checked_in and rsvp.counts_toward_plan
    assert events_remaining(membership) == 0
    with pytest.raises(desk.DeskError, match="No events left this month"):
        desk.walk_in(desk_staff, membership, also_tonight, 1)
    # Checking in again (already on the list) is not another event.
    desk.walk_in(desk_staff, membership, tonight, 1)
    assert MembershipUsage.objects.get(membership=membership).events_used == 1
    entries = AuditLog.objects.filter(category=AuditLog.Category.DOOR_DESK)
    assert {e.action for e in entries} == {"walk_in", "check_in"}
    assert all("Secret Salon" not in f"{e.target_label} {e.reason}" for e in entries)


def test_walk_in_applies_the_tier_rules(make_tier, member_of, members_event, desk_staff, tag):
    tagged = make_tier(event_access=Tier.EventAccess.TAGGED)
    tagged.allowed_event_tags.set([tag])
    tonight = members_event(starts_at=today_at(12), max_party_size=2)
    with pytest.raises(desk.DeskError, match="does not include this event"):
        desk.walk_in(desk_staff, member_of(tagged), tonight, 1)
    with pytest.raises(desk.DeskError, match="allows a party of 1"):
        desk.walk_in(desk_staff, member_of(make_tier()), tonight, 2)
    later = members_event(starts_at=on_day(1, 10))
    with pytest.raises(desk.DeskError, match="tonight's members-only events"):
        desk.walk_in(desk_staff, member_of(make_tier()), later, 1)


def test_walk_in_from_the_desk_page(limited, member_of, members_event, desk_client):
    membership = member_of(limited)
    tonight = members_event(starts_at=today_at(12))
    url = reverse("admin:memberships_door_desk")
    page = desk_client.get(url, {"q": membership.reference_code}).content.decode()
    assert "Check in tonight" in page and "1 left" in page
    desk_client.post(
        url,
        {
            "action": "walk_in",
            "membership": membership.pk,
            "event": tonight.pk,
            "party_size": "1",
            "q": membership.reference_code,
        },
    )
    page = desk_client.get(url, {"q": membership.reference_code}).content.decode()
    assert "0 left" in page
    assert RSVP.objects.get(event=tonight).checked_in


def test_desk_rows_show_the_tier_rules(make_tier, member_of, desk_client):
    rose_plus = member_of(make_tier(guests_included_per_event=1, guest_discount=True))
    page = desk_client.get(
        reverse("admin:memberships_door_desk"), {"q": rose_plus.reference_code}
    ).content.decode()
    assert "Unlimited" in page and "1 included per event" in page and "Guest discount" in page


# Free tiers


@pytest.fixture
def first_fridays(make_tier):
    tier = make_tier(
        name="First Fridays",
        slug="first-fridays",
        price_cents=0,
        interval=Tier.Interval.ONCE,
        duration_days=7,
        events_per_month=1,
    )
    return tier


def join_free(client, agreement, slug):
    return client.post(
        "/api/membership/join/",
        {"tier": slug, "agreement_version": agreement.version, "typed_name": "Sam Realname"},
        format="json",
    )


def test_free_tier_join_has_no_payment_step(signed_in, first_fridays, agreement):
    client, user = signed_in()
    response = join_free(client, agreement, "first-fridays")
    assert response.status_code == 201
    data = response.json()["membership"]
    assert data["status"] == "pending_payment" and data["paid_awaiting_id_check"]
    assert data["status_label"] == "Waiting for ID check"
    assert data["code_expires_at"]  # an unused free code lapses like an unpaid one
    assert data["reference_code"]
    assert not Payment.objects.exists()
    assert "photo ID" in mail.outbox[0].body and "payment" not in mail.outbox[0].body


def test_free_tier_starts_after_the_desk_id_check(signed_in, first_fridays, agreement, desk_staff):
    client, user = signed_in()
    join_free(client, agreement, "first-fridays")
    membership = Membership.objects.get(user=user)
    with pytest.raises(desk.DeskError, match="Check a photo ID"):
        desk.activate_paid_online(desk_staff, membership)
    desk.activate_paid_online(desk_staff, membership, id_checked=True)
    membership.refresh_from_db()
    assert membership.status == Membership.Status.ACTIVE
    assert membership.current_period_end - membership.current_period_start == timedelta(days=7)
    assert not Payment.objects.exists()


def test_free_tier_starts_at_once_with_an_id_check_on_file(
    signed_in, first_fridays, agreement, make_membership
):
    earlier = make_membership(status="expired")
    client, user = signed_in(user=earlier.user)
    response = join_free(client, agreement, "first-fridays")
    assert response.json()["membership"]["status"] == "active"
    assert not mail.outbox  # nothing to bring, so no reference code email


def test_free_tier_can_be_cancelled_before_it_starts(signed_in, first_fridays, agreement):
    client, user = signed_in()
    join_free(client, agreement, "first-fridays")
    assert client.post("/api/membership/cancel/").status_code == 200
    assert Membership.objects.get(user=user).status == Membership.Status.CANCELLED


def test_time_limited_free_tier_expires_without_grace(first_fridays, make_membership):
    membership = make_membership(tier=first_fridays, current_period_end=timezone.now())
    counts = lifecycle.run(timezone.now() + timedelta(minutes=1))
    membership.refresh_from_db()
    assert membership.status == Membership.Status.EXPIRED
    assert counts["free_ended"] == 1 and counts["to_grace"] == 0
    assert not mail.outbox


def test_renewing_free_tier_stays_open(make_tier, make_membership):
    community = make_tier(price_cents=0, renews=True)
    membership = make_membership(tier=community, current_period_end=timezone.now())
    later = timezone.now() + timedelta(minutes=1)
    assert lifecycle.run(later)["free_continued"] == 1
    membership.refresh_from_db()
    assert membership.status == Membership.Status.ACTIVE
    assert membership.current_period_end > later
    assert not mail.outbox


def test_unused_free_codes_lapse(first_fridays, make_membership, settings):
    membership = make_membership(
        tier=first_fridays, status="pending_payment", paid_awaiting_id_check=True
    )
    Membership.objects.filter(pk=membership.pk).update(
        created_at=timezone.now() - timedelta(days=settings.MEMBERSHIP_PENDING_EXPIRY_DAYS + 1)
    )
    lifecycle.run()
    membership.refresh_from_db()
    assert membership.status == Membership.Status.EXPIRED


def test_no_renewal_reminders_for_free_tiers(make_tier, make_membership):
    community = make_tier(price_cents=0, renews=True)
    make_membership(tier=community, current_period_end=timezone.now() + timedelta(days=2))
    assert lifecycle.run()["reminders"] == 0


# Retention and privacy


def test_usage_is_purged_after_13_months(make_membership):
    membership = make_membership()
    today = timezone.localdate()
    months = []
    first = today.replace(day=1)
    for _ in range(16):
        months.append(first)
        first = (first - timedelta(days=1)).replace(day=1)
    for month in months:
        MembershipUsage.objects.create(membership=membership, month=month, events_used=1)
    assert usage.purge_old() == 2
    kept = sorted(MembershipUsage.objects.values_list("month", flat=True))
    assert kept == sorted(months[:14])


def test_usage_is_never_exposed_beyond_your_own_events_remaining(
    limited, member_of, members_event, signed_in, client
):
    membership = member_of(limited)
    event = members_event()
    submit_rsvp(membership.user, event, 1)
    other_client, _ = signed_in(user=member_of(limited).user)
    member_client, _ = signed_in(user=membership.user)

    mine = member_client.get("/api/membership/me/").json()["membership"]
    assert "events_used" not in json.dumps(mine)
    assert member_client.get(f"/api/events/{event.slug}/").json()["rsvp"]["events_remaining"] == 0
    # Someone else sees their own allowance, never this member's.
    assert other_client.get(f"/api/events/{event.slug}/").json()["rsvp"]["events_remaining"] == 1
    for path in ("/api/events/", f"/api/events/{event.slug}/", "/api/membership/tiers/"):
        for viewer in (client, other_client, member_client):
            body = viewer.get(path).content.decode()
            assert "events_used" not in body and "counts_toward_plan" not in body
    assert MembershipUsage not in admin.site._registry


# Content


def write_tiers(folder, tiers):
    (folder / "membership.yaml").write_text(
        yaml.safe_dump(
            {
                "status": "draft - needs club approval",
                "source_url": ["https://old.example/membership"],
                "tiers": tiers,
            }
        )
    )


def load(folder):
    call_command("load_site_content", "--dir", str(folder), "--commit", stdout=StringIO())


def test_content_loads_tier_rules_by_slug(tmp_path):
    write_tiers(
        tmp_path,
        [
            {
                "slug": "community",
                "name": "Community",
                "price_cents": 0,
                "interval": "month",
                "renews": True,
                "event_access": "tagged",
                "allowed_event_tags": ["community"],
                "perks": ["Education nights"],
                "grants_feed_access": False,
            },
            {
                "slug": "rose",
                "name": "Rose",
                "price_cents": 4000,
                "interval": "month",
                "renews": True,
                "guest_discount": True,
                "premium_discord": True,
                "is_featured": True,
                "events_per_month": None,
            },
        ],
    )
    load(tmp_path)
    community = Tier.objects.get(slug="community")
    assert community.is_free and community.renews and not community.grants_feed_access
    assert [tag.slug for tag in community.allowed_event_tags.all()] == ["community"]
    rose = Tier.objects.get(slug="rose")
    assert rose.is_featured and rose.guest_discount and rose.events_per_month is None


def test_content_refuses_unknown_event_tags(tmp_path):
    write_tiers(
        tmp_path,
        [
            {
                "slug": "x",
                "name": "X",
                "price_cents": 0,
                "interval": "month",
                "allowed_event_tags": ["nope"],
            }
        ],
    )
    with pytest.raises(CommandError, match="unknown event tags"):
        load(tmp_path)
    assert not Tier.objects.exists()


def test_the_seeded_event_tags_exist():
    assert set(EventTag.objects.values_list("slug", flat=True)) >= {"community", "first_friday"}
