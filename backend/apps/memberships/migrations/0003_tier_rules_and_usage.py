import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def derive(apps, schema_editor):
    """Existing tiers: free from the price; monthly and yearly tiers renew."""
    Tier = apps.get_model("memberships", "Tier")
    Tier.objects.filter(price_cents=0).update(is_free=True)
    Tier.objects.filter(interval__in=["month", "year"]).update(renews=True)


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0004_event_tags_and_guest_allowance"),
        ("memberships", "0002_tier_is_guest_pass"),
    ]

    operations = [
        migrations.RenameField(model_name="tier", old_name="benefits", new_name="perks"),
        migrations.AlterField(
            model_name="tier",
            name="perks",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Short lines, e.g. ["Weekend socials", "Members-only classes"].',
            ),
        ),
        migrations.AlterField(
            model_name="tier",
            name="description",
            field=models.TextField(blank=True, help_text="One line, shown under the price."),
        ),
        migrations.AlterModelOptions(name="tier", options={"ordering": ["price_cents", "sort_order"]}),
        migrations.AddField(
            model_name="tier",
            name="is_free",
            field=models.BooleanField(default=False, editable=False, help_text="Set from the price."),
        ),
        migrations.AddField(
            model_name="tier",
            name="renews",
            field=models.BooleanField(
                default=False,
                help_text="Runs month after month (or year after year) until cancelled. A free tier that renews simply stays open.",
            ),
        ),
        migrations.AddField(
            model_name="tier",
            name="events_per_month",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Members-only events per calendar month. Blank for unlimited.",
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AddField(
            model_name="tier",
            name="guests_included_per_event",
            field=models.PositiveSmallIntegerField(
                default=0, help_text="Guests who come free with the member to a members-only event."
            ),
        ),
        migrations.AddField(
            model_name="tier",
            name="guest_discount",
            field=models.BooleanField(
                default=False, help_text="Guests beyond those included pay the discounted guest price."
            ),
        ),
        migrations.AddField(
            model_name="tier",
            name="premium_discord",
            field=models.BooleanField(default=False, help_text="Includes the premium Discord channels."),
        ),
        migrations.AddField(
            model_name="tier",
            name="event_access",
            field=models.CharField(
                choices=[
                    ("all", "All members-only events"),
                    ("tagged", "Only events with one of the tags below"),
                ],
                default="all",
                max_length=6,
            ),
        ),
        migrations.AddField(
            model_name="tier",
            name="allowed_event_tags",
            field=models.ManyToManyField(
                blank=True,
                help_text="With tagged access: members-only events carrying any of these tags.",
                related_name="tiers",
                to="events.eventtag",
            ),
        ),
        migrations.AddField(
            model_name="tier",
            name="is_featured",
            field=models.BooleanField(
                default=False, help_text='Highlighted on the membership page as "Most popular".'
            ),
        ),
        migrations.AlterField(
            model_name="membership",
            name="paid_awaiting_id_check",
            field=models.BooleanField(
                default=False,
                help_text="Nothing left to pay (paid online, or a free tier); becomes active once staff check a photo ID.",
            ),
        ),
        migrations.CreateModel(
            name="MembershipUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.DateField(help_text="The first day of the month, Chicago time.")),
                ("events_used", models.PositiveIntegerField(default=0)),
                (
                    "membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usage",
                        to="memberships.membership",
                    ),
                ),
            ],
            options={
                "ordering": ["-month"],
                "constraints": [
                    models.UniqueConstraint(fields=("membership", "month"), name="one_usage_row_per_month")
                ],
            },
        ),
        migrations.RunPython(derive, migrations.RunPython.noop),
    ]
