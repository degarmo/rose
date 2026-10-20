from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.core.consent_images import consented_image
from apps.core.private_media import private_storage

BIO_MAX_LENGTH = 160

# Fields that identify a real person. They are never serialized to any public
# or member-facing endpoint; tests/test_privacy.py enforces this.
PRIVATE_USER_FIELDS = frozenset(
    {
        "email",
        "legal_name",
        "phone",
        "password",
        "last_login",
        "is_superuser",
        "is_staff",
        "email_verified_at",
        "session_epoch",
    }
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

    class Appearance(models.TextChoices):
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

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
    email_verified_at = models.DateTimeField(null=True, blank=True)
    # Part of the session hash: raising it ends every session this person has
    # ("Sign out everywhere", and any change to staff or active status).
    session_epoch = models.PositiveIntegerField(default=0, editable=False)
    # Light unless the person picks dark, whatever the device prefers.
    appearance = models.CharField(
        max_length=5, choices=Appearance.choices, default=Appearance.LIGHT
    )

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

    def _get_session_auth_hash(self, secret=None):
        key_salt = "apps.accounts.User.session_auth_hash"
        return salted_hmac(
            key_salt, f"{self.password}:{self.session_epoch}", secret=secret, algorithm="sha256"
        ).hexdigest()

    def sign_out_everywhere(self):
        User.objects.filter(pk=self.pk).update(session_epoch=F("session_epoch") + 1)
        self.refresh_from_db(fields=["session_epoch"])
        self.account_sessions.all().delete()

    @property
    def email_verified(self):
        return self.email_verified_at is not None

    def mark_email_verified(self):
        if self.email_verified_at is None:
            self.email_verified_at = timezone.now()
            self.save(update_fields=["email_verified_at"])


class Profile(
    consented_image("avatar", upload_to="avatars", storage=private_storage, alt_required=False)
):
    """Member-facing presence. Everything social is opt-in and off by default."""

    # Avatars are member uploads: private storage, reviewed through moderation.
    private_media = True

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

    # Entitlement. Staff grant it for comped members and volunteers; it stays
    # alongside paid membership once that exists.
    feed_access_granted = models.BooleanField(
        default=False, help_text="Lets this person use the member feed."
    )
    feed_access_granted_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", editable=False
    )
    feed_access_granted_at = models.DateTimeField(null=True, blank=True, editable=False)

    joined_feed_at = models.DateTimeField(null=True, blank=True, editable=False)
    bio = models.CharField(max_length=BIO_MAX_LENGTH, blank=True)
    avatar_key = models.CharField(max_length=32, blank=True, editable=False)
    hide_from_directory = models.BooleanField(
        default=True, help_text="Leave on to stay out of the member directory search."
    )
    always_show_sensitive = models.BooleanField(default=False)
    pronouns = models.CharField(
        max_length=40, blank=True, help_text="Optional. Shown on the profile only when filled in."
    )
    # Account preferences (Settings in the member app).
    calendar_details = models.BooleanField(
        default=False,
        help_text='Calendar files include the event name and place. Off: "Rose - Evening".',
    )
    email_event_reminders = models.BooleanField(default=True)
    email_membership_reminders = models.BooleanField(default=True)
    notify_likes = models.BooleanField(default=True)
    notify_comments = models.BooleanField(default=True)
    # When the person last opened Settings > Notices; anything newer counts as unread.
    notices_seen_at = models.DateTimeField(null=True, blank=True)
    # The switch-on of the feed's age check (SiteSettings.age_verification_switched_on_at)
    # this person was told about, by email and on Home and in Settings: at most once per
    # switch-on (apps.memberships.tasks.notify_age_check_switched_on).
    age_check_notice_at = models.DateTimeField(null=True, blank=True, editable=False)
    hidden_by_report = models.BooleanField(
        default=False, help_text="Avatar, bio and profile page hidden pending review."
    )

    feed_suspended_until = models.DateTimeField(null=True, blank=True)
    feed_banned_at = models.DateTimeField(null=True, blank=True)
    posting_cooldown_until = models.DateTimeField(null=True, blank=True)
    # Set and cleared only through member actions (apps/safety).
    events_suspended_until = models.DateTimeField(
        null=True, blank=True, editable=False, help_text="No RSVPs until then; flagged at the door."
    )
    do_not_admit_at = models.DateTimeField(
        null=True, blank=True, editable=False, help_text="Banned: the door desk shows Do not admit."
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.display_name}"

    def consent_publish_state(self):
        return self.participates_in_feed

    @property
    def is_feed_banned(self):
        return self.feed_banned_at is not None

    def is_feed_suspended(self, now=None):
        return bool(
            self.feed_suspended_until and self.feed_suspended_until > (now or timezone.now())
        )

    def is_events_suspended(self, now=None):
        return bool(
            self.events_suspended_until and self.events_suspended_until > (now or timezone.now())
        )

    def set_feed_participation(self, participates):
        """Opt in or out. Opting out hides content; it never deletes it."""
        if self.participates_in_feed == participates:
            return
        self.participates_in_feed = participates
        self.feed_status_changed_at = timezone.now()
        self.save(update_fields=["participates_in_feed", "feed_status_changed_at", "updated_at"])


class AccountSession(models.Model):
    """One signed-in session, for "where you are signed in" in Settings. Only a coarse
    device label (browser and system) and times; never an IP address. The session key
    is kept as a hash."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="account_sessions")
    key_hash = models.CharField(max_length=64, unique=True)
    device = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-last_seen_at"]

    def __str__(self):
        return f"Session on {self.device}"


def feed_visible_q(author_field="author"):
    """Filter for content whose author currently participates in the feed.

    Every feed query must use this, e.g. `Post.objects.filter(feed_visible_q())`.
    Pass `author_field=None` to filter User rows directly. Banned members'
    content is hidden too.
    """
    prefix = f"{author_field}__" if author_field else ""
    return Q(
        **{
            f"{prefix}is_active": True,
            f"{prefix}profile__participates_in_feed": True,
            f"{prefix}profile__feed_banned_at__isnull": True,
        }
    )
