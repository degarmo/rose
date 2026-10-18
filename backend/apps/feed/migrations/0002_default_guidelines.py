from django.db import migrations
from django.utils import timezone

DEFAULT_BODY = """The member feed is a private space for people who chose to be here. These guidelines keep it safe for everyone in it.

Consent comes first
- Only post someone if they agreed, clearly and in advance, to that photo being posted here.
- Never show another person's face without their approval. When in doubt, crop it out or use the redaction tool.
- Anyone can change their mind. If someone asks you to take a post down, take it down.

Protect identities
- No identifying details: workplaces, uniforms, license plates, street signs, house numbers, or tattoos and marks that could identify someone.
- Never use anyone's real name, including your own, unless it is their display name here.

What happens here stays here
- No screenshots, downloads, screen recordings or resharing anything from the feed anywhere else.
- Images carry a faint mark naming the account that viewed them, so leaks can be traced.

Be respectful
- Be kind, curious and generous. No harassment, pressure, shaming or unsolicited advances.
- Respect a no, a block or silence.

Reporting
- If something feels wrong, report it from the post, comment or profile menu. Reports are private and reviewed by our team.
- Content reported as posted without consent, or as possibly involving someone under 18, is hidden straight away while we look.

Breaking these guidelines can lead to removal of posts, a pause on posting, suspension or losing access to the feed."""


def create_default(apps, schema_editor):
    Guidelines = apps.get_model("feed", "Guidelines")
    if not Guidelines.objects.exists():
        Guidelines.objects.create(
            version=1,
            title="Community guidelines",
            body=DEFAULT_BODY,
            published_at=timezone.now(),
        )


def remove_default(apps, schema_editor):
    Guidelines = apps.get_model("feed", "Guidelines")
    Guidelines.objects.filter(version=1, body=DEFAULT_BODY).delete()


class Migration(migrations.Migration):
    dependencies = [("feed", "0001_initial")]

    operations = [migrations.RunPython(create_default, remove_default)]
