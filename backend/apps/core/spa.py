"""Serve the built React app from Django, so everything shares one origin.

WhiteNoise serves the hashed files in FRONTEND_DIST (`/assets/...`) with a
year-long immutable cache. Every client route gets index.html with
`Cache-Control: no-cache`, so a deploy is picked up on the next page load.
The fallback never answers for the API, the admin, media or anything that
looks like a file, which get a real 404 instead.
"""

import json
import re
from functools import lru_cache

from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils.html import escape
from django.views.decorators.http import require_safe

from apps.pages.site_images import site_images

from .branding import display_name, neutral_name, short_name

# The page images (apps.pages.site_images), read by the app before it makes any request.
SITE_IMAGES_DATA = '<script type="application/json" id="rose-site-images">{}</script>'
# A page's own pictures start downloading with the page. The sizes match the app's frame
# (PageHero and the home hero), so the browser uses this download for the picture; page
# headers only show from 1024px.
PAGE_IMAGE = (
    '<link rel="preload" as="image" type="image/webp" fetchpriority="high" imagesrcset="{}" '
    'imagesizes="(min-width: 1024px) 50vw, 100vw"{} />'
)
# The club's names and the neutral one, read by the app before it makes any request
# (the age gate shows the name; member-app tabs and calendar notes use the neutral one).
NAME_META = '<meta name="rose-site-{}" content="{}" />'
OPEN_GRAPH = '<meta property="og:{}" content="{}" />'
# The preview picture for a shared link: the emblem on blush (scripts/build_brand_assets.py).
OPEN_GRAPH_IMAGE = ("/brand/og-image.jpg", 1200, 630)
# The name under a home-screen icon is always the neutral one.
HOME_SCREEN_META = '<meta name="{}" content="{}" />'
HOME_SCREEN_NAMES = ("apple-mobile-web-app-title", "application-name")
TITLE = re.compile(r"<title>[^<]*</title>")
# Member-app tabs keep the neutral name: a tab title shows on shared screens.
MEMBER_APP = "/members"
# The storage buckets serve every image, so their connections start with the page.
PRECONNECT = '<link rel="preconnect" href="{}" />'
# A first visit opens on the age gate, where the emblem is the largest thing: it is fetched
# with the page rather than once the app has drawn the gate. The candidates and size match
# the gate's <Logo height={120}> exactly, so the browser uses this download for it.
AGE_COOKIE = "age_ok"
GATE_EMBLEM = (
    '<link rel="preload" as="image" type="image/webp" fetchpriority="high" imagesrcset="'
    + ", ".join(f"/brand/emblem-{width}.webp {width}w" for width in (120, 240, 480, 960))
    + '" imagesizes="247px" />'
)


def _excluded_prefixes():
    return ("/api/", f"/{settings.ADMIN_PATH.strip('/')}/", "/media/", "/static/", "/assets/")


@lru_cache(maxsize=1)
def _index_template(path, modified):
    return path.read_text(encoding="utf-8")


def index_html(path_requested="/", age_confirmed=True):
    path = settings.FRONTEND_DIST / "index.html"
    if not path.is_file():
        raise Http404("The site has not been built. Run `npm run build` in frontend/.")
    html = _index_template(path, path.stat().st_mtime)
    display, short, neutral = escape(display_name()), escape(short_name()), escape(neutral_name())
    member_app = path_requested == MEMBER_APP or path_requested.startswith(f"{MEMBER_APP}/")
    title = neutral if member_app else display
    html = TITLE.sub(f"<title>{title}</title>", html, count=1)
    tags = [
        SITE_IMAGES_DATA.format(_script_json(site_images())),
        NAME_META.format("display-name", display),
        NAME_META.format("short-name", short),
        NAME_META.format("neutral-name", neutral),
        *(HOME_SCREEN_META.format(name, neutral) for name in HOME_SCREEN_NAMES),
    ]
    if not member_app:
        image, width, height = OPEN_GRAPH_IMAGE
        tags += [
            OPEN_GRAPH.format("site_name", display),
            OPEN_GRAPH.format("title", display),
            OPEN_GRAPH.format("image", escape(f"{settings.SITE_URL}{image}")),
            OPEN_GRAPH.format("image:width", width),
            OPEN_GRAPH.format("image:height", height),
            OPEN_GRAPH.format("image:alt", display),
        ]
    tags += [PRECONNECT.format(escape(origin)) for origin in settings.MEDIA_ORIGINS]
    if not age_confirmed:
        tags.append(GATE_EMBLEM)
    else:
        tags += _page_image_preloads(path_requested)
    head = "".join(f"    {tag}\n" for tag in tags)
    return html.replace("</head>", f"{head}  </head>", 1)


def _script_json(data):
    """JSON safe inside a <script> element: nothing in it can close the element."""
    return json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")


def _page_image_preloads(path):
    from apps.pages.models import SiteImage

    pages = {page_path: page for page, page_path in SiteImage.PATHS.items()}
    page = pages.get(path.rstrip("/") or "/")
    if page is None:
        return []
    media = "" if page == SiteImage.Page.HOME else ' media="(min-width: 1024px)"'
    return [
        PAGE_IMAGE.format(escape(image["srcset"]), media)
        for slot, image in site_images().items()
        if slot.startswith(f"{page}.") and image["srcset"]
    ]


@require_safe
def spa(request, path=""):
    full = request.path
    last_segment = full.rstrip("/").rsplit("/", 1)[-1]
    if full.startswith(_excluded_prefixes()) or "." in last_segment:
        raise Http404
    age_confirmed = request.COOKIES.get(AGE_COOKIE) == "1"
    response = HttpResponse(
        index_html(full, age_confirmed), content_type="text/html; charset=utf-8"
    )
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
