"""One pattern for every image that can show a person.

`consented_image("hero_image", upload_to="events")` returns an abstract model
that adds four fields:

- `hero_image`: a SanitizedImageField (metadata stripped, renamed on upload)
- `hero_image_alt`: required whenever an image is set
- `hero_image_faces_visible`
- `hero_image_consent_confirmed`

Models inherit it, and `ConsentImageMixin.clean()` blocks publishing an image
that shows faces without confirmed consent. `consent_image_payload()` is the
render block: serializers use it, so a withheld image never leaves the API.
"""

from functools import cache

from django.core.exceptions import ValidationError
from django.db import models

from .images import RandomizedUploadTo, SanitizedImageField

ALT_REQUIRED = "Describe the image for people using screen readers."
CONSENT_REQUIRED = (
    "This image shows faces without confirmed consent, so it cannot be published. "
    "Confirm consent, untick faces visible, or remove the image."
)


def consent_image_field_names(model):
    """Names of every consented image field on a model or instance."""
    names = {field.name for field in model._meta.get_fields()}
    return [
        field.name
        for field in model._meta.get_fields()
        if isinstance(field, SanitizedImageField)
        and f"{field.name}_alt" in names
        and f"{field.name}_faces_visible" in names
        and f"{field.name}_consent_confirmed" in names
    ]


class ConsentImageMixin(models.Model):
    class Meta:
        abstract = True

    def consent_publish_state(self):
        """Whether the owning record is (or is about to be) public."""
        return bool(getattr(self, "is_published", False))

    def image_is_displayable(self, field):
        if not getattr(self, field):
            return False
        faces = getattr(self, f"{field}_faces_visible")
        return not faces or getattr(self, f"{field}_consent_confirmed")

    def image_hidden_reason(self, field):
        if not getattr(self, field):
            return "no image"
        if not self.image_is_displayable(field):
            return "faces visible without confirmed consent"
        return ""

    def consent_image_errors(self, published=None):
        published = self.consent_publish_state() if published is None else published
        errors = {}
        for field in consent_image_field_names(self):
            if not getattr(self, field):
                continue
            alt_required = getattr(self._meta.get_field(field), "consent_alt_required", True)
            if alt_required and not getattr(self, f"{field}_alt", "").strip():
                errors[f"{field}_alt"] = ALT_REQUIRED
            if published and not self.image_is_displayable(field):
                errors[f"{field}_consent_confirmed"] = CONSENT_REQUIRED
        return errors

    def clean(self):
        super().clean()
        errors = self.consent_image_errors()
        if errors:
            raise ValidationError(errors)


@cache
def consented_image(field, upload_to, required=False, storage=None, alt_required=True):
    """Build (once) the abstract model that adds `field` and its consent fields.

    `storage` is a callable returning a Storage (use private storage for anything
    members upload). `alt_required=False` keeps alt text encouraged but optional,
    which is how member uploads work.
    """
    image_kwargs = {
        "upload_to": RandomizedUploadTo(upload_to),
        "blank": not required,
        "help_text": "Metadata is stripped and the file renamed on upload.",
    }
    if storage is not None:
        image_kwargs["storage"] = storage
    image_field = SanitizedImageField(**image_kwargs)
    image_field.consent_alt_required = alt_required
    attrs = {
        "__module__": __name__,
        "Meta": type("Meta", (), {"abstract": True}),
        field: image_field,
        f"{field}_alt": models.CharField(
            max_length=200,
            blank=True,
            help_text=(
                "Required when an image is set. Describe what it shows."
                if alt_required
                else "Encouraged. Describe what it shows."
            ),
        ),
        f"{field}_faces_visible": models.BooleanField(
            default=False, help_text="Tick if any identifiable face is visible."
        ),
        f"{field}_consent_confirmed": models.BooleanField(
            default=False,
            help_text="Tick only when everyone visible has given written consent.",
        ),
    }
    class_name = f"Consented{''.join(part.title() for part in field.split('_'))}"
    return type(class_name, (ConsentImageMixin,), attrs)


def consent_image_payload(obj, field, request=None):
    """Serializer render block: `{url, alt}` or None when withheld."""
    if not obj.image_is_displayable(field):
        return None
    url = getattr(obj, field).url
    return {
        "url": request.build_absolute_uri(url) if request else url,
        "alt": getattr(obj, f"{field}_alt"),
    }


def consent_image_models(include_private=True):
    """Models using the pattern. Private (member) uploads are reviewed through
    moderation, not the public Image review page, so callers can leave them out."""
    from django.apps import apps

    return [
        model
        for model in apps.get_models()
        if issubclass(model, ConsentImageMixin)
        and consent_image_field_names(model)
        and (include_private or not getattr(model, "private_media", False))
    ]
