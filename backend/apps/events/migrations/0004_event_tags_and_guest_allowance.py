import django.core.validators
from django.db import migrations, models

TAGS = [("community", "Community"), ("first_friday", "First Friday")]


def seed_tags(apps, schema_editor):
    EventTag = apps.get_model("events", "EventTag")
    for slug, name in TAGS:
        EventTag.objects.get_or_create(slug=slug, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0003_event_is_private_hold"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=60)),
                ("slug", models.SlugField(max_length=60, unique=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="event",
            name="access_tags",
            field=models.ManyToManyField(
                blank=True,
                help_text="Members-only events: memberships limited to tagged events can RSVP when one of these tags is on their membership.",
                related_name="events",
                to="events.eventtag",
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="guest_allowance",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Members-only events: guests a member may bring beyond what their membership includes. The party size above still caps the total.",
                validators=[django.core.validators.MaxValueValidator(1)],
            ),
        ),
        migrations.AddField(
            model_name="rsvp",
            name="counts_toward_plan",
            field=models.BooleanField(
                default=False,
                editable=False,
                help_text="This RSVP is counted in its member's monthly event allowance.",
            ),
        ),
        migrations.RunPython(seed_tags, migrations.RunPython.noop),
    ]
