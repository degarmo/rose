"""Send a neutral test message through the configured email backend.

    python manage.py send_test_email someone@example.org --staff you@example.org

Only an active staff account may send it, and each send is written to the
audit log (without the recipient's address).
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.core.email import send_neutral_mail
from apps.core.models import AuditLog, audit

SUBJECT = "Test message"
BODY = "This is a test message to confirm that email is set up correctly.\n\nNo action is needed.\n"


class Command(BaseCommand):
    help = "Send a neutral test email. Staff only; logged."

    def add_arguments(self, parser):
        parser.add_argument("address")
        parser.add_argument("--staff", required=True, help="Your staff account's email.")

    def handle(self, *args, address, staff, **options):
        sender = User.objects.filter(email__iexact=staff, is_staff=True, is_active=True).first()
        if sender is None:
            raise CommandError("--staff must be an active staff account.")
        send_neutral_mail(SUBJECT, BODY, to=[address])
        audit(
            AuditLog.Category.OPERATIONS,
            "test_email_sent",
            sender,
            f"Test email through {settings.EMAIL_PROVIDER}",
            "email",
        )
        self.stdout.write(
            self.style.SUCCESS(f"Sent a test message through {settings.EMAIL_PROVIDER}.")
        )
