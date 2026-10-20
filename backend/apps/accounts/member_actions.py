"""The actions staff take on accounts from the admin's Members page, one at a time or in
bulk, and the rules they all share.

Each action calls an existing service: moderation in apps.safety.services, the account in
apps.accounts.services. This module adds only what is common to running them from the
admin:

- the role each needs (Moderator, Staff or Admin; superusers count as admins)
- at most MAX_USERS accounts at once
- never on your own account, and never on a staff or superuser account for the actions
  marked `protected` (ban, suspensions, deactivation, erasure): those are skipped and
  listed
- a fresh code from the actor's authenticator app for those marked `fresh_code` (ban,
  unban, erase), checked once for the whole batch
- a summary of what was done and what was skipped, and why

There is no action for ID checks: they happen in person at the door desk only.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time

from django.utils import timezone

from apps.safety import roles
from apps.safety.models import MemberAction
from apps.safety.services import ActionInput, SafetyError, lift_suspensions, take_action, unban

from . import services
from .services import AccountActionError
from .two_step import fresh_code

MAX_USERS = 50
K = MemberAction.Kind


class ActionError(Exception):
    """The whole batch was refused; the message says why."""


@dataclass
class Summary:
    done: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass(frozen=True)
class Spec:
    key: str
    label: str
    role: str
    # What the confirmation page asks for (apps.accounts.admin_forms).
    fields: tuple[str, ...]
    run: Callable
    protected: bool = False
    fresh_code: bool = False
    danger: bool = False
    # Runs once for all the accounts (the export), not once per account.
    batch: bool = False


def _until(data):
    """A suspension's end: 7 or 30 days, or the end of a chosen day."""
    if data["length"] == "custom":
        day = data["until"]
        return {"until": timezone.make_aware(datetime.combine(day, time(23, 59)))}
    return {"days": int(data["length"])}


def _moderate(kind):
    def run(actor, user, data):
        extra = _until(data) if kind in (K.FEED_SUSPENSION, K.EVENT_SUSPENSION) else {}
        take_action(
            actor,
            user,
            ActionInput(
                kind=kind,
                rule=data["rule"],
                reason=data["reason"],
                block_email=data.get("block_email", False),
                **extra,
            ),
        )
        return ""

    return run


def _lift(actor, user, data):
    lifted = lift_suspensions(actor, user, data["reason"])
    return ", ".join(action.get_kind_display().lower() for action in lifted)


def _unban(actor, user, data):
    unban(actor, user, data["reason"])
    return ""


def _export(actor, users, data):
    return services.export_rows(actor, users, data.get("include_email", False))


MODERATION = "Moderation"
ACCOUNT = "Account"

