import mimetypes

import markdown
import nh3
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.safestring import mark_safe
from unfold.sites import UnfoldAdminSite

from . import admin_auth
from .branding import site_name
from .consent_images import consent_image_field_names, consent_image_models
from .manifest import STATUS_LABELS, entry_status, find_entry, image_file, load_manifest

# Staff who look after the pages that carry images may open Image review.
IMAGE_PERMISSIONS = (
    "events.change_event",
    "journal.change_post",
    "pages.change_staffprofile",
    "education.change_opportunity",
)


def can_review_images(user):
    return user.is_superuser or any(user.has_perm(perm) for perm in IMAGE_PERMISSIONS)


class RoseAdminSite(UnfoldAdminSite):
    """The admin in the site's look (django-unfold, config/unfold.py), behind the two-step login."""

    index_title = "Dashboard"

    # The club's name from settings (apps.core.branding), never written into the code.
    @property
    def site_header(self):
        return site_name()

    @property
    def site_title(self):
        return site_name()

    def has_permission(self, request):
        """Staff only, and only after the two-step check (apps.core.admin_auth)."""
        return super().has_permission(request) and request.user.is_verified()

    def login(self, request, extra_context=None):
        return admin_auth.admin_login(request, self)

    def get_urls(self):
        extra = [
            path("login/verify/", self._pre_auth(admin_auth.otp_verify), name="otp_verify"),
            path("login/set-up/", self._pre_auth(admin_auth.otp_enrol), name="otp_enrol"),
            path(
                "login/backup-codes/",
                self._pre_auth(admin_auth.otp_backup_codes),
                name="otp_backup_codes",
            ),
            path(
                "image-review/",
                self.admin_view(self.image_review_view),
                name="image_review",
            ),
            path("staff-guide/", self.admin_view(self.staff_guide_view), name="staff_guide"),
            path(
                "metrics/export/",
                self.admin_view(self.metrics_export_view),
                name="metrics_export",
            ),
            path(
                "image-review/file/<str:filename>",
                self.admin_view(self.image_file_view),
                name="image_review_file",
            ),
        ]
        return extra + super().get_urls()

    def metrics_export_view(self, request):
        """The dashboard's figures as CSV: the same aggregates, small numbers withheld, and
        the download is logged. Admin and Staff roles only."""
        from django.http import HttpResponse
        from django.utils import timezone

        from apps.core import metrics
        from apps.core.models import AuditLog, audit

        from .dashboard import sees_everything

        if request.method != "POST" or not sees_everything(request.user):
            raise PermissionDenied
        data = metrics.dashboard(str(request.POST.get("range", "30d")))
        audit(
            AuditLog.Category.EXPORT,
            "metrics_export",
            request.user,
            f"Dashboard figures ({data['range']})",
            "metrics",
        )
        response = HttpResponse(metrics.export_csv(data), content_type="text/csv; charset=utf-8")
        stamp = timezone.localdate().isoformat()
        response["Content-Disposition"] = (
            f'attachment; filename="metrics-{data["range"]}-{stamp}.csv"'
        )
        response["Cache-Control"] = "private, no-store"
        return response

    def _pre_auth(self, view):
        def wrapped(request):
            return view(request, self)

        return wrapped

    def image_review_view(self, request):
        """Read-only overview of every site image and why it is shown or hidden."""
        if not can_review_images(request.user):
            raise PermissionDenied
        manifest_rows = []
        for entry in load_manifest()["images"]:
            status = entry_status(entry)
            manifest_rows.append(
                {
                    "entry": entry,
                    "status": status,
                    "status_label": STATUS_LABELS[status],
                    "has_file": image_file(entry).exists(),
                }
            )
        manifest_rows.sort(key=lambda row: (row["status"] == "shown", row["entry"]["filename"]))

        upload_rows = []
        for model in consent_image_models(include_private=False):
            for field in consent_image_field_names(model):
                for obj in model.objects.exclude(**{field: ""}):
                    upload_rows.append(
                        {
                            "object": obj,
                            "model": model._meta.verbose_name,
                            "url": getattr(obj, field).url,
                            "alt": getattr(obj, f"{field}_alt"),
                            "shown": obj.image_is_displayable(field),
                            "reason": obj.image_hidden_reason(field) or "Shown on the site",
                        }
                    )
        upload_rows.sort(key=lambda row: row["shown"])

        context = {
            **self.each_context(request),
            "title": "Image review",
            "manifest_rows": manifest_rows,
            "upload_rows": upload_rows,
            "hidden_count": sum(1 for row in manifest_rows if row["status"] != "shown")
            + sum(1 for row in upload_rows if not row["shown"]),
        }
        return TemplateResponse(request, "admin/image_review.html", context)

    def image_file_view(self, request, filename):
        """Serve a manifest image to staff only, so hidden images never go public."""
        if not can_review_images(request.user):
            raise PermissionDenied
        entry = find_entry(load_manifest(), filename)
        if entry is None:
            raise Http404
        file_path = image_file(entry)
        if not file_path.exists():
            raise Http404
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        response = FileResponse(file_path.open("rb"), content_type=content_type)
        response["Cache-Control"] = "private, no-store"
        return response

    def staff_guide_view(self, request):
        """docs/staff-guide.md, for anyone with a staff login."""
        try:
            text = settings.STAFF_GUIDE_PATH.read_text(encoding="utf-8")
        except OSError as exc:
            raise Http404("The staff guide is not on this server.") from exc
        rendered = nh3.clean(
            markdown.markdown(text),
            tags={"h1", "h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "code", "a"},
            attributes={"a": {"href"}},
            url_schemes={"https", "mailto"},
            link_rel="noopener noreferrer",
        )
        context = {
            **self.each_context(request),
            "title": "Staff guide",
            "guide": mark_safe(rendered),  # sanitised by nh3 above
        }
        return TemplateResponse(request, "admin/staff_guide.html", context)
