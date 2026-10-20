import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.consent_images import consented_image
from apps.core.text import sanitize_rich_text


class SiteSettings(models.Model):
    """Singleton holding the editable site-wide details. Always pk=1."""

    tagline = models.CharField(max_length=200)
    hours_text = models.TextField(help_text="Shown on Plan Your Visit. Line breaks are kept.")
    address_text = models.TextField(help_text="Shown in the footer and on Contact.")
    directions_text = models.TextField(
        blank=True, help_text="Shown on Plan Your Visit. Transit, parking and entrance notes."
    )
    phone_text = models.CharField(
        max_length=40,
        blank=True,
        verbose_name="phone number",
        help_text="Public phone number, shown with the address on Plan Your Visit.",
    )
    contact_email = models.EmailField(help_text="Public address shown on the site.")
    quick_exit_url = models.URLField(
        blank=True,
        help_text="Where the Leave control sends people. Blank uses the build default.",
    )
    nonprofit_status_text = models.CharField(
        max_length=200,
        blank=True,
        help_text='Shown on the Donate page, e.g. "A volunteer-run 501(c)(3) nonprofit."',
    )
    check_payable_to = models.CharField(
        max_length=120, blank=True, help_text="Who checks are made out to (Donate page)."
    )
    mailing_address = models.TextField(
        blank=True, help_text="Where to mail checks (Donate page). Line breaks are kept."
    )
    legal_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="The organisation's legal name. Staff only: used on donation "
        "acknowledgements, never shown on the site or in an email subject.",
    )
    ein = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="EIN",
        help_text="Employer identification number, for donation acknowledgements only.",
    )
    # Changed only through apps.memberships.age.set_age_check_required: Admin role, a
    # reason and a fresh two-step code, and every change is in the audit log.
    require_age_verification_for_feed = models.BooleanField(
        default=True,
        editable=False,
        verbose_name="age verification for the member feed",
        help_text="On: the member feed opens only after an in-person ID check at the door desk.",
    )
    age_verification_switched_on_at = models.DateTimeField(null=True, blank=True, editable=False)
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
    slug = models.SlugField(
        max_length=80,
        unique=True,
        null=True,
        blank=True,
        help_text="Used by load_site_content to update this question in place.",
    )
    question = models.CharField(max_length=255)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "FAQ item"

    def __str__(self):
        return self.question


class StaffProfile(consented_image("photo", upload_to="staff")):
    """A volunteer shown on Our Staff. Not an account: never shows an email.

    Linking to an account is optional and only for the volunteer's own record;
    nothing about the account is ever shown.
    """

    slug = models.SlugField(max_length=80, unique=True)
    display_name = models.CharField(max_length=60)
    role_title = models.CharField(max_length=80)
    bio = models.TextField(max_length=600, blank=True, help_text="A few sentences.")
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_profile",
        help_text="Optional. Only if the volunteer asks for it; never shown on the site.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "display_name"]

    def __str__(self):
        return self.display_name


class PageContent(models.Model):
    """One editable piece of copy on a page, so staff can change words without a deploy.

    Keys group with dots: "hero.title", "steps.1.body". Rich values are
    sanitised to the same small set of tags as event bodies.
    """

    class Format(models.TextChoices):
        PLAIN = "plain", "Plain text"
        RICH = "rich", "Formatted (paragraphs, lists, bold, links)"

    page = models.SlugField(max_length=60, db_index=True)
    key = models.CharField(max_length=120)
    value = models.TextField(blank=True)
    format = models.CharField(max_length=5, choices=Format.choices, default=Format.PLAIN)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["page", "key"]
        verbose_name = "page copy"
        verbose_name_plural = "page copy"
        constraints = [
            models.UniqueConstraint(fields=["page", "key"], name="one_value_per_page_key")
        ]

    def __str__(self):
        return f"{self.page}: {self.key}"

    def save(self, *args, **kwargs):
        if self.format == self.Format.RICH:
            self.value = sanitize_rich_text(self.value)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if not re.fullmatch(r"[a-z0-9_]+(\.[a-z0-9_]+)*", self.key or ""):
            raise ValidationError(
                {"key": "Use lowercase words, digits and underscores, joined by dots."}
            )


def normalise_path(path):
    """Lowercase, no query or trailing slash: /Our-Staff/ and /our-staff match."""
    path = "/" + path.strip().lstrip("/")
    path = path.split("?")[0].split("#")[0]
    if len(path) > 1:
        path = path.rstrip("/")
    return path.lower()


class Redirect(models.Model):
    """An address from the old site and where it lives now. Served as a 301."""

    old_path = models.CharField(
        max_length=300,
        unique=True,
        help_text='A path from the old site. End it with "/*" to cover everything under it.',
    )
    new_path = models.CharField(max_length=300, help_text="A path on this site, starting with /.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["old_path"]

    def __str__(self):
        return f"{self.old_path} -> {self.new_path}"

    def save(self, *args, **kwargs):
        self.old_path = normalise_path(self.old_path)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if not self.new_path.startswith("/") or self.new_path.startswith("//"):
            raise ValidationError({"new_path": "Use a path on this site, starting with /."})
