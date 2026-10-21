from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .content import page_entries
from .models import FAQItem, SiteSettings, StaffProfile
from .serializers import FAQItemSerializer, SiteSettingsSerializer, StaffProfileSerializer
from .site_images import site_images

# Public copy: browsers may keep it briefly; the server's own cache is cleared on every edit.
CONTENT_CACHE_CONTROL = "public, max-age=60"
# Page images: browsers check every time, so a replaced picture shows within seconds.
SITE_IMAGES_CACHE_CONTROL = "public, no-cache"


class SiteSettingsView(generics.RetrieveAPIView):
    serializer_class = SiteSettingsSerializer

    def get_object(self):
        return SiteSettings.load()


class FAQListView(generics.ListAPIView):
    serializer_class = FAQItemSerializer
    queryset = FAQItem.objects.filter(is_published=True)


class StaffListView(generics.ListAPIView):
    serializer_class = StaffProfileSerializer
    queryset = StaffProfile.objects.filter(is_published=True)


class PageContentView(APIView):
    """Every piece of editable copy for one page, served from the cache."""

    def get(self, request, page):
        response = Response({"page": page, "entries": page_entries(page)})
        response["Cache-Control"] = CONTENT_CACHE_CONTROL
        return response


class SiteImagesView(APIView):
    """Every page image (slot) the public site shows, from the cache."""

    def get(self, request):
        response = Response({"images": site_images()})
        response["Cache-Control"] = SITE_IMAGES_CACHE_CONTROL
        return response
