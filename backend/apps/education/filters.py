import django_filters

from .models import Opportunity


class OpportunityFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(choices=Opportunity.Category.choices)
    level = django_filters.ChoiceFilter(choices=Opportunity.Level.choices)

    class Meta:
        model = Opportunity
        fields = ["category", "level"]
