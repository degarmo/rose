from django.urls import path

from . import views

urlpatterns = [
    path("site-settings/", views.SiteSettingsView.as_view(), name="site-settings"),
    path("faqs/", views.FAQListView.as_view(), name="faq-list"),
]
