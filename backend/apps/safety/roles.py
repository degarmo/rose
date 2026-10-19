"""Team roles, stored as Django groups.

- Moderator: reports and member actions.
- Staff: everything a moderator does, plus the metrics.
- Admin: everything, plus managing the team and revealing who sent a report.

A superuser counts as an admin. Every role also needs the staff two-step login
(django-otp) on the current session before the staff section answers at all.
"""

from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Q

MODERATOR = "moderator"
STAFF = "staff"
ADMIN = "admin"
ROLES = (MODERATOR, STAFF, ADMIN)
GROUP_NAMES = {MODERATOR: "Moderator", STAFF: "Staff", ADMIN: "Admin"}
LABELS = GROUP_NAMES
RANK = {None: 0, MODERATOR: 1, STAFF: 2, ADMIN: 3}


def role_of(user):
    """The highest team role this person holds, or None."""
    if not (user and user.is_authenticated and user.is_active and user.is_staff):
        return None
    if user.is_superuser:
        return ADMIN
    held = set(user.groups.values_list("name", flat=True))
    for role in (ADMIN, STAFF, MODERATOR):
        if GROUP_NAMES[role] in held:
            return role
    return None


def has_role(user, minimum):
    return RANK[role_of(user)] >= RANK[minimum]


def dev_skip_two_step():
    """DEV_SKIP_STAFF_2FA, honoured only in local development (DEBUG on, not deployed)."""
    return bool(
        settings.DEV_SKIP_STAFF_2FA
        and settings.DEBUG
        and settings.DJANGO_ENV not in settings.DEPLOYED_ENVS
    )


def is_verified(user):
    """Whether this session passed the staff two-step login."""
    if dev_skip_two_step() and role_of(user) is not None:
        return True
    return bool(getattr(user, "is_verified", lambda: False)())


def can_use_staff_section(user, minimum=MODERATOR):
    return has_role(user, minimum) and is_verified(user)


def team_members(minimum=MODERATOR):
    """Everyone holding at least `minimum`, superusers included."""
    from apps.accounts.models import User

    names = [GROUP_NAMES[role] for role in ROLES if RANK[role] >= RANK[minimum]]
    return (
        User.objects.filter(is_active=True, is_staff=True)
        .filter(Q(is_superuser=True) | Q(groups__name__in=names))
        .distinct()
        .order_by("display_name")
    )


def set_role(user, role):
    """Give someone exactly one team role (or none). A role needs the staff flag, for the
    two-step login; taking the last role away clears it unless other groups need it."""
    team_groups = Group.objects.filter(name__in=GROUP_NAMES.values())
    user.groups.remove(*team_groups)
    if role is not None:
        group, _ = Group.objects.get_or_create(name=GROUP_NAMES[role])
        user.groups.add(group)
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])
    elif user.is_staff and not user.is_superuser and not user.groups.exists():
        if not user.user_permissions.exists():
            user.is_staff = False
            user.save(update_fields=["is_staff"])
