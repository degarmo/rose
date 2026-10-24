"""Which rows are sample content (apps.pages.samples), for the admin and for --purge only.

Nothing on the public site reads this: serializers and pages never ask whether a row is a
sample, so a "Sample" badge can only ever appear in the admin lists.
"""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef
from unfold.decorators import display

from .models import SampleRecord


def register(obj):
    SampleRecord.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(obj, for_concrete_model=True),
        object_id=obj.pk,
    )


def is_sample(obj):
    return SampleRecord.objects.filter(
        content_type=ContentType.objects.get_for_model(obj, for_concrete_model=True),
        object_id=obj.pk,
    ).exists()


def with_sample_flag(queryset):
    """Annotate `is_sample` in one subquery, for an admin list."""
    content_type = ContentType.objects.get_for_model(queryset.model, for_concrete_model=True)
    records = SampleRecord.objects.filter(content_type=content_type, object_id=OuterRef("pk"))
    return queryset.annotate(is_sample=Exists(records))


class SampleBadgeAdmin:
    """A "Sample" badge column on an admin list, for rows load_staging_samples made."""

    def get_queryset(self, request):
        return with_sample_flag(super().get_queryset(request))

    def get_list_display(self, request):
        return [*super().get_list_display(request), "sample_badge"]

    @display(description="Sample", label={"Sample": "warning"})
    def sample_badge(self, obj):
        return "Sample" if getattr(obj, "is_sample", False) else ""
