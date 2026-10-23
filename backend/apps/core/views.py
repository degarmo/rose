from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.static import serve

from .preview import preview_active

# Private paths are disallowed. The admin is deliberately not listed: naming
# it here would publish its secret path.
PUBLIC_ROBOTS = (
    "User-agent: *\n"
    "Allow: /\n"
    "Disallow: /members\n"
    "Disallow: /account\n"
    "Disallow: /join/confirming\n"
    "Disallow: /api\n"
    "Disallow: /media\n"
    "Disallow: /exit\n"
    "Disallow: /dev\n"
    "Disallow: /subscribe\n"
    "Disallow: /unsubscribe\n"
    "Disallow: /events/cancel\n"
)
CLOSED_ROBOTS = "User-agent: *\nDisallow: /\n"


@require_GET
def robots_txt(request):
    """Indexable sites list the private paths; staging and development are closed to crawlers."""
    indexable = settings.SITE_INDEXABLE and settings.DJANGO_ENV != "staging"
    body = PUBLIC_ROBOTS if indexable else CLOSED_ROBOTS
    return HttpResponse(body, content_type="text/plain")


@require_GET
@never_cache
def csrf_token(request):
    """Hand the SPA a CSRF token while the cookie itself stays HttpOnly."""
    return JsonResponse({"csrfToken": get_token(request)})


def csrf_failure(request, reason=""):
    """JSON instead of Django's HTML page, so the SPA can refresh its token and retry."""
    return JsonResponse({"detail": f"CSRF Failed: {reason}"}, status=403)


@require_GET
def preview_media(request, path):
    """Public uploads in a staging preview, which keeps them on the container's disk
    (apps.core.preview). Elsewhere they are on object storage, so this is a 404. Private
    media is in another folder and is only ever served by its access-checked view."""
    if not (preview_active() and settings.STORAGE_BACKEND == "local"):
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)
