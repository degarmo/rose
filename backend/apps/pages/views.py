from rest_framework import generics

from .models import FAQItem, SiteSettings
from .serializers import FAQItemSerializer, SiteSettingsSerializer


class SiteSettingsView(generics.RetrieveAPIView):
    serializer_class = SiteSettingsSerializer

    def get_object(self):
        return SiteSettings.load()


class FAQListView(generics.ListAPIView):
    serializer_class = FAQItemSerializer
    queryset = FAQItem.objects.filter(is_published=True)
