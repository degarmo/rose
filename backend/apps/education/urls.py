from django.urls import path

from . import views

urlpatterns = [
    path(
        "opportunities/",
        views.OpportunityViewSet.as_view({"get": "list"}),
        name="opportunity-list",
    ),
    path(
        "opportunities/<slug:slug>/",
        views.OpportunityViewSet.as_view({"get": "retrieve"}),
        name="opportunity-detail",
    ),
]
