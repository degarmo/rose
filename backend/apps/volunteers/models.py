"""People offering to help. Staff-only: no endpoint ever lists or returns a signup."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Interest(models.TextChoices):
    DOOR = "door", "Door and hosting"
    SETUP = "setup", "Setup and cleanup"
    TEACHING = "teaching", "Teaching"
    EVENTS = "events", "Events"
    OUTREACH = "outreach", "Social work outreach"
    MAINTENANCE = "maintenance", "Maintenance"
    ADMIN = "admin_web", "Admin and web"
    OTHER = "other", "Other"


class Availability(models.TextChoices):
    WEEKNIGHTS = "weeknights", "Weeknights"
    WEEKENDS = "weekends", "Weekends"
    DAYTIME = "daytime", "Daytime"
    ONE_OFF = "one_off", "One-off events"


class VolunteerSignup(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="volunteer_signups",
    )
    contact_name = models.CharField(
        max_length=120, help_text="Their display name, or the name they gave."
    )
    contact_email = models.EmailField()
    interests = models.JSONField(default=list, help_text="Keys from the interests list.")
    availability = models.JSONField(default=list, help_text="Keys from the availability list.")
    experience_note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "volunteer signup"

    def __str__(self):
        return f"Volunteer signup #{self.pk}"

    @property
    def interest_labels(self):
        return [Interest(key).label for key in self.interests if key in Interest.values]

    @property
    def availability_labels(self):
        return [Availability(key).label for key in self.availability if key in Availability.values]


def forget_account(user):
    """Account deletion: their offers to volunteer go with it."""
    return VolunteerSignup.objects.filter(user=user).delete()
