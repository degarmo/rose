from django.urls import path

from . import views

urlpatterns = [
    path("posts/", views.PostListView.as_view(), name="journal-list"),
    path("posts/<slug:slug>/", views.PostDetailView.as_view(), name="journal-detail"),
]
