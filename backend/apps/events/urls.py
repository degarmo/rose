from django.urls import path

from . import views

urlpatterns = [
    path("", views.EventListView.as_view(), name="event-list"),
    path("calendar/", views.EventCalendarView.as_view(), name="event-calendar"),
    path("rsvp/cancel/", views.CancelByTokenView.as_view(), name="rsvp-cancel-token"),
    path("<slug:slug>/", views.EventDetailView.as_view(), name="event-detail"),
    path("<slug:slug>/rsvp/", views.EventRSVPView.as_view(), name="event-rsvp"),
    path("<slug:slug>/calendar.ics", views.EventICSView.as_view(), name="event-ics"),
]
