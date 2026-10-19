from django.urls import path

from . import views

urlpatterns = [
    path("notices/", views.NoticeListView.as_view(), name="account-notices"),
    path(
        "notices/<int:pk>/appeal/", views.NoticeAppealView.as_view(), name="account-notice-appeal"
    ),
    path("reports/", views.MyReportsView.as_view(), name="account-reports"),
]
