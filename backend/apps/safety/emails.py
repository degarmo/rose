"""Discreet email for moderation and concerns.

Subjects never say what happened, and bodies never quote a report, a post or a
reason: they say where to look, and the details are only in the app.
"""

from apps.core.email import send_neutral_mail, site_link

ACCOUNT_SUBJECT = "An update about your account"
RECEIVED_SUBJECT = "We received your message"
REVIEWED_SUBJECT = "An update on your message"
TEAM_SUBJECT = "Something is waiting for review"


def account_update(address):
    body = (
        "Hello,\n\n"
        "There is an update about your account. You can read it on your account page:\n"
        f"{site_link('/account/notices')}\n"
    )
    send_neutral_mail(ACCOUNT_SUBJECT, body, to=[address])


def concern_received(address):
    body = (
        "Hello,\n\n"
        "Thank you for writing to us. Your message has reached our team, and someone will "
        "look at it soon. We will write again once it has been reviewed.\n"
    )
    send_neutral_mail(RECEIVED_SUBJECT, body, to=[address])


def concern_reviewed(address):
    body = (
        "Hello,\n\n"
        "Our team has now reviewed your message. Thank you for telling us.\n\n"
        "If there is anything else, you can write to us again at "
        f"{site_link('/report-a-concern')}\n"
    )
    send_neutral_mail(REVIEWED_SUBJECT, body, to=[address])


def alert_team(addresses):
    """A new report or appeal is waiting. Nothing about it is in the email."""
    if not addresses:
        return
    body = (
        f"Something new is waiting in the staff inbox.\n\n{site_link('/members/staff/reports')}\n"
    )
    for address in addresses:
        send_neutral_mail(TEAM_SUBJECT, body, to=[address])
