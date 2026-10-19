from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.MeView.as_view(), name="feed-me"),
    path("me/avatar/", views.MyAvatarView.as_view(), name="feed-me-avatar"),
    path("me/blocks/", views.MyBlocksView.as_view(), name="feed-me-blocks"),
    path("guidelines/", views.GuidelinesView.as_view(), name="feed-guidelines"),
    path("feed/", views.FeedView.as_view(), name="feed-list"),
    path("home/", views.HomeView.as_view(), name="feed-home"),
    path("saved/", views.SavedView.as_view(), name="feed-saved"),
    path("stories/", views.StoriesView.as_view(), name="feed-stories"),
    path("stories/seen/", views.StoriesSeenView.as_view(), name="feed-stories-seen"),
    path("posts/<str:public_id>/", views.PostDetailView.as_view(), name="feed-post"),
    path("posts/<str:public_id>/like/", views.PostLikeView.as_view(), name="feed-post-like"),
    path("posts/<str:public_id>/save/", views.PostSaveView.as_view(), name="feed-post-save"),
    path(
        "posts/<str:public_id>/comments/",
        views.PostCommentsView.as_view(),
        name="feed-post-comments",
    ),
    path("comments/<str:public_id>/", views.CommentDetailView.as_view(), name="feed-comment"),
    path("u/<str:handle>/", views.MemberProfileView.as_view(), name="feed-member"),
    path("u/<str:handle>/posts/", views.MemberPostsView.as_view(), name="feed-member-posts"),
    path(
        "u/<str:handle>/<str:kind>/",
        views.MemberRelationshipView.as_view(),
        name="feed-member-relationship",
    ),
    path("directory/", views.DirectoryView.as_view(), name="feed-directory"),
    path("notifications/", views.NotificationsView.as_view(), name="feed-notifications"),
    path(
        "notifications/read/",
        views.NotificationsReadView.as_view(),
        name="feed-notifications-read",
    ),
    path("reports/", views.ReportView.as_view(), name="feed-reports"),
    path("media/<str:public_id>/", views.MediaView.as_view(), name="feed-media"),
    path("avatars/<str:key>/", views.AvatarMediaView.as_view(), name="feed-avatar"),
]
