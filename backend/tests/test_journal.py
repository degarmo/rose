from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.journal.models import Post, PostImage

pytestmark = pytest.mark.django_db


@pytest.fixture
def upload(gps_image_path):
    def make():
        return SimpleUploadedFile("x.jpg", gps_image_path.read_bytes(), content_type="image/jpeg")

    return make


@pytest.fixture
def make_post(upload):
    counter = {"n": 0}

    def make(images=1, **kwargs):
        counter["n"] += 1
        defaults = {
            "slug": f"post-{counter['n']}",
            "caption": "Caption",
            "is_published": True,
            "published_at": timezone.now() - timedelta(minutes=counter["n"]),
        }
        defaults.update(kwargs)
        post = Post.objects.create(**defaults)
        for order in range(images):
            PostImage.objects.create(post=post, image=upload(), image_alt="Alt", sort_order=order)
        return post

    return make


def test_caption_is_sanitized_with_breaks_and_links(make_post, api_client):
    make_post(slug="caption", caption="Line one\nSee https://example.org/x <script>x()</script>")
    html = api_client.get("/api/journal/posts/caption/").json()["caption_html"]
    assert "<br>" in html
    assert '<a href="https://example.org/x" rel="noopener noreferrer nofollow">' in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_pagination_with_cursor(make_post, api_client):
    for _ in range(15):
        make_post()
    first = api_client.get("/api/journal/posts/").json()
    assert len(first["results"]) == 12
    assert first["next"]
    cursor = first["next"].split("cursor=")[1]
    second = api_client.get(f"/api/journal/posts/?cursor={cursor}").json()
    assert len(second["results"]) == 3
    assert second["next"] is None
    seen = [p["slug"] for p in first["results"] + second["results"]]
    assert len(set(seen)) == 15
    assert seen == [f"post-{n}" for n in range(1, 16)]


def test_only_live_posts_listed(make_post, api_client):
    make_post(slug="live")
    make_post(slug="draft", is_published=False)
    make_post(slug="scheduled", published_at=timezone.now() + timedelta(days=1))
    slugs = [p["slug"] for p in api_client.get("/api/journal/posts/").json()["results"]]
    assert slugs == ["live"]
    assert api_client.get("/api/journal/posts/scheduled/").status_code == 404


def test_post_shape_and_author_display_name_only(make_post, make_user, api_client):
    author = make_user(is_staff=True, display_name="editor_one", email="editor@example.org")
    make_post(slug="shape", images=3, author=author)
    data = api_client.get("/api/journal/posts/shape/").json()
    assert set(data) == {"slug", "caption_html", "published_at", "author", "images", "event", "cta"}
    assert data["author"] == "editor_one"
    assert len(data["images"]) == 3
    assert set(data["images"][0]) == {"url", "alt"}
    assert "editor@example.org" not in str(data)


def test_event_link_beats_cta(make_post, make_event, api_client):
    event = make_event(slug="linked", title="Linked")
    make_post(slug="with-event", event=event, cta_label="Ignored", cta_url="/contact")
    make_post(slug="with-cta", cta_label="Read more", cta_url="/education")
    with_event = api_client.get("/api/journal/posts/with-event/").json()
    assert with_event["event"]["slug"] == "linked"
    assert with_event["cta"] is None
    with_cta = api_client.get("/api/journal/posts/with-cta/").json()
    assert with_cta["event"] is None
    assert with_cta["cta"] == {"label": "Read more", "url": "/education"}


def test_account_event_link_hidden_from_visitors(make_post, make_event, api_client):
    make_post(slug="p", event=make_event(audience="account"))
    assert api_client.get("/api/journal/posts/p/").json()["event"] is None


def test_withheld_images_never_serialized(make_post, api_client):
    post = make_post(slug="faces", images=2, is_published=False)
    PostImage.objects.filter(post=post, sort_order=1).update(image_faces_visible=True)
    Post.objects.filter(pk=post.pk).update(is_published=True)
    images = api_client.get("/api/journal/posts/faces/").json()["images"]
    assert len(images) == 1


def test_publish_blocked_on_unconsented_faces(make_post, upload):
    post = make_post(is_published=True)
    image = PostImage(post=post, image=upload(), image_alt="Group", image_faces_visible=True)
    with pytest.raises(ValidationError) as exc:
        image.full_clean()
    assert "image_consent_confirmed" in exc.value.message_dict

    image.image_consent_confirmed = True
    image.full_clean()

    draft = make_post(is_published=False)
    PostImage(post=draft, image=upload(), image_alt="Group", image_faces_visible=True).full_clean()


def test_alt_text_required(make_post, upload):
    post = make_post(is_published=False)
    with pytest.raises(ValidationError) as exc:
        PostImage(post=post, image=upload(), image_alt="  ").full_clean()
    assert "image_alt" in exc.value.message_dict


def test_publish_errors_count_and_consent(make_post):
    assert make_post(images=0, is_published=False).publish_errors() == [
        "A post needs between 1 and 10 images."
    ]
    too_many = make_post(images=11, is_published=False)
    assert "between 1 and 10" in too_many.publish_errors()[0]
    post = make_post(images=1)
    post.images.update(image_faces_visible=True)
    assert any("cannot be published" in e for e in post.publish_errors())
    assert make_post(images=2).publish_errors() == []


def test_cta_requires_label_and_url():
    post = Post(slug="x", caption="c", cta_label="Only a label")
    with pytest.raises(ValidationError):
        post.full_clean()


def test_admin_inline_blocks_publish_with_unconsented_faces(admin_client, upload):
    def payload(**extra):
        data = {
            "slug": "admin-post",
            "caption": "Caption",
            "published_at_0": timezone.localtime().strftime("%Y-%m-%d"),
            "published_at_1": "12:00:00",
            "is_published": "on",
            "author": "",
            "event": "",
            "cta_label": "",
            "cta_url": "",
            "images-TOTAL_FORMS": "1",
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "10",
            "images-0-image": upload(),
            "images-0-image_alt": "Two people",
            "images-0-image_faces_visible": "on",
            "images-0-sort_order": "0",
        }
        data.update(extra)
        return data

    response = admin_client.post("/admin/journal/post/add/", payload())
    assert response.status_code == 200
    assert "cannot be published" in response.content.decode()
    assert not Post.objects.exists()

    response = admin_client.post(
        "/admin/journal/post/add/", payload(**{"images-0-image_consent_confirmed": "on"})
    )
    assert response.status_code == 302
    assert Post.objects.get().images.count() == 1


def test_admin_requires_an_image_to_publish(admin_client):
    data = {
        "slug": "no-images",
        "caption": "Caption",
        "published_at_0": timezone.localtime().strftime("%Y-%m-%d"),
        "published_at_1": "12:00:00",
        "is_published": "on",
        "images-TOTAL_FORMS": "0",
        "images-INITIAL_FORMS": "0",
        "images-MIN_NUM_FORMS": "0",
        "images-MAX_NUM_FORMS": "10",
    }
    response = admin_client.post("/admin/journal/post/add/", data)
    assert response.status_code == 200
    assert "at least one image" in response.content.decode()
