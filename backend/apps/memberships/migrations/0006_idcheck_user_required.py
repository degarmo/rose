import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("memberships", "0005_idcheck_backfill_person")]

    operations = [
        migrations.AlterField(
            model_name="idcheck",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="id_checks",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
