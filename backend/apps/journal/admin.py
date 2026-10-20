from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from unfold.admin import ModelAdmin, TabularInline

from apps.core.admin_display import ButtonFields, flag

from .models import MAX_IMAGES, MIN_IMAGES, Post, PostImage


class PostImageFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        kept = [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
        ]
        if self.instance.is_published and len(kept) < MIN_IMAGES:
            raise ValidationError("A published post needs at least one image.")
        if len(kept) > MAX_IMAGES:
            raise ValidationError(f"A post can have at most {MAX_IMAGES} images.")


class PostImageInline(TabularInline):
    model = PostImage
    formset = PostImageFormSet
    extra = 1
    max_num = MAX_IMAGES
    fields = ("image", "image_alt", "image_faces_visible", "image_consent_confirmed", "sort_order")


@admin.register(Post)
class PostAdmin(ButtonFields, ModelAdmin):
    inlines = [PostImageInline]
    list_display = ("slug", "published_at", "is_published_chip", "image_count", "event")
    is_published_chip = flag("is_published", "Published", "Draft", "Status")
    list_filter = ("is_published",)
    search_fields = ("slug", "caption")
    autocomplete_fields = ("event",)
    fields = (
        "slug",
        "caption",
        "published_at",
        "is_published",
        "author",
        "event",
        "cta_label",
        "cta_url",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("images")

    @admin.display(description="Images")
    def image_count(self, obj):
        return len(obj.images.all())

    def get_changeform_initial_data(self, request):
        return {**super().get_changeform_initial_data(request), "author": request.user.pk}
