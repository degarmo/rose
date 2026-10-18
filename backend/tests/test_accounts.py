import pytest
from django.contrib.auth.hashers import identify_hasher
from django.core.exceptions import ValidationError

from apps.accounts.models import Profile, User, feed_visible_q

pytestmark = pytest.mark.django_db


def test_create_user_uses_email_login_and_normalizes(member):
    assert member.email == "private.person@example.org"
    assert User.USERNAME_FIELD == "email"
    assert member.check_password("a-long-test-password-123")
    assert str(member) == "velvet_fox"
    assert member.get_full_name() == "velvet_fox"
    assert member.get_short_name() == "velvet_fox"


def test_lookup_by_email_is_case_insensitive(member):
    assert User.objects.get_by_natural_key("PRIVATE.person@example.org") == member


def test_create_user_requires_email_and_display_name():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", display_name="someone", password="x")
    with pytest.raises(ValueError):
        User.objects.create_user(email="a@example.org", display_name="", password="x")


def test_create_superuser_sets_flags():
    admin = User.objects.create_superuser(
        email="admin@example.org", display_name="house_admin", password="another-long-pass-1"
    )
    assert admin.is_staff and admin.is_superuser


def test_passwords_use_argon2(member):
    assert identify_hasher(member.password).algorithm == "argon2"


def test_display_name_validation():
    user = User(email="v@example.org", display_name="no spaces allowed!")
    with pytest.raises(ValidationError) as exc:
        user.full_clean()
    assert "display_name" in exc.value.message_dict


def test_profile_is_created_private_and_opted_out(member):
    profile = member.profile
    assert profile.participates_in_feed is False
    assert profile.visibility == Profile.Visibility.PRIVATE
    assert profile.feed_status_changed_at is None
    assert str(profile) == "Profile for velvet_fox"


def test_feed_participation_is_reversible(member):
    profile = member.profile
    profile.set_feed_participation(True)
    profile.refresh_from_db()
    assert profile.participates_in_feed is True
    first_change = profile.feed_status_changed_at
    assert first_change is not None

    profile.set_feed_participation(False)
    profile.refresh_from_db()
    assert profile.participates_in_feed is False
    assert profile.feed_status_changed_at >= first_change
    assert User.objects.filter(pk=member.pk).exists()


def test_setting_same_feed_status_is_a_no_op(member):
    member.profile.set_feed_participation(False)
    member.profile.refresh_from_db()
    assert member.profile.feed_status_changed_at is None


def test_feed_visibility_filter_hides_opted_out_and_inactive_users(member):
    opted_in = User.objects.create_user(
        email="in@example.org", display_name="opted_in", password="pass-word-long-1"
    )
    opted_in.profile.set_feed_participation(True)
    inactive = User.objects.create_user(
        email="gone@example.org", display_name="inactive", password="pass-word-long-1"
    )
    inactive.profile.set_feed_participation(True)
    inactive.is_active = False
    inactive.save()

    assert list(User.objects.feed_participants()) == [opted_in]

    opted_in.profile.set_feed_participation(False)
    assert list(User.objects.feed_participants()) == []

    member.profile.set_feed_participation(True)
    assert list(User.objects.feed_participants()) == [member]


def test_feed_visible_q_targets_author_relation():
    q = feed_visible_q()
    assert dict(q.children) == {
        "author__is_active": True,
        "author__profile__participates_in_feed": True,
    }
