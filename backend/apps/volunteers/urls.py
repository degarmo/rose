from django.urls import path

from . import views

urlpatterns = [
    path("options/", views.VolunteerOptionsView.as_view(), name="volunteer-options"),
    path("signup/", views.VolunteerSignupCreateView.as_view(), name="volunteer-signup"),
]
