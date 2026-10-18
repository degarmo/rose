"""import_members: dry run by default, all or nothing, and quiet about emails."""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import AuditLog
from apps.memberships.emails import INVITE_SUBJECT
from apps.memberships.models import IdCheck, Membership

pytestmark = pytest.mark.django_db
HEADER = "email,display_name,tier_slug,period_end,id_checked\n"


@pytest.fixture
def csv_file(tmp_path, make_tier):
    make_tier(slug="monthly")
    future = (timezone.localdate() + timedelta(days=40)).isoformat()
    past = (timezone.localdate() - timedelta(days=5)).isoformat()

    def write(rows=None):
        rows = rows or [
            f"new.person@example.org,new_person,monthly,{future},yes",
            f"no.id@example.org,no_id_yet,monthly,{future},no",
            f"lapsed@example.org,lapsed_one,monthly,{past},yes",
        ]
        path = tmp_path / "members.csv"
        path.write_text(HEADER + "\n".join(rows) + "\n")
        return str(path)

    return write


def run(*args, **kwargs):
    from io import StringIO

    out = StringIO()
    call_command("import_members", *args, stdout=out, **kwargs)
    return out.getvalue()


def test_dry_run_writes_nothing(csv_file):
    output = run(csv_file())
    assert "3 rows: 3 new accounts" in output
    assert "Dry run" in output
    assert not User.objects.filter(email="new.person@example.org").exists()
    assert not Membership.objects.exists()
    assert mail.outbox == []


def test_commit_imports(csv_file):
    run(csv_file(), commit=True)
    new = Membership.objects.get(user__display_name="new_person")
    assert new.status == "active"
    assert timezone.localtime(new.current_period_end).date() == timezone.localdate() + timedelta(
        days=40
    )
    check = IdCheck.objects.get(membership=new)
    assert check.checked_by.display_name == "system_import" and not check.checked_by.is_active
    waiting = Membership.objects.get(user__display_name="no_id_yet")
    assert waiting.status == "pending_payment" and waiting.paid_awaiting_id_check
    assert Membership.objects.get(user__display_name="lapsed_one").status == "expired"
    user = new.user
    assert not user.has_usable_password() and user.email_verified
    assert AuditLog.objects.filter(action="import").count() == 3

    assert len(mail.outbox) == 3
    for message in mail.outbox:
        assert message.subject == INVITE_SUBJECT
        assert "/account/forgot" in message.body
        assert "token" not in message.body


def test_existing_account_gets_the_membership(csv_file, make_user):
    existing = make_user(email="new.person@example.org", display_name="already_here")
    run(csv_file(), commit=True)
    assert Membership.objects.get(user=existing).status == "active"
    assert "added to your account" in mail.outbox[0].body


def test_any_problem_means_nothing_is_written(csv_file, make_user):
    make_user(display_name="taken_name")
    path = csv_file(
        [
            "ok.person@example.org,fine_name,monthly,2099-01-01,yes",
            "bad-email,taken_name,missing-tier,01/02/2099,maybe",
        ]
    )
    with pytest.raises(CommandError):
        run(path, commit=True)
    assert not Membership.objects.exists()
    assert not User.objects.filter(email="ok.person@example.org").exists()


def test_emails_are_not_printed_with_debug_off(csv_file):
    path = csv_file(["secret.address@example.org,x,monthly,2099-01-01,yes"])
    from io import StringIO

    out = StringIO()
    with pytest.raises(CommandError):
        call_command("import_members", path, stdout=out)
    assert "line 2" in out.getvalue()
    assert "secret.address" not in out.getvalue()


def test_emails_are_printed_in_development(csv_file, settings):
    settings.DEBUG = True
    path = csv_file(["secret.address@example.org,x,monthly,2099-01-01,yes"])
    from io import StringIO

    out = StringIO()
    with pytest.raises(CommandError):
        call_command("import_members", path, stdout=out)
    assert "secret.address@example.org" in out.getvalue()


def test_wrong_columns_are_refused(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("email,name\na@example.org,x\n")
    with pytest.raises(CommandError, match="Expected columns"):
        run(str(path))
