"""Each ID check now belongs to the person; until now it hung off a membership."""

from django.db import migrations


def backfill(apps, schema_editor):
    IdCheck = apps.get_model("memberships", "IdCheck")
    for check in IdCheck.objects.select_related("membership").filter(user__isnull=True):
        owner = check.membership.user_id if check.membership_id else None
        if owner is None:
            # A deleted account's check verifies nobody.
            check.delete()
            continue
        check.user_id = owner
        check.save(update_fields=["user"])


class Migration(migrations.Migration):
    dependencies = [("memberships", "0004_idcheck_person_witness_revoke")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
