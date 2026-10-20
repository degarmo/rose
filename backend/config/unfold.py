"""The admin's look and navigation (django-unfold), themed as Rose.

Colours, fonts and radii live in apps/core/static/core/rose-admin.css rather than in
COLORS here: Unfold writes COLORS into an inline <style> block, which the content
security policy does not allow (templates/unfold/layouts/skeleton.html loads the
stylesheet instead). Nothing here loads anything from another site.
"""

from django.templatetags.static import static
from django.urls import reverse_lazy

UNFOLD = {
    "SITE_TITLE": "Rose",
    "SITE_HEADER": "Rose",
    "SITE_URL": "/",
    # The site has no description of the club anywhere in the admin.
    "SITE_SUBHEADER": None,
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "8px",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "type": "image/svg+xml",
            "href": lambda request: static("core/favicon.svg"),
        },
    ],
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": "apps.core.admin_nav.sidebar",
    },
    "ACCOUNT": {
        "navigation": [
            {"title": "Staff guide", "link": reverse_lazy("admin:staff_guide")},
            {"title": "Change password", "link": reverse_lazy("admin:password_change")},
            {"title": "View the website", "link": "/"},
        ],
    },
    "DASHBOARD_CALLBACK": "apps.core.dashboard.dashboard_callback",
}
