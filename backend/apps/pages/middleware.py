from django.http import HttpResponsePermanentRedirect

from apps.core.middleware import admin_prefix

from .content import redirect_for


class OldSiteRedirectMiddleware:
    """301s from the old site's addresses, before the single-page app's fallback.

    Only GET and HEAD on paths that could be pages: never the API, the admin,
    media or static files. Unknown old paths fall through to the site's normal
    not-found page.
    """

    SKIP = ("/api/", "/media/", "/static/", "/assets/", "/healthz")

    def __init__(self, get_response):
        self.get_response = get_response
        self.skip = (*self.SKIP, admin_prefix())

    def __call__(self, request):
        if request.method in ("GET", "HEAD") and not request.path.startswith(self.skip):
            target = redirect_for(request.path)
            if target and target.rstrip("/") != request.path.rstrip("/"):
                return HttpResponsePermanentRedirect(target)
        return self.get_response(request)
