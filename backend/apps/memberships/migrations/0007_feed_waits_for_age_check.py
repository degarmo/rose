"""The member feed now needs an in-person age check, for everyone (decision 455).

From here on the code closes the feed to anyone without a valid ID check, so this
migration changes no access itself. It finds the accounts that had feed access and no
check, stamps Profile.age_check_notice_at (Home and Settings then show why the feed is
closed and what to bring), and the email goes out once from
apps.memberships.tasks.send_age_check_notices. Grants and opt-ins are kept, so the feed
reopens the moment staff record the check. The count is printed.
"""

from django.db import migrations
from django.db.models import Q
from django.utils import timezone

ENTITLED = ("active", "grace")


def stamp(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Profile = apps.get_model("accounts", "Profile")
    IdCheck = apps.get_model("memberships", "IdCheck")
    Membership = apps.get_model("memberships", "Membership")

    feed_members = Membership.objects.filter(
        status__in=ENTITLED, tier__grants_feed_access=True
    ).values("user_id")
    verified = IdCheck.objects.filter(verified_18_plus=True, revoked_at__isnull=True).values(
        "user_id"
    )
    waiting = (
        User.objects.filter(is_active=True)
        .filter(
            Q(is_superuser=True)
            | Q(is_staff=True)
            | Q(profile__feed_access_granted=True)
            | Q(pk__in=feed_members)
        )
        .exclude(pk__in=verified)
        .distinct()
    )
    count = Profile.objects.filter(
        user__in=waiting, age_check_notice_at__isnull=True
    ).update(age_check_notice_at=timezone.now())
    print(f"\n  The member feed now waits for an ID check for {count} account(s).")


def unstamp(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    Profile.objects.update(age_check_notice_at=None, age_check_emailed_at=None)


class Migration(migrations.Migration):
    dependencies = [
        ("memberships", "0006_idcheck_user_required"),
        ("accounts", "0009_profile_age_check_notice"),
    ]

    operations = [migrations.RunPython(stamp, unstamp)]
