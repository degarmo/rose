from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from apps.core import spa
from apps.core import views as core_views
from apps.safety import views as safety_views

api_patterns = [
    path("csrf/", core_views.csrf_token, name="csrf"),
    path("", include("apps.pages.urls")),
    path("education/", include("apps.education.urls")),
    path("contact/", include("apps.contact.urls")),
    path("account/feed/", include("apps.feed.account_urls")),
    path("account/", include("apps.safety.account_urls")),
    path("account/", include("apps.accounts.urls")),
    path("members/", include("apps.feed.urls")),
    path("staff/", include("apps.safety.urls")),
    path("concerns/", safety_views.ConcernView.as_view(), name="concerns"),
    path("membership/", include("apps.memberships.urls")),
    path("payments/", include("apps.memberships.payment_urls")),
    path("events/", include("apps.events.urls")),
    path("journal/", include("apps.journal.urls")),
    path("rentals/", include("apps.rentals.urls")),
    path("volunteer/", include("apps.volunteers.urls")),
    path("donations/", include("apps.donations.urls")),
    path("newsletter/", include("apps.newsletter.urls")),
]

urlpatterns = [
    path("robots.txt", core_views.robots_txt, name="robots"),
    path(settings.ADMIN_PATH, admin.site.urls),
    path("api/", include(api_patterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# Public uploads on disk in a staging preview; a 404 everywhere else.
urlpatterns += [re_path(r"^media/(?P<path>.*)$", core_views.preview_media, name="preview-media")]

# Last: every other path is a client-side route of the single-page app.
urlpatterns += [re_path(r"^(?P<path>.*)$", spa.spa, name="spa")]
