"""Erasing an account: one routine for the member's own "Delete account" and staff's
"Erase account" (run as a task, apps.accounts.tasks.erase_account).

It frees their event places, deletes everything they made in the member feed with its
files (posts, images in storage, comments, likes, follows, blocks, notifications, cached
and watermarked copies, exports), detaches memberships, payments and gifts, forgets their
contact messages, volunteer offers and rental contact details, and deletes the account
with its profile, RSVPs and ID checks. Moderation records stay, showing "Erased member",
and so does a blocked email address from a ban.

No other code path deletes an account: the admin offers no delete (tests/test_user_admin).
"""

from django.db import transaction

from apps.contact.models import anonymize_messages_from
from apps.core.models import AuditLog
from apps.events.services import release_places_held_by
from apps.feed.services import erase_feed_data
from apps.memberships.account import close_for_deleted_account
from apps.rentals.services import forget_account as forget_rental_contact
from apps.volunteers.models import forget_account as forget_volunteer


def erase_account(user):
    """Erase the account. Returns the email address, for the closing email."""
    email = user.email
    with transaction.atomic():
        release_places_held_by(user)
        erase_feed_data(user)
        # Stops online renewals; payment records stay, detached from the person.
        close_for_deleted_account(user)
        anonymize_messages_from(email)
        # Volunteer offers go; rental inquiries keep only type, date and status.
        forget_volunteer(user)
        forget_rental_contact(user)
        AuditLog.forget_person(user)
        # Cascades to the profile, RSVPs and ID checks; moderation records are kept.
        user.delete()
    return email
