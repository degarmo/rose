"""The owner's "everything" account: a superuser.

A superuser holds the Admin role (roles.role_of) and every entitlement
(memberships.access.entitlements), with no membership record. The first time one
logs in, their account is made ready to use the member app: the email is treated as
confirmed (only someone with server access can create a superuser) and they join the
member app quietly, hidden from the directory, with no bio, picture or posts.
"""

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.feed import services as feed_services
from apps.feed.access import can_join_feed
from apps.feed.models import Guidelines


def prepare_owner(user):
    """Idempotent. Returns True when something changed."""
    if not (user.is_superuser and user.is_active):
        return False
    changed = False
    if not user.email_verified:
        user.mark_email_verified()
        changed = True
    profile = user.profile
    guidelines = Guidelines.current()
    first_time = profile.joined_feed_at is None and not profile.participates_in_feed
    if guidelines is not None and first_time and can_join_feed(user):
        feed_services.join_feed(user, guidelines.version, bio="", hide_from_directory=True)
        changed = True
    return changed


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    prepare_owner(user)
