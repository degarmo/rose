"""Import existing members from a CSV file.

Columns: email, display_name, tier_slug, period_end (YYYY-MM-DD), id_checked
(yes/no). Nothing is written without --commit, and nothing at all is written
if any row has a problem. Email addresses are never printed unless DEBUG is on.
"""

import csv
from dataclasses import dataclass
from datetime import date, datetime, time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, display_name_validator
from apps.core.models import AuditLog, audit

from ...emails import send_import_invite
from ...models import IdCheck, Membership, Tier

COLUMNS = ["email", "display_name", "tier_slug", "period_end", "id_checked"]
TRUE = {"yes", "y", "true", "1"}
FALSE = {"no", "n", "false", "0", ""}
SYSTEM_EMAIL = "system.import@localhost.invalid"
SYSTEM_NAME = "system_import"


@dataclass
class Row:
    line: int
    email: str
    display_name: str
    tier: Tier
    period_end: datetime
    id_checked: bool
    user: User | None


def system_user():
    """The inactive account that imported ID checks are recorded against."""
    user = User.objects.filter(email=SYSTEM_EMAIL).first()
    if user is None:
        user = User.objects.create_user(email=SYSTEM_EMAIL, display_name=SYSTEM_NAME)
        user.set_unusable_password()
        user.is_active = False
        user.save()
    return user


class Command(BaseCommand):
    help = "Import existing members from CSV. Dry run unless --commit is given."

    def add_arguments(self, parser):
        parser.add_argument("csv_path")
        parser.add_argument("--commit", action="store_true", help="Write the import.")

    def who(self, row_or_email, line):
        email = row_or_email if isinstance(row_or_email, str) else row_or_email.email
        return f"line {line} ({email})" if settings.DEBUG else f"line {line}"

    def handle(self, *args, csv_path, commit, **options):
        try:
            with open(csv_path, newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                header = [h.strip().lower() for h in (reader.fieldnames or [])]
                if sorted(header) != sorted(COLUMNS):
                    raise CommandError(f"Expected columns: {', '.join(COLUMNS)}")
                raw = [
                    (n, {k.strip().lower(): (v or "").strip() for k, v in r.items()})
                    for n, r in enumerate(reader, start=2)
                ]
        except OSError as exc:
            raise CommandError(f"Could not read {csv_path}: {exc.strerror}") from exc

        rows, errors = self.validate(raw)
        new_accounts = sum(1 for r in rows if r.user is None)
        self.stdout.write(
            f"{len(raw)} rows: {new_accounts} new accounts, "
            f"{len(rows) - new_accounts} existing accounts, {len(errors)} problems."
        )
        for message in errors:
            self.stdout.write(self.style.WARNING(f"  {message}"))
        if errors:
            raise CommandError("Nothing was imported. Fix the rows above and run again.")
        if not commit:
            self.stdout.write("Dry run: nothing was written. Run again with --commit to import.")
            return
        self.write(rows)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(rows)} memberships."))

    def validate(self, raw):
        rows, errors, seen_emails, seen_names = [], [], set(), set()
        tiers = Tier.objects.all() if settings.DEBUG else Tier.objects.filter(is_placeholder=False)
        tiers = {t.slug: t for t in tiers}
        for line, data in raw:
            email = User.objects.normalize_email(data["email"]).lower()
            problems = []
            try:
                validate_email(email)
            except ValidationError:
                problems.append("email is not valid")
            if email in seen_emails:
                problems.append("email appears twice in the file")
            seen_emails.add(email)
            user = User.objects.filter(email__iexact=email).first() if email else None
            name = data["display_name"]
            if user is None:
                try:
                    display_name_validator(name)
                except ValidationError:
                    problems.append("display_name must be 3 to 30 letters, numbers, . - or _")
                if User.objects.filter(display_name__iexact=name).exists():
                    problems.append("display_name is taken")
                if name.lower() in seen_names:
                    problems.append("display_name appears twice in the file")
                seen_names.add(name.lower())
            elif Membership.objects.non_terminal().filter(user=user).exists():
                problems.append("this account already has an open membership")
            tier = tiers.get(data["tier_slug"])
            if tier is None:
                problems.append(f"unknown tier_slug {data['tier_slug']!r}")
            try:
                end_date = date.fromisoformat(data["period_end"])
                period_end = timezone.make_aware(datetime.combine(end_date, time(23, 59)))
            except ValueError:
                problems.append("period_end must be YYYY-MM-DD")
                period_end = None
            flag = data["id_checked"].lower()
            if flag not in TRUE | FALSE:
                problems.append("id_checked must be yes or no")
            if problems:
                errors.append(f"{self.who(email, line)}: {'; '.join(problems)}")
                continue
            rows.append(Row(line, email, name, tier, period_end, flag in TRUE, user))
        return rows, errors

    @transaction.atomic
    def write(self, rows):
        system = system_user()
        now = timezone.now()
        for row in rows:
            new_account = row.user is None
            user = row.user or User.objects.create_user(
                email=row.email, display_name=row.display_name
            )
            if new_account:
                user.set_unusable_password()
                # They received this address from us before; it is how they were a member.
                user.email_verified_at = now
                user.save()
            membership = Membership(
                user=user,
                tier=row.tier,
                source=Membership.Source.MANUAL,
                current_period_start=now,
                current_period_end=row.period_end,
            )
            if row.period_end <= now:
                membership.end(Membership.Status.EXPIRED, now)
            elif row.id_checked:
                membership.status = Membership.Status.ACTIVE
            else:
                # Paid up, but no ID seen yet: the door desk activates after the check.
                membership.status = Membership.Status.PENDING_PAYMENT
                membership.paid_awaiting_id_check = True
            membership.save()
            if row.id_checked:
                IdCheck.objects.create(membership=membership, checked_by=system)
            audit(
                AuditLog.Category.DOOR_DESK,
                "import",
                None,
                f"Membership {membership.reference_code} ({user.display_name})",
                "membership",
                target_user=user,
                target_ref=membership.reference_code,
                reason="Imported from CSV",
            )
            transaction.on_commit(lambda m=membership, n=new_account: send_import_invite(m, n))
