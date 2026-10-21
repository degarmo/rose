import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction

from apps.core.consent_images import PUBLIC_VARIANT_WIDTHS, consented_image
from apps.core.images import variant_name
from apps.core.text import sanitize_rich_text


class SiteSettings(models.Model):
    """Singleton holding the editable site-wide details. Always pk=1."""

    site_display_name = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="club name",
        help_text="Shown on the website, in the member app and in the admin. Never in "
        "email, receipts, calendar files or the authenticator app, which stay neutral. "
        "Blank uses the SITE_DISPLAY_NAME setting.",
    )
    site_short_name = models.CharField(
        max_length=60,
        blank=True,
        verbose_name="short club name",
        help_text="For tight spots: the phone header and the member sidebar. Blank uses "
        "the club name above, or the SITE_SHORT_NAME setting.",
    )
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
    value = models.TextField(
        blank=True,
        help_text="Write {display_name} (or {short_name}) for the club's name; it follows "
        "Site settings.",
    )
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


class SiteImage(consented_image("image", upload_to="site-images")):
    """One fixed picture on a public page (a slot), changed in Admin > Content > Page images.

    The site asks for it by `slot` ("home.hero"); docs/page-images.md lists every slot.
    An empty slot, or one whose picture shows faces without confirmed consent, shows the
    page's texture instead. Replacing, removing or restoring keeps the previous pictures
    as versions (`SiteImageVersion`), the newest few only.
    """

    class Page(models.TextChoices):
        HOME = "home", "Home"
        ABOUT = "about", "About"
        VISIT = "visit", "Plan your visit"
        GUESTS = "guests", "Guests"
        RENTALS = "rentals", "Rentals"
        VOLUNTEER = "volunteer", "Volunteer"
        DONATE = "donate", "Donate"

    page = models.CharField(max_length=20, choices=Page.choices)
    slot = models.CharField(max_length=60, unique=True, help_text="The key the site asks for.")
    label = models.CharField(max_length=80, help_text="What staff see, e.g. Home: top banner.")
    help_text = models.CharField(
        max_length=240, blank=True, help_text="The recommended size and shape."
    )
    aspect_ratio = models.CharField(max_length=10, help_text="Width/height on computers, e.g. 3/2.")
    phone_aspect_ratio = models.CharField(
        max_length=10, blank=True, help_text="Width/height on phones. Blank: phones do not show it."
    )
    recommended_width = models.PositiveIntegerField(
        default=1600, help_text="Smaller pictures are accepted with a warning."
    )
    credit = models.CharField(
        max_length=300, blank=True, help_text="Where the picture came from, and its licence."
    )
    focal_x = models.FloatField(
        default=0.5, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    focal_y = models.FloatField(
        default=0.5, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    PATHS = {
        Page.HOME: "/",
        Page.ABOUT: "/about",
        Page.VISIT: "/visit",
        Page.GUESTS: "/guests",
        Page.RENTALS: "/rentals",
        Page.VOLUNTEER: "/get-involved/volunteer",
        Page.DONATE: "/get-involved/donate",
    }
    KEEP_VERSIONS = 5

    class Meta:
        ordering = ["sort_order", "slot"]
        constraints = [
            models.UniqueConstraint(fields=["page", "slot"], name="pages_siteimage_page_slot")
        ]
        verbose_name = "page image"

    def __str__(self):
        return self.label

    def consent_publish_state(self):
        """A slot is always on a public page."""
        return True

    @property
    def is_shown(self):
        """Whether the site shows this picture (set, and cleared for consent)."""
        return self.image_is_displayable("image")

    def get_absolute_url(self):
        from apps.core.email import site_link

        return site_link(self.PATHS[self.page])

    def save(self, *args, **kwargs):
        previous = SiteImage.objects.filter(pk=self.pk).first() if self.pk else None
        super().save(*args, **kwargs)
        if previous and previous.image and previous.image.name != self.image.name:
            SiteImageVersion.keep(previous, replaced_by=self.updated_by)
            self.purge_versions()

    def restore(self, version, actor):
        """Put a previous picture back. The one showing now becomes a version itself."""
        self.image.name = version.image.name
        for field in VERSIONED_FIELDS:
            setattr(self, field, getattr(version, field))
        self.updated_by = actor
        with transaction.atomic():
            version.delete()
            self.save()

    def purge_versions(self):
        """Keep the newest KEEP_VERSIONS; delete the rest and their files."""
        for version in self.versions.all()[self.KEEP_VERSIONS :]:
            name = version.image.name
            version.delete()
            # Slots can share a file (the migration seeds some), so check every row.
            in_use = (
                SiteImage.objects.filter(image=name).exists()
                or SiteImageVersion.objects.filter(image=name).exists()
            )
            if name and not in_use:
                delete_with_variants(version.image.storage, name)


VERSIONED_FIELDS = (
    "image_width",
    "image_height",
    "image_alt",
    "image_faces_visible",
    "image_consent_confirmed",
    "credit",
    "focal_x",
    "focal_y",
)


def delete_with_variants(storage, name):
    for path in (name, *(variant_name(name, width) for width in PUBLIC_VARIANT_WIDTHS)):
        if storage.exists(path):
            storage.delete(path)


class SiteImageVersion(models.Model):
    """A picture a slot showed before, kept so staff can restore it."""

    site_image = models.ForeignKey(SiteImage, on_delete=models.CASCADE, related_name="versions")
    image = models.ImageField(max_length=200, editable=False)
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)
    image_alt = models.CharField(max_length=200, blank=True)
    image_faces_visible = models.BooleanField(default=False)
    image_consent_confirmed = models.BooleanField(default=False)
    credit = models.CharField(max_length=300, blank=True)
    focal_x = models.FloatField(default=0.5)
    focal_y = models.FloatField(default=0.5)
    replaced_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.site_image}: {self.created_at:%Y-%m-%d %H:%M}"

    @classmethod
    def keep(cls, site_image, replaced_by=None):
        values = {field: getattr(site_image, field) for field in VERSIONED_FIELDS}
        return cls.objects.create(
            site_image=site_image, image=site_image.image.name, replaced_by=replaced_by, **values
        )
