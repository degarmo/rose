from django.db.models import F
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from .models import Profile, User


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        Profile.objects.get_or_create(user=instance)


PRIVILEGE_FIELDS = ("is_staff", "is_superuser", "is_active")


@receiver(pre_save, sender=User)
def end_sessions_on_privilege_change(sender, instance, raw=False, **kwargs):
    """A change to staff, superuser or active status ends every existing session."""
    if raw or instance.pk is None:
        return
    before = User.objects.filter(pk=instance.pk).values(*PRIVILEGE_FIELDS).first()
    if before and any(before[field] != getattr(instance, field) for field in PRIVILEGE_FIELDS):
        instance.session_epoch += 1


@receiver(m2m_changed, sender=User.groups.through)
@receiver(m2m_changed, sender=User.user_permissions.through)
def end_sessions_on_permission_change(sender, instance, action, reverse, pk_set, **kwargs):
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if reverse:
        users = User.objects.filter(pk__in=pk_set or [])
    else:
        users = User.objects.filter(pk=instance.pk)
    users.update(session_epoch=F("session_epoch") + 1)
