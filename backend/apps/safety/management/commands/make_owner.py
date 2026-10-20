"""Create or upgrade the owner's account: a superuser holding the Admin role.

    python manage.py make_owner owner@example.org
    python manage.py make_owner owner@example.org --display-name the_owner

Idempotent: run it again and nothing changes except what is missing. A new account
asks for a password (or takes DJANGO_SUPERUSER_PASSWORD); an existing one keeps its own.
"""

import getpass
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User, display_name_validator

from ... import roles
from ...owner import prepare_owner


class Command(BaseCommand):
    help = "Create or upgrade a superuser with the Admin role, ready for the staff section."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument(
            "--display-name",
            help="For a new account. Defaults to the part of the email before the @.",
        )

    def _password(self):
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if password is None:
            password = getpass.getpass("Password for the new account: ")
            if password != getpass.getpass("Again: "):
                raise CommandError("The passwords do not match.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        return password

    def _display_name(self, email, wanted):
        name = wanted or email.split("@")[0].replace(".", "_").replace("-", "_")[:30]
        try:
            display_name_validator(name)
        except ValidationError as exc:
            raise CommandError(f"Display name {name!r}: {' '.join(exc.messages)}") from exc
        if User.objects.filter(display_name__iexact=name).exists():
            raise CommandError(f"The display name {name!r} is taken. Pass --display-name.")
        return name

    def handle(self, *args, email, display_name=None, **options):
        email = email.strip()
        if "@" not in email:
            raise CommandError("Give an email address.")
        user = User.objects.filter(email__iexact=email).first()
        created = user is None
        if created:
            name = self._display_name(email, display_name)
            password = self._password()
        with transaction.atomic():
            if created:
                user = User.objects.create_superuser(
                    email=email, display_name=name, password=password
                )
            else:
                user.is_superuser = True
                user.is_staff = True
                user.is_active = True
                user.save(update_fields=["is_superuser", "is_staff", "is_active"])
            roles.set_role(user, roles.ADMIN)
            prepare_owner(user)

        verb = "Created" if created else "Upgraded"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} {user.email} ({user.display_name}): superuser, Admin role.")
        )
        self.stdout.write(
            "\nNext steps:\n"
            "  1. Log in on the website with this email. You land on the staff dashboard.\n"
            "  2. The staff section asks for the two-step login. The first time, it sets up\n"
            "     an authenticator app (scan the code, then keep the ten backup codes safe).\n"
            "  3. After that, Staff in the account menu leads to the dashboard, reports, the\n"
            "     door desk, the member app and the Django admin.\n"
            "  4. The member feed opens once your own ID check is recorded at the door desk,\n"
            "     with a second team member as witness, as it is for everyone.\n"
            "  For local development only, DEV_SKIP_STAFF_2FA=true (with DEBUG on) skips\n"
            "  step 2; staging and production refuse to start with it set.\n"
        )
