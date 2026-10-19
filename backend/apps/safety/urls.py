from django.urls import path

from . import views

urlpatterns = [
    path("overview/", views.OverviewView.as_view(), name="staff-overview"),
    path("metrics/", views.MetricsView.as_view(), name="staff-metrics"),
    path("metrics/export/", views.MetricsExportView.as_view(), name="staff-metrics-export"),
    path("team/", views.TeamView.as_view(), name="staff-team"),
    path("rules/", views.RulesView.as_view(), name="staff-rules"),
    path("reports/", views.ReportListView.as_view(), name="staff-reports"),
    path("reports/<int:pk>/", views.ReportDetailView.as_view(), name="staff-report"),
    path("reports/<int:pk>/status/", views.ReportStatusView.as_view(), name="staff-report-status"),
    path("reports/<int:pk>/assign/", views.ReportAssignView.as_view(), name="staff-report-assign"),
    path("reports/<int:pk>/notes/", views.ReportNoteView.as_view(), name="staff-report-notes"),
    path("reports/<int:pk>/reveal/", views.ReportRevealView.as_view(), name="staff-report-reveal"),
    path("members/", views.MemberSearchView.as_view(), name="staff-members"),
    path("members/<str:handle>/", views.MemberDetailView.as_view(), name="staff-member"),
    path(
        "members/<str:handle>/actions/",
        views.MemberActionView.as_view(),
        name="staff-member-actions",
    ),
    path(
        "actions/<int:pk>/reverse/", views.ActionReverseView.as_view(), name="staff-action-reverse"
    ),
    path("appeals/", views.AppealListView.as_view(), name="staff-appeals"),
    path("appeals/<int:pk>/", views.AppealDetailView.as_view(), name="staff-appeal"),
    path("appeals/<int:pk>/decide/", views.AppealDecideView.as_view(), name="staff-appeal-decide"),
    path("media/<str:public_id>/", views.StaffMediaView.as_view(), name="staff-media"),
]
