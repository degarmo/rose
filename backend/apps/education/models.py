from django.db import models

from apps.core.consent_images import consented_image
from apps.core.validators import cta_url_validator


class OpportunityQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Opportunity(consented_image("hero_image", upload_to="education")):
    class Category(models.TextChoices):
        CLASS = "class", "Class"
        WORKSHOP = "workshop", "Workshop"
        MENTORSHIP = "mentorship", "Mentorship"
        VOLUNTEER = "volunteer", "Volunteer"
        OTHER = "other", "Other"

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        ALL = "all", "All levels"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    summary = models.CharField(max_length=300)
    body = models.TextField(help_text="Plain text. Blank lines separate paragraphs.")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.CLASS)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.ALL)
    starts_at = models.DateTimeField(null=True, blank=True)
    location_label = models.CharField(max_length=120, blank=True)
    cta_label = models.CharField(max_length=60, blank=True)
    cta_url = models.CharField(
        max_length=500,
        blank=True,
        validators=[cta_url_validator],
        help_text="A site path such as /contact or a full https:// address.",
    )
    is_published = models.BooleanField(default=False)
    members_only = models.BooleanField(
        default=False,
        help_text="Title, summary and image stay public; the details and sign-up are for members.",
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OpportunityQuerySet.as_manager()

    class Meta:
        ordering = ["sort_order", "starts_at", "title"]
        verbose_name_plural = "opportunities"

    def __str__(self):
        return self.title
