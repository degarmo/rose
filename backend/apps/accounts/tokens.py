from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.core.ratelimit import hashed_value

from .models import User

VERIFY_SALT = "accounts.email-verification"


def make_verification_token(user):
    """Signed, expiring token tied to the user and their current email address."""
    return signing.dumps({"u": user.pk, "e": hashed_value(user.email)}, salt=VERIFY_SALT)


def user_from_verification_token(token):
    try:
        data = signing.loads(token, salt=VERIFY_SALT, max_age=settings.EMAIL_VERIFICATION_MAX_AGE)
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=data.get("u"), is_active=True).first()
    if user is None or hashed_value(user.email) != data.get("e"):
        return None
    return user


def make_reset_params(user):
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


def user_from_reset_params(uid, token):
    try:
        pk = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError):
        return None
    user = User.objects.filter(pk=pk, is_active=True).first()
    if user is None or not default_token_generator.check_token(user, token):
        return None
    return user
