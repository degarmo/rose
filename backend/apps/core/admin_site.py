import mimetypes

from django.contrib import admin
from django.http import FileResponse, Http404
from django.template.response import TemplateResponse
from django.urls import path

from . import admin_auth
from .consent_images import consent_image_field_names, consent_image_models
from .dashboard import build_dashboard
from .manifest import STATUS_LABELS, entry_status, find_entry, image_file, load_manifest


class RoseAdminSite(admin.AdminSite):
    site_header = "Rose administration"
    site_title = "Rose"
    index_title = "Site content"

    def has_permission(self, request):
        """Staff only, and only after the two-step check (apps.core.admin_auth)."""
        return super().has_permission(request) and request.user.is_verified()

    def index(self, request, extra_context=None):
        """The admin home page, with a metrics dashboard above the model list."""
        context = {"dashboard": build_dashboard(request.user), **(extra_context or {})}
        return super().index(request, extra_context=context)

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
            path(
                "image-review/file/<str:filename>",
                self.admin_view(self.image_file_view),
                name="image_review_file",
            ),
        ]
        return extra + super().get_urls()

    def _pre_auth(self, view):
        def wrapped(request):
            return view(request, self)

        return wrapped

    def image_review_view(self, request):
        """Read-only overview of every site image and why it is shown or hidden."""
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
