"""Status chips for admin lists: a field's value as a coloured label (Unfold's display).

Variants: success (rose-green, done or live), warning (amber, waiting), danger (red,
needs care), info (rose, informational); anything unlisted is a neutral chip.
"""

from unfold.decorators import display


def chip(field, labels, description="Status"):
    """A choices field shown by its label, coloured by `labels` ({label: variant})."""

    @display(description=description, ordering=field, label=labels)
    def show(self, obj):
        return getattr(obj, f"get_{field}_display")()

    show.__name__ = f"{field}_chip"
    return show


def flag(field, yes, no, description, yes_variant="success", no_variant="warning"):
    """A yes/no field shown as two words, e.g. Published / Draft."""

    @display(description=description, ordering=field, label={yes: yes_variant, no: no_variant})
    def show(self, obj):
        return yes if getattr(obj, field) else no

    show.__name__ = f"{field}_chip"
    return show


def image_preview(field):
    """A consent image (apps.core.consent_images) as staff see it, with whether it is shown."""
    from django.utils.html import format_html

    @display(description="Preview")
    def show(self, obj):
        image = getattr(obj, field)
        if not image:
            return "No image yet"
        state = (
            "Shown on the site"
            if obj.image_is_displayable(field)
            else (obj.image_hidden_reason(field) or "Hidden from the site")
        )
        return format_html(
            '<img src="{}" alt="" class="rose-preview"><p class="rose-help">{}</p>',
            image.url,
            state[:1].upper() + state[1:],
        )

    show.__name__ = f"{field}_preview"
    return show


class ButtonFields:
    """The call-to-action button on journal posts and classes, in plain words."""

    def get_form(self, request, obj=None, **kwargs):
        kwargs.setdefault("labels", {"cta_label": "Button label", "cta_url": "Button link"})
        kwargs.setdefault(
            "help_texts",
            {
                "cta_url": "A page on this site starting with /, an https:// address, or a "
                "mailto: link. Leave both empty for no button."
            },
        )
        return super().get_form(request, obj, **kwargs)
