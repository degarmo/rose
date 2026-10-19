from django.db import migrations


def drop_membership_redirect(apps, schema_editor):
    """/membership is a page of its own now; an old redirect there would hide it."""
    Redirect = apps.get_model("pages", "Redirect")
    Redirect.objects.filter(old_path="/membership").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0003_site_content"),
    ]

    operations = [
        migrations.RunPython(drop_membership_redirect, migrations.RunPython.noop),
    ]
