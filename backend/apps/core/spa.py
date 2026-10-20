"""Serve the built React app from Django, so everything shares one origin.

WhiteNoise serves the hashed files in FRONTEND_DIST (`/assets/...`) with a
year-long immutable cache. Every client route gets index.html with
`Cache-Control: no-cache`, so a deploy is picked up on the next page load.
The fallback never answers for the API, the admin, media or anything that
looks like a file, which get a real 404 instead.
"""

from functools import lru_cache

from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils.html import escape
from django.views.decorators.http import require_safe

SITE_IMAGES_META = '<meta name="rose-site-images" content="{}" />'
# The storage buckets serve every image, so their connections start with the page.
PRECONNECT = '<link rel="preconnect" href="{}" />'


def _excluded_prefixes():
    return ("/api/", f"/{settings.ADMIN_PATH.strip('/')}/", "/media/", "/static/", "/assets/")


@lru_cache(maxsize=1)
def _index_template(path, modified):
    return path.read_text(encoding="utf-8")


def index_html():
    path = settings.FRONTEND_DIST / "index.html"
    if not path.is_file():
        raise Http404("The site has not been built. Run `npm run build` in frontend/.")
    html = _index_template(path, path.stat().st_mtime)
    tags = [SITE_IMAGES_META.format(escape(settings.SITE_IMAGES_URL))]
    tags += [PRECONNECT.format(escape(origin)) for origin in settings.MEDIA_ORIGINS]
    head = "".join(f"    {tag}\n" for tag in tags)
    return html.replace("</head>", f"{head}  </head>", 1)


@require_safe
def spa(request, path=""):
    full = request.path
    last_segment = full.rstrip("/").rsplit("/", 1)[-1]
    if full.startswith(_excluded_prefixes()) or "." in last_segment:
        raise Http404
    response = HttpResponse(index_html(), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    if _is_past_event_page(full):
        # Old links still work, but search engines should not list an evening that is over.
        response["X-Robots-Tag"] = "noindex"
    return response


def _is_past_event_page(path):
    from apps.events.models import Event

    parts = path.strip("/").split("/")
    if len(parts) != 2 or parts[0] != "events":
        return False
    event = Event.objects.filter(slug=parts[1]).only("starts_at", "ends_at").first()
    return bool(event and event.is_past)
