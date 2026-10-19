from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit entries cannot be changed.")

    def delete(self):
        raise ValidationError("Audit entries cannot be deleted.")


class AuditLog(models.Model):
    """Append-only record of sensitive staff actions: moderation, the door desk,
    exports and anything that reveals private data. Never edited or deleted.
    """

    class Category(models.TextChoices):
        MODERATION = "moderation", "Feed moderation"
        DOOR_DESK = "door_desk", "Door desk"
        EXPORT = "export", "Data export"
        PRIVATE_DATA = "private_data", "Private data viewed"
        SECURITY = "security", "Staff security"
        OPERATIONS = "operations", "Operations"
        RENTALS = "rentals", "Rentals"
        DONATIONS = "donations", "Donations"
        VOLUNTEERS = "volunteers", "Volunteers"
        NEWSLETTER = "newsletter", "Email list"
        CONTENT = "content", "Site content"

    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    action = models.CharField(max_length=40)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    actor_label = models.CharField(max_length=30)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    target_label = models.CharField(max_length=120)
    target_type = models.CharField(max_length=20)
    target_ref = models.CharField(max_length=32, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "audit entry"
        verbose_name_plural = "audit log"

    def __str__(self):
        label = self.get_category_display()
        return f"{label}: {self.action} {self.target_label} by {self.actor_label}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Audit entries cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit entries cannot be deleted.")


def audit(
    category, action, actor, target_label, target_type, target_user=None, target_ref="", reason=""
):
    """Write one audit entry. `actor` may be None for system actions."""
    return AuditLog.objects.create(
        category=category,
        action=action,
        actor=actor,
        actor_label=(actor.display_name if actor else "system")[:30],
        target_user=target_user,
        target_label=target_label[:120],
        target_type=target_type,
        target_ref=(target_ref or "")[:32],
        reason=reason,
    )


class SeedMarker(models.Model):
    """Written by seed_demo. Its presence stops staging and production from starting."""

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "demo seed marker"

    def __str__(self):
        return f"Demo data loaded {self.created_at:%Y-%m-%d}"
