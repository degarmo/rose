from django.core.exceptions import ValidationError
from django.db import models


class SiteSettings(models.Model):
    """Singleton holding the editable site-wide details. Always pk=1."""

    tagline = models.CharField(max_length=200)
    hours_text = models.TextField(help_text="Shown on Plan Your Visit. Line breaks are kept.")
    address_text = models.TextField(help_text="Shown in the footer and on Contact.")
    directions_text = models.TextField(
        blank=True, help_text="Shown on Plan Your Visit. Transit, parking and entrance notes."
    )
    contact_email = models.EmailField(help_text="Public address shown on the site.")
    quick_exit_url = models.URLField(
        blank=True,
        help_text="Where the Leave control sends people. Blank uses the build default.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Site settings cannot be deleted.")

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "tagline": "",
                "hours_text": "",
                "address_text": "",
                "directions_text": "",
                "contact_email": "",
            },
        )
        return obj


class SocialLink(models.Model):
    """A plain outbound link. No embeds, widgets or share buttons."""

    settings = models.ForeignKey(
        SiteSettings, on_delete=models.CASCADE, related_name="social_links"
    )
    label = models.CharField(max_length=60)
    url = models.URLField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.label


class FAQItem(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "FAQ item"

    def __str__(self):
        return self.question
