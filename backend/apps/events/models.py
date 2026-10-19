from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from apps.core.consent_images import consented_image
from apps.core.text import sanitize_rich_text

MAX_PARTY_SIZE = 2
# Slugs that would collide with fixed routes under /events/.
RESERVED_SLUGS = frozenset({"calendar", "rsvp", "cancel"})


class EventQuerySet(models.QuerySet):
    def published(self):
        # A private hold (a confirmed rental's placeholder) is never public.
        return self.filter(is_published=True, is_private_hold=False)

    def visible_to(self, user):
        """Published events this person may see. Account-only events need a sign-in."""
        events = self.published()
        if not (user and user.is_authenticated):
            events = events.exclude(audience=Event.Audience.ACCOUNT)
        return events

    def upcoming(self, now=None):
        return self.filter(ends_at__gte=now or timezone.now())

    def with_going_total(self):
        return self.annotate(
            going_total=models.functions.Coalesce(
                Sum("rsvps__party_size", filter=Q(rsvps__status=RSVP.Status.GOING)), 0
            )
        )


class Event(consented_image("hero_image", upload_to="events")):
    class Category(models.TextChoices):
        EDUCATION = "education", "Education night"
        SOCIAL = "social", "Social"
        WORKSHOP = "workshop", "Workshop"
        MEMBER_NIGHT = "member_night", "Member night"
        SPECIAL = "special", "Special"

    class Audience(models.TextChoices):
        PUBLIC = "public", "Everyone (RSVP with a verified account)"
        ACCOUNT = "account", "Signed-in accounts only (hidden from visitors)"
        MEMBERS = "members", "Members only"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.CharField(max_length=300)
    body = models.TextField(
        blank=True,
        help_text="Basic formatting only: paragraphs, bold, italics, lists, links. "
        "Anything else is removed on save.",
    )
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.SOCIAL)
    starts_at = models.DateTimeField(help_text="Chicago time.")
    ends_at = models.DateTimeField(help_text="Chicago time.")
    location_label = models.CharField(max_length=120, blank=True)
    is_published = models.BooleanField(default=False)
    audience = models.CharField(max_length=10, choices=Audience.choices, default=Audience.PUBLIC)

    capacity = models.PositiveIntegerField(
        null=True, blank=True, help_text="Total people, counting guests. Blank means unlimited."
    )
    waitlist_enabled = models.BooleanField(default=True)
    max_party_size = models.PositiveSmallIntegerField(
        default=MAX_PARTY_SIZE,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_PARTY_SIZE)],
        help_text="1 for just themselves, 2 to allow one guest.",
    )
    rsvp_opens_at = models.DateTimeField(null=True, blank=True, help_text="Blank opens now.")
    rsvp_closes_at = models.DateTimeField(
        null=True, blank=True, help_text="Blank closes when the event starts."
    )
    show_attendee_count = models.BooleanField(
        default=False, help_text="Show how many people are going. Names are never shown."
    )
    opportunity = models.ForeignKey(
        "education.Opportunity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )

    is_private_hold = models.BooleanField(
        default=False,
        editable=False,
        help_text="A confirmed rental's placeholder, so the date is not double-booked. "
        "Never published or shown on the site.",
    )

    final_going_count = models.PositiveIntegerField(null=True, blank=True, editable=False)
    final_checked_in_count = models.PositiveIntegerField(null=True, blank=True, editable=False)
    rsvps_purged_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventQuerySet.as_manager()

    class Meta:
        ordering = ["starts_at", "title"]

    def __str__(self):
        local = timezone.localtime(self.starts_at)
        return f"{self.title} ({local:%a %b} {local.day})"

    def save(self, *args, **kwargs):
        self.body = sanitize_rich_text(self.body)
        if self.is_private_hold:
            self.is_published = False
        super().save(*args, **kwargs)

    def clean(self):
        errors = {}
        try:
            super().clean()
        except ValidationError as exc:
            errors.update(exc.message_dict)
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            errors["ends_at"] = "The end must be after the start."
        if self.rsvp_opens_at and self.rsvp_closes_at and self.rsvp_closes_at <= self.rsvp_opens_at:
            errors["rsvp_closes_at"] = "RSVPs must close after they open."
        if self.rsvp_closes_at and self.ends_at and self.rsvp_closes_at > self.ends_at:
            errors["rsvp_closes_at"] = "RSVPs cannot close after the event ends."
        if self.slug in RESERVED_SLUGS:
            errors["slug"] = "That address is reserved. Please choose another."
        if self.capacity == 0:
            errors["capacity"] = "Use a number above zero, or leave blank for unlimited."
        if self.is_private_hold and self.is_published:
            errors["is_published"] = "A private rental hold is never published."
        if errors:
            raise ValidationError(errors)

    @property
    def rsvp_deadline(self):
        return self.rsvp_closes_at or self.starts_at

    def going_count(self):
        total = getattr(self, "going_total", None)
        if total is not None:
            return total
        return (
            self.rsvps.filter(status=RSVP.Status.GOING).aggregate(total=Sum("party_size"))["total"]
            or 0
        )

    def is_full(self):
        return self.capacity is not None and self.going_count() >= self.capacity


class RSVP(models.Model):
    class Status(models.TextChoices):
        GOING = "going", "Going"
        WAITLIST = "waitlist", "Waitlist"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="rsvps")
    status = models.CharField(max_length=10, choices=Status.choices)
    party_size = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(MAX_PARTY_SIZE)]
    )
    note_to_hosts = models.CharField(max_length=280, blank=True)
    checked_in = models.BooleanField(default=False)
    waitlisted_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "RSVP"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="one_rsvp_per_person_per_event")
        ]
        permissions = [("export_attendees", "Can export door lists")]

    def __str__(self):
        return f"{self.user.display_name} for {self.event.title}"


class AttendeeExport(models.Model):
    """Audit log: who downloaded a door list, and when. Holds no attendee data."""

    event = models.ForeignKey(Event, null=True, on_delete=models.SET_NULL, related_name="+")
    event_label = models.CharField(max_length=260)
    exported_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    exported_by_label = models.CharField(max_length=30)
    exported_at = models.DateTimeField(auto_now_add=True)
    row_count = models.PositiveIntegerField()

    class Meta:
        ordering = ["-exported_at"]

    def __str__(self):
        return f"{self.event_label} exported by {self.exported_by_label}"
