"""Print a fresh sign-in link for a staging preview, where email is not sent.

    python manage.py show_email_link someone@example.org --staff you@example.org
    python manage.py show_email_link someone@example.org --staff you@example.org --reset

Without --reset it prints the email verification link (for an address not yet confirmed);
with it, a password-reset link (valid for two hours). Preview mode only: once a real email
provider is set up the person gets the email itself. Only an active staff account may run
it, and each use is written to the audit log (without the address). The link is printed
here, in the shell, and never written to the log.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.accounts.tokens import reset_link, verification_link
from apps.core.models import AuditLog, audit
from apps.core.preview import preview_active


class Command(BaseCommand):
    help = "Print a verification or password-reset link. Staging preview only; staff; logged."

    def add_arguments(self, parser):
        parser.add_argument("address")
        parser.add_argument("--staff", required=True, help="Your staff account's email.")
        parser.add_argument("--reset", action="store_true", help="A password-reset link.")

    def handle(self, *args, address, staff, reset, **options):
        if not preview_active():
            raise CommandError("Only in a staging preview. Elsewhere the email itself is sent.")
        actor = User.objects.filter(email__iexact=staff, is_staff=True, is_active=True).first()
        if actor is None:
            raise CommandError("--staff must be an active staff account.")
        user = User.objects.filter(email__iexact=address, is_active=True).first()
        if user is None:
            raise CommandError("No active account has that address.")
        if reset:
            link, kind = reset_link(user), "password-reset"
        elif user.email_verified:
            raise CommandError("That address is already confirmed. Use --reset for a new password.")
        else:
            link, kind = verification_link(user), "verification"
        audit(
            AuditLog.Category.OPERATIONS,
            "preview_link_shown",
            actor,
            f"A preview {kind} link",
            "account",
            target_user=user,
        )
        self.stdout.write(link)
