"""Serve the built React app from Django, so everything shares one origin.

WhiteNoise serves the hashed files in FRONTEND_DIST (`/assets/...`) with a
year-long immutable cache. Every client route gets index.html with
`Cache-Control: no-cache`, so a deploy is picked up on the next page load.
The fallback never answers for the API, the admin, media or anything that
looks like a file, which get a real 404 instead.
"""

import re
from functools import lru_cache

from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils.html import escape
from django.views.decorators.http import require_safe

from .branding import site_name

SITE_IMAGES_META = '<meta name="rose-site-images" content="{}" />'
# The club's name, read by the app before it makes any request (the age gate shows it).
SITE_NAME_META = '<meta name="rose-site-name" content="{}" />'
TITLE = re.compile(r"<title>[^<]*</title>")
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
    name = escape(site_name())
    html = TITLE.sub(f"<title>{name}</title>", html, count=1)
    tags = [SITE_IMAGES_META.format(escape(settings.SITE_IMAGES_URL)), SITE_NAME_META.format(name)]
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
    return response
