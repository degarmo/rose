"""Accounts that stand for the site itself, where a record must name who acted.

import_members records carried-over ID checks against one, and make_feed_member (DEBUG
only) records its door desk activations against another. Nobody can log in as either:
they are inactive and have no usable password.
"""

from apps.accounts.models import User


def system_user(email, display_name):
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_user(email=email, display_name=display_name)
        user.set_unusable_password()
        user.is_active = False
        user.save()
    return user
