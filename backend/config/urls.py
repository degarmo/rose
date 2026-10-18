from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from apps.core import spa
from apps.core import views as core_views

api_patterns = [
    path("csrf/", core_views.csrf_token, name="csrf"),
    path("", include("apps.pages.urls")),
    path("education/", include("apps.education.urls")),
    path("contact/", include("apps.contact.urls")),
    path("account/feed/", include("apps.feed.account_urls")),
    path("account/", include("apps.accounts.urls")),
    path("members/", include("apps.feed.urls")),
    path("membership/", include("apps.memberships.urls")),
    path("payments/", include("apps.memberships.payment_urls")),
    path("events/", include("apps.events.urls")),
    path("journal/", include("apps.journal.urls")),
]

urlpatterns = [
    path("robots.txt", core_views.robots_txt, name="robots"),
    path(settings.ADMIN_PATH, admin.site.urls),
    path("api/", include(api_patterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Last: every other path is a client-side route of the single-page app.
urlpatterns += [re_path(r"^(?P<path>.*)$", spa.spa, name="spa")]
