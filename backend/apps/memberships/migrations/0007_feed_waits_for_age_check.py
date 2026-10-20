"""How many people the feed's age check would close it to (decisions 455 and 467).

The check is a site setting, evaluated live on every request, so this migration changes
nothing. It counts the active accounts with feed access and no valid ID check, and prints
the number, so the club knows the effect before the setting is on in production.
"""

from django.db import migrations
from django.db.models import Q

ENTITLED = ("active", "grace")


def count(apps, schema_editor):
    User = apps.get_model("accounts", "User")
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
        .count()
    )
    print(
        f"\n  {waiting} account(s) with feed access have no ID check: with age verification "
        "on, the member feed waits for one."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("memberships", "0006_idcheck_user_required"),
        ("accounts", "0009_profile_age_check_notice"),
    ]

    operations = [migrations.RunPython(count, migrations.RunPython.noop)]
