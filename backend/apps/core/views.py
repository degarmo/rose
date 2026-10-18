from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

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
    "Disallow: /events/cancel\n"
)
CLOSED_ROBOTS = "User-agent: *\nDisallow: /\n"


@require_GET
def robots_txt(request):
    """Production lists the private paths; every other environment is closed to crawlers."""
    body = PUBLIC_ROBOTS if settings.DJANGO_ENV == "production" else CLOSED_ROBOTS
    return HttpResponse(body, content_type="text/plain")


@require_GET
@never_cache
def csrf_token(request):
    """Hand the SPA a CSRF token while the cookie itself stays HttpOnly."""
    return JsonResponse({"csrfToken": get_token(request)})


def csrf_failure(request, reason=""):
    """JSON instead of Django's HTML page, so the SPA can refresh its token and retry."""
    return JsonResponse({"detail": f"CSRF Failed: {reason}"}, status=403)
