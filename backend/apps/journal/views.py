from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.pagination import CursorPagination

from .models import Post, PostImage
from .serializers import PostSerializer


class JournalPagination(CursorPagination):
    page_size = 12
    ordering = ("-published_at", "-pk")


def live_posts():
    return (
        Post.objects.live()
        .select_related("author", "event")
        .prefetch_related(Prefetch("images", queryset=PostImage.objects.order_by("sort_order")))
    )


class PostListView(generics.ListAPIView):
    serializer_class = PostSerializer
    pagination_class = JournalPagination

    def get_queryset(self):
        return live_posts()


class PostDetailView(generics.RetrieveAPIView):
    serializer_class = PostSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return live_posts()
