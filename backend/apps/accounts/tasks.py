"""Account email. Tasks take ids, not tokens, so no secret sits in the queue."""

from celery import shared_task

from apps.core.email import send_neutral_mail, site_link

from .models import User
from .tokens import make_reset_params, make_verification_token

VERIFY_SUBJECT = "Confirm your email"
ALREADY_REGISTERED_SUBJECT = "About your sign-up"
RESET_SUBJECT = "Reset your password"
PASSWORD_CHANGED_SUBJECT = "Your password was changed"
DELETED_SUBJECT = "Your account has been closed"

SIGN_OFF = "\n\nIf this was not you, you can ignore this email.\n"


def _active_user(user_id):
    return User.objects.filter(pk=user_id, is_active=True).first()


@shared_task
def send_verification_email(user_id):
    user = _active_user(user_id)
    if user is None or user.email_verified:
        return
    link = site_link(f"/account/verify#token={make_verification_token(user)}")
    body = (
        f"Hello {user.display_name},\n\n"
        f"Please confirm your email address by opening this link within three days:\n\n"
        f"{link}" + SIGN_OFF
    )
    send_neutral_mail(VERIFY_SUBJECT, body, to=[user.email])


@shared_task
def send_already_registered_email(user_id):
    user = _active_user(user_id)
    if user is None:
        return
    body = (
        "Someone tried to create an account with this email address, which already has one.\n\n"
        f"To sign in, go to {site_link('/account/login')}\n"
        f"If you have forgotten your password, go to {site_link('/account/forgot')}" + SIGN_OFF
    )
    send_neutral_mail(ALREADY_REGISTERED_SUBJECT, body, to=[user.email])


@shared_task
def send_password_reset_email(user_id):
    user = _active_user(user_id)
    if user is None:
        return
    uid, token = make_reset_params(user)
    link = site_link(f"/account/reset#uid={uid}&token={token}")
    body = f"Use this link within two hours to choose a new password:\n\n{link}" + SIGN_OFF
    send_neutral_mail(RESET_SUBJECT, body, to=[user.email])


@shared_task
def send_password_changed_email(user_id):
    user = _active_user(user_id)
    if user is None:
        return
    body = (
        "The password for your account was just changed.\n\n"
        "If you did not do this, reset your password straight away at "
        f"{site_link('/account/forgot')} and let us know through the contact form.\n"
    )
    send_neutral_mail(PASSWORD_CHANGED_SUBJECT, body, to=[user.email])


@shared_task
def send_account_deleted_email(email):
    body = (
        "Your account has been closed and your details removed, as you asked.\n\n"
        "Thank you for being part of the community.\n"
    )
    send_neutral_mail(DELETED_SUBJECT, body, to=[email])
