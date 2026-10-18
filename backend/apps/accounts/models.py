from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

# Fields that identify a real person. They are never serialized to any public
# or member-facing endpoint; tests/test_privacy.py enforces this.
PRIVATE_USER_FIELDS = frozenset(
    {"email", "legal_name", "phone", "password", "last_login", "is_superuser", "is_staff"}
)

display_name_validator = RegexValidator(
    regex=r"^[A-Za-z0-9_.-]{3,30}$",
    message="Use 3 to 30 letters, numbers, dots, dashes or underscores.",
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, display_name, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        if not display_name:
            raise ValueError("A display name is required.")
        user = self.model(
            email=self.normalize_email(email).lower(),
            display_name=display_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, display_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, display_name, password, **extra_fields)

    def create_superuser(self, email, display_name, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self._create_user(email, display_name, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)

    def feed_participants(self):
        return self.filter(feed_visible_q(author_field=None))


class User(AbstractBaseUser, PermissionsMixin):
    """Account holder. Logs in with email; is known to others by display_name."""

    email = models.EmailField("email address", unique=True)
    display_name = models.CharField(
        max_length=30,
        unique=True,
        validators=[display_name_validator],
        help_text="Public handle. The only identifier other people ever see.",
    )
    legal_name = models.CharField(
        max_length=200, blank=True, help_text="Private. Never shown to members or the public."
    )
    phone = models.CharField(
        max_length=32, blank=True, help_text="Private. Never shown to members or the public."
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name

    def get_full_name(self):
        return self.display_name


class Profile(models.Model):
    """Member-facing presence. Everything social is opt-in and off by default."""

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private (only me and staff)"
        MEMBERS = "members", "Signed-in members"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    participates_in_feed = models.BooleanField(
        default=False,
        help_text=(
            "When off, nothing this person has posted appears in the member feed. "
            "Posts are hidden, never deleted, and reappear if they opt back in."
        ),
    )
    visibility = models.CharField(
        max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    feed_status_changed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.display_name}"

    def set_feed_participation(self, participates):
        """Opt in or out. Opting out hides content; it never deletes it."""
        if self.participates_in_feed == participates:
            return
        self.participates_in_feed = participates
        self.feed_status_changed_at = timezone.now()
        self.save(update_fields=["participates_in_feed", "feed_status_changed_at", "updated_at"])


def feed_visible_q(author_field="author"):
    """Filter for content whose author currently participates in the feed.

    Every feed query must use this, e.g. `Post.objects.filter(feed_visible_q())`.
    Pass `author_field=None` to filter User rows directly.
    """
    prefix = f"{author_field}__" if author_field else ""
    return Q(**{f"{prefix}is_active": True, f"{prefix}profile__participates_in_feed": True})
