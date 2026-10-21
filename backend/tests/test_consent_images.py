import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.core.consent_images import (
    ConsentImageMixin,
    consent_image_field_names,
    consent_image_models,
    consented_image,
)
from apps.core.images import SanitizedImageField
from apps.education.models import Opportunity
from apps.events.models import Event
from apps.journal.models import PostImage


def test_factory_builds_the_four_fields_once():
    mixin = consented_image("hero_image", upload_to="education")
    assert mixin is consented_image("hero_image", upload_to="education")
    assert mixin._meta.abstract
    names = {field.name for field in mixin._meta.get_fields()}
    assert names == {
        "hero_image",
        "hero_image_alt",
        "hero_image_faces_visible",
        "hero_image_consent_confirmed",
        # Public images also record their size, for srcset and layout.
        "hero_image_width",
        "hero_image_height",
    }


def test_private_images_get_no_size_variants():
    from apps.core.private_media import private_storage

    mixin = consented_image(
        "avatar", upload_to="avatars", storage=private_storage, alt_required=False
    )
    names = {field.name for field in mixin._meta.get_fields()}
    assert "avatar_width" not in names
    assert mixin._meta.get_field("avatar").variant_widths == ()


@pytest.mark.django_db
def test_public_uploads_get_variants_and_sizes(settings, tmp_path):
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    from apps.core.consent_images import consent_image_payload
    from apps.education.models import Opportunity

    settings.MEDIA_ROOT = tmp_path
    buffer = BytesIO()
    Image.new("RGB", (2000, 1000), (80, 20, 30)).save(buffer, format="JPEG")
    item = Opportunity(title="Class", slug="class", summary="s", body="b", is_published=True)
    item.hero_image = SimpleUploadedFile("hero.jpg", buffer.getvalue(), content_type="image/jpeg")
    item.hero_image_alt = "A red square"
    item.save()
    assert (item.hero_image_width, item.hero_image_height) == (2000, 1000)
    stem = item.hero_image.name.rsplit(".", 1)[0]
    for width in (640, 1280):
        with Image.open(tmp_path / f"{stem}-{width}w.webp") as variant:
            assert variant.size == (width, width // 2)
    payload = consent_image_payload(item, "hero_image")
    assert payload["width"] == 2000 and payload["height"] == 1000
    assert payload["srcset"].count("w,") == 2 and payload["srcset"].endswith(" 2000w")


def test_every_image_model_uses_the_pattern():
    from apps.accounts.models import Profile
    from apps.feed.models import FeedImage
    from apps.pages.models import SiteImage, StaffProfile

    assert set(consent_image_models()) == {
        Opportunity,
        Event,
        PostImage,
        Profile,
        FeedImage,
        StaffProfile,
        SiteImage,
    }
    # Member uploads are private and reviewed in moderation, not on the public review page.
    public = {Opportunity, Event, PostImage, StaffProfile, SiteImage}
    assert set(consent_image_models(include_private=False)) == public
    for model in consent_image_models():
        assert issubclass(model, ConsentImageMixin)
    assert consent_image_field_names(PostImage) == ["image"]


def test_no_unmanaged_image_fields_anywhere():
    from django.apps import apps

    for model in apps.get_models():
        for field in model._meta.get_fields():
            if isinstance(field, SanitizedImageField):
                assert field.name in consent_image_field_names(model), (model, field.name)


@pytest.mark.django_db
def test_opportunity_rules(gps_image_path):
    upload = SimpleUploadedFile("x.jpg", gps_image_path.read_bytes(), content_type="image/jpeg")
    opportunity = Opportunity(
        title="T", slug="t", summary="s", body="b", hero_image=upload, is_published=True
    )
    with pytest.raises(ValidationError) as exc:
        opportunity.full_clean()
    assert "hero_image_alt" in exc.value.message_dict

    opportunity.hero_image_alt = "Candles"
    opportunity.hero_image_faces_visible = True
    with pytest.raises(ValidationError) as exc:
        opportunity.full_clean()
    assert "hero_image_consent_confirmed" in exc.value.message_dict

    opportunity.is_published = False
    opportunity.full_clean()


@pytest.mark.django_db(transaction=True)
def test_opportunity_migration_keeps_image_data():
    executor = MigrationExecutor(connection)
    executor.migrate([("education", "0001_initial")])
    old_apps = executor.loader.project_state([("education", "0001_initial")]).apps
    OldOpportunity = old_apps.get_model("education", "Opportunity")
    OldOpportunity.objects.create(
        title="Kept",
        slug="kept",
        summary="s",
        body="b",
        hero_image="education/abc.webp",
        hero_image_alt="Candlelight",
        hero_image_faces_visible=True,
        hero_image_consent_confirmed=True,
    )

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())

    kept = Opportunity.objects.get(slug="kept")
    assert kept.hero_image.name == "education/abc.webp"
    assert kept.hero_image_alt == "Candlelight"
    assert kept.hero_image_faces_visible and kept.hero_image_consent_confirmed
