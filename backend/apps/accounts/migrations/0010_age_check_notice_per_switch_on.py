"""The age check notice now records which switch-on of the setting a person was told about.

The stamps left by the first version of memberships migration 0007 meant something else
(that the feed had closed), so they are cleared; nobody had been emailed about them.
"""

from django.db import migrations


def clear(apps, schema_editor):
    apps.get_model("accounts", "Profile").objects.update(age_check_notice_at=None)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_profile_age_check_notice"),
        ("memberships", "0007_feed_waits_for_age_check"),
    ]

    operations = [
        migrations.RemoveField(model_name="profile", name="age_check_emailed_at"),
        migrations.RunPython(clear, migrations.RunPython.noop),
    ]
