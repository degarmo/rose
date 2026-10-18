from rest_framework import viewsets

from .filters import OpportunityFilter
from .models import Opportunity
from .serializers import OpportunityDetailSerializer, OpportunitySerializer


class OpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Opportunity.objects.published()
    lookup_field = "slug"
    filterset_class = OpportunityFilter

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OpportunityDetailSerializer
        return OpportunitySerializer
