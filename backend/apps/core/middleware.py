from django.conf import settings

PRIVATE_PATH_PREFIXES = ("/api/", "/members", "/account", "/media/")


class PrivacyHeadersMiddleware:
    """Mark every private or machine-facing path as non-indexable.

    Search engines that ignore robots.txt still honour X-Robots-Tag, so the
    header is set on every response under a private prefix and on the admin.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.prefixes = PRIVATE_PATH_PREFIXES + (f"/{settings.ADMIN_PATH.strip('/')}",)

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.prefixes):
            response["X-Robots-Tag"] = "noindex, nofollow"
        if request.path.startswith("/api/"):
            response["Cache-Control"] = response.get("Cache-Control", "no-store")
        response["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )
        return response
