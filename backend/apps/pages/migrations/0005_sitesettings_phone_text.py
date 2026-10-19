from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0004_membership_is_a_page"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="phone_text",
            field=models.CharField(
                blank=True,
                help_text="Public phone number, shown with the address on Plan Your Visit.",
                max_length=40,
                verbose_name="phone number",
            ),
        ),
    ]
