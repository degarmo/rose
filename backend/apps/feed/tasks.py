from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.core.email import send_neutral_mail, site_link
from apps.core.private_media import private_media

from . import services
from .models import DataExport

ERASE_SUBJECT = "Your request is complete"
EXPORT_SUBJECT = "Your download is ready"


@shared_task
def process_post_images(post_id):
    services.process_images(post_id)


@shared_task
def erase_member_feed(user_id, notify=True):
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return
    services.erase_feed_data(user)
    if notify:
        send_neutral_mail(
            ERASE_SUBJECT,
            f"Hello {user.display_name},\n\n"
            "Everything you shared in the members area has now been permanently deleted: "
            "posts, photos, comments, likes, follows and notifications.\n\n"
            "Your account itself is unchanged.\n",
            to=[user.email],
        )


@shared_task
def build_member_export(export_id):
    export = DataExport.objects.select_related("user").filter(pk=export_id).first()
    if export is None:
        return
    token = services.build_export(export)
    send_neutral_mail(
        EXPORT_SUBJECT,
        f"Hello {export.user.display_name},\n\n"
        "The copy of your data you asked for is ready. The link works once and expires "
        "in 24 hours:\n\n"
        f"{site_link(f'/account/export#token={token}')}\n\n"
        "If you did not ask for this, you can ignore this email.\n",
        to=[export.user.email],
    )


@shared_task
def purge_expired_exports():
    """Delete export files once used or expired, and drop the old rows."""
    media = private_media()
    now = timezone.now()
    done = DataExport.objects.filter(Q(used_at__isnull=False) | Q(expires_at__lte=now))
    count = 0
    for export in done:
        media.delete(export.file_name)
        export.delete()
        count += 1
    return count
