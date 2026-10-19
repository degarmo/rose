"""Inquiries to rent the space. No account is needed to send one.

Contact details live here only while staff need them: declined and cancelled
inquiries keep just their type, date and status after RENTAL_RETENTION_DAYS
(see tasks.purge_closed_inquiries).
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

MAX_DURATION_HOURS = 12
MAX_PARTY_SIZE = 200


class RentalInquiry(models.Model):
    class Type(models.TextChoices):
        PRIVATE_SESSION = "private_session", "Private session"
        WORKSHOP = "workshop", "Workshop or class"
        PHOTOSHOOT = "photoshoot", "Photoshoot"
        GROUP_EVENT = "group_event", "Group event"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_DISCUSSION = "in_discussion", "In discussion"
        QUOTED = "quoted", "Quoted"
        CONFIRMED = "confirmed", "Confirmed"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    CLOSED = (Status.DECLINED, Status.CANCELLED)
    # The order of the admin pipeline's columns.
    PIPELINE = (
        Status.NEW,
        Status.IN_DISCUSSION,
        Status.QUOTED,
        Status.CONFIRMED,
        Status.DECLINED,
        Status.CANCELLED,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rental_inquiries",
    )
    contact_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    type = models.CharField(max_length=20, choices=Type.choices)
    preferred_date = models.DateField()
    alternate_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True, help_text="Chicago time.")
    duration_hours = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_DURATION_HOURS)],
    )
    party_size = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_PARTY_SIZE)],
    )
    notes = models.TextField(blank=True)
    photoshoot_acknowledged = models.BooleanField(
        default=False,
        help_text="They confirmed everyone photographed will consent, and no other guests "
        "or members will appear in any image.",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    quoted_amount_cents = models.PositiveIntegerField(null=True, blank=True)
    staff_notes = models.TextField(blank=True, help_text="Staff only. Never shown or emailed.")
    hold = models.OneToOneField(
        "events.Event",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rental_inquiry",
        editable=False,
        help_text="The private calendar placeholder made when this was confirmed.",
    )
    closed_at = models.DateTimeField(null=True, blank=True, editable=False)
    contact_purged_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "rental inquiry"
        verbose_name_plural = "rental inquiries"

    def __str__(self):
        return f"{self.get_type_display()} on {self.preferred_date:%b} {self.preferred_date.day}"

    @property
    def label(self):
        """How staff and the audit log refer to it: never the contact's name."""
        return f"Rental inquiry #{self.pk}"

    def window(self, date=None):
        """The requested time as an aware (start, end) pair in Chicago time.

        Without a start time or duration the whole day counts, which is what a
        conflict check should assume.
        """
        date = date or self.preferred_date
        if self.start_time is None or not self.duration_hours:
            start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
            return start, start + timedelta(days=1)
        start = timezone.make_aware(datetime.combine(date, self.start_time))
        return start, start + timedelta(hours=self.duration_hours)
