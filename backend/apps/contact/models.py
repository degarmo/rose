from django.db import models
from django.utils import timezone

ANONYMIZED_NAME = "Deleted account"


class ContactMessage(models.Model):
    """A message from the contact form. No IP address or user agent is stored."""

    class Topic(models.TextChoices):
        GENERAL = "general", "General"
        MEMBERSHIP = "membership", "Membership"
        EVENTS = "events", "Events"
        VOLUNTEER = "volunteer", "Volunteer"
        CONCERN = "concern", "Report a concern"

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    topic = models.CharField(max_length=20, choices=Topic.choices, default=Topic.GENERAL)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)
    is_priority = models.BooleanField(
        default=False, editable=False, help_text="Set automatically for reported concerns."
    )
    anonymized_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text="Set when the sender deleted their account.",
    )

    class Meta:
        ordering = ["handled", "-is_priority", "-created_at"]

    def __str__(self):
        return f"{self.get_topic_display()} message #{self.pk}"

    def save(self, *args, **kwargs):
        self.is_priority = self.topic == self.Topic.CONCERN
        super().save(*args, **kwargs)


def anonymize_messages_from(email):
    """Strip identity from a sender's messages; the text stays for safety records."""
    return ContactMessage.objects.filter(email__iexact=email).update(
        name=ANONYMIZED_NAME, email="", phone="", anonymized_at=timezone.now()
    )
