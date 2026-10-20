"""Development-only team accounts and casework, so every staff screen has content.
seed_demo calls this only when DEBUG is on."""

from django.utils import timezone

from apps.accounts.models import User
from apps.events.models import Event
from apps.feed import services as feed_services
from apps.feed.models import Guidelines, Report
from apps.memberships.age import seed_check

from . import roles, services
from .models import MemberAction

TEAM = [
    ("team.moderator@example.org", "team_moderator", roles.MODERATOR),
    ("team.staff@example.org", "team_staff", roles.STAFF),
    ("team.admin@example.org", "team_admin", roles.ADMIN),
]


def seed_team(password):
    """Returns [(label, email)]. Each is staff, holds a role and has joined the member app."""
    guidelines = Guidelines.current()
    accounts = []
    for email, display_name, role in TEAM:
        user = User.objects.filter(email=email).first()
        if user is None:
            user = User.objects.create_user(email=email, display_name=display_name)
        user.set_password(password)
        user.save()
        user.mark_email_verified()
        roles.set_role(user, role)
        seed_check(user)
        if guidelines is not None and not user.profile.participates_in_feed:
            feed_services.join_feed(user, guidelines.version)
        accounts.append((f"team: {roles.LABELS[role]}", email))
    return accounts


def seed_safety():
    """A concern from a member, one from the website, and a warning with an open appeal."""
    already = MemberAction.objects.filter(rule="Community guidelines", reason__startswith="Demo:")
    if already.exists():
        return
    moderator = User.objects.get(email="team.moderator@example.org")
    member = User.objects.filter(display_name="demo_member").first()
    warned = User.objects.filter(display_name="low_tide").first()
    event = Event.objects.filter(slug="member-night").first()
    if member is not None:
        services.file_concern(
            member,
            "Someone kept standing too close at the bar after I asked them to give me space.",
            event=event,
            event_date=timezone.localdate(event.starts_at) if event else None,
            reported_name="brass_key",
        )
    services.file_concern(
        None,
        "I visited as a guest and want to tell someone about how a conversation went.",
        contact_email="visitor@example.org",
    )
    if warned is not None:
        action = services.take_action(
            moderator,
            warned,
            services.ActionInput(
                kind=MemberAction.Kind.WARNING,
                rule="Community guidelines",
                reason="Demo: several posts were off topic after a reminder.",
            ),
        )
        services.submit_appeal(
            warned, action, "I did not see the reminder. I will keep posts on topic."
        )
    spam = Report.objects.filter(reason=Report.Reason.SPAM, status=Report.Status.OPEN).first()
    if spam is not None:
        services.assign(moderator, spam, moderator)