ACTIONS = {
    spec.key: spec
    for spec in (
        Spec("warn", "Send a warning", roles.MODERATOR, ("rule", "reason"), _moderate(K.WARNING)),
        Spec(
            "suspend_feed",
            "Suspend from feed",
            roles.MODERATOR,
            ("length", "until", "rule", "reason"),
            _moderate(K.FEED_SUSPENSION),
            protected=True,
        ),
        Spec(
            "suspend_events",
            "Suspend from events",
            roles.MODERATOR,
            ("length", "until", "rule", "reason"),
            _moderate(K.EVENT_SUSPENSION),
            protected=True,
        ),
        Spec("lift_suspensions", "Lift suspensions", roles.MODERATOR, ("reason",), _lift),
        Spec(
            "remove_content",
            "Remove all feed content",
            roles.MODERATOR,
            ("rule", "reason"),
            _moderate(K.REMOVE_ALL_CONTENT),
        ),
        Spec(
            "ban",
            "Ban",
            roles.ADMIN,
            ("rule", "reason", "block_email", "code"),
            _moderate(K.BAN),
            protected=True,
            fresh_code=True,
            danger=True,
        ),
        Spec("unban", "Unban", roles.ADMIN, ("reason", "code"), _unban, fresh_code=True),
        Spec(
            "grant_feed",
            "Grant staff feed grant",
            roles.ADMIN,
            ("reason",),
            lambda actor, user, data: services.set_feed_grant(actor, user, True, data["reason"]),
        ),
        Spec(
            "revoke_feed",
            "Revoke staff feed grant",
            roles.ADMIN,
            ("reason",),
            lambda actor, user, data: services.set_feed_grant(actor, user, False, data["reason"]),
        ),
        Spec(
            "confirm_email",
            "Mark email verified",
            roles.ADMIN,
            ("reason",),
            lambda actor, user, data: services.confirm_email(actor, user, data["reason"]),
        ),
        Spec(
            "password_reset",
            "Send password reset email",
            roles.STAFF,
            (),
            lambda actor, user, data: services.send_password_reset(actor, user),
        ),
        Spec(
            "sign_out",
            "Log out everywhere",
            roles.STAFF,
            ("reason",),
            lambda actor, user, data: services.sign_out_everywhere(actor, user, data["reason"]),
        ),
        Spec(
            "deactivate",
            "Deactivate account",
            roles.ADMIN,
            ("reason",),
            lambda actor, user, data: services.set_active(actor, user, False, data["reason"]),
            protected=True,
            danger=True,
        ),
        Spec(
            "reactivate",
            "Reactivate account",
            roles.ADMIN,
            ("reason",),
            lambda actor, user, data: services.set_active(actor, user, True, data["reason"]),
        ),
        Spec(
            "export", "Export selected (CSV)", roles.ADMIN, ("include_email",), _export, batch=True
        ),
        Spec(
            "erase",
            "Erase account",
            roles.ADMIN,
            ("reason", "confirm", "code"),
            lambda actor, user, data: services.request_erasure(actor, user, data["reason"]),
            protected=True,
            fresh_code=True,
            danger=True,
        ),
    )
}

# How the detail page groups them in its top bar.
GROUPS = {
    MODERATION: (
        "warn",
        "suspend_feed",
        "suspend_events",
        "lift_suspensions",
        "remove_content",
        "ban",
        "unban",
    ),
    ACCOUNT: (
        "grant_feed",
        "revoke_feed",
        "confirm_email",
        "password_reset",
        "sign_out",
        "deactivate",
        "reactivate",
        "export",
        "erase",
    ),
}


def allowed(user, key):
    return roles.has_role(user, ACTIONS[key].role)


def is_protected(user):
    return bool(user.is_staff or user.is_superuser)


def run(actor, key, users, data, code=""):
    """Run one action on these accounts. Raises ActionError when the whole batch is refused
    (role, size, code); otherwise returns what was done and skipped."""
    spec = ACTIONS[key]
    users = list(users)
    if not allowed(actor, key):
        raise ActionError(f"{spec.label} needs the {roles.LABELS[spec.role]} role.")
    if not users:
        raise ActionError("Choose at least one member.")
    if len(users) > MAX_USERS:
        raise ActionError(
            f"Choose at most {MAX_USERS} members at a time; {len(users)} were selected."
        )
    if spec.fresh_code and not fresh_code(actor, code):
        raise ActionError("That code did not work. Use a new code from your authenticator app.")

    summary = Summary()
    eligible = []
    for user in users:
        if user.pk == actor.pk:
            summary.skipped.append((user.display_name, "your own account"))
        elif spec.protected and is_protected(user):
            summary.skipped.append(
                (user.display_name, "a staff or superuser account; change it in Team and roles")
            )
        else:
            eligible.append(user)
    if spec.batch:
        if eligible:
            summary.rows = spec.run(actor, eligible, data)
            summary.done = [(user.display_name, "") for user in eligible]
        return summary
    for user in eligible:
        try:
            note = spec.run(actor, user, data)
        except (SafetyError, AccountActionError) as exc:
            summary.skipped.append((user.display_name, getattr(exc, "message", str(exc))))
        else:
            summary.done.append((user.display_name, note))
    return summary
