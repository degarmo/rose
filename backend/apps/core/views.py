from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

ROBOTS_TXT = "User-agent: *\nDisallow: /\n"


@require_GET
def robots_txt(request):
    """The API host is never indexed. The public site serves its own file."""
    return HttpResponse(ROBOTS_TXT, content_type="text/plain")


@require_GET
@never_cache
def csrf_token(request):
    """Hand the SPA a CSRF token while the cookie itself stays HttpOnly."""
    return JsonResponse({"csrfToken": get_token(request)})


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
