from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.consent_images import consented_image
from apps.core.text import caption_to_html
from apps.core.validators import cta_url_validator

MIN_IMAGES = 1
MAX_IMAGES = 10


class PostQuerySet(models.QuerySet):
    def live(self, now=None):
        return self.filter(is_published=True, published_at__lte=now or timezone.now())


class Post(models.Model):
    """A staff-written public post: one to ten images and a caption."""

    slug = models.SlugField(max_length=120, unique=True)
    caption = models.TextField(
        help_text="Plain text. Line breaks are kept and https:// links become clickable."
    )
    published_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"is_staff": True},
        related_name="journal_posts",
        help_text="Only their display name is shown.",
    )
    event = models.ForeignKey(
        "events.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_posts",
        help_text="When set, the post shows an RSVP button for this event.",
    )
    cta_label = models.CharField(max_length=60, blank=True)
    cta_url = models.CharField(max_length=500, blank=True, validators=[cta_url_validator])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-pk"]

    def __str__(self):
        return self.slug

    @property
    def caption_html(self):
        return caption_to_html(self.caption)

    def clean(self):
        super().clean()
        if bool(self.cta_label) != bool(self.cta_url):
            raise ValidationError({"cta_url": "Give both a button label and a link, or neither."})

    def publish_errors(self):
        """Problems that block publishing. Used by admin and tests alike."""
        errors = []
        images = list(self.images.all()) if self.pk else []
        if not MIN_IMAGES <= len(images) <= MAX_IMAGES:
            errors.append(f"A post needs between {MIN_IMAGES} and {MAX_IMAGES} images.")
        for image in images:
            for message in image.consent_image_errors(published=True).values():
                errors.append(f"Image {image.sort_order + 1}: {message}")
        return errors


class PostImage(consented_image("image", upload_to="journal", required=True)):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self):
        return f"{self.post.slug} image {self.sort_order + 1}"

    def consent_publish_state(self):
        # Inline admin forms attach an unsaved parent, so read it directly.
        try:
            return bool(self.post.is_published)
        except Post.DoesNotExist:
            return False
