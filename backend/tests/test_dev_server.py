"""The development runserver: migrations first, loud warnings, and the empty-tiers notice."""

from io import StringIO

import pytest
from django.core.management import call_command, get_commands
from django.core.management.color import no_style

from apps.core.management.commands import runserver

pytestmark = pytest.mark.django_db(transaction=True)


def outputs():
    return StringIO(), StringIO()


def test_the_project_runserver_is_the_one_used():
    assert get_commands()["runserver"] == "apps.core"


def test_unapplied_migrations_are_applied_before_starting():
    call_command("migrate", "pages", "0003", verbosity=0)
    assert ("pages", "0004_membership_is_a_page") in runserver.pending_migrations()
    stdout, stderr = outputs()
    assert runserver.migrate_for_development(stdout, stderr, no_style()) == 0
    assert runserver.pending_migrations() == []
    assert "Applying 1 unapplied migration(s)" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_nothing_happens_when_up_to_date():
    stdout, stderr = outputs()
    assert runserver.migrate_for_development(stdout, stderr, no_style()) == 0
    assert stdout.getvalue() == stderr.getvalue() == ""


def test_a_failed_migration_is_reported_loudly(monkeypatch):
    call_command("migrate", "pages", "0003", verbosity=0)

    def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(runserver, "call_command", broken)
    stdout, stderr = outputs()
    assert runserver.migrate_for_development(stdout, stderr, no_style()) == 1
    assert "Migrations failed: boom" in stderr.getvalue()
    assert "WARNING: 1 migration(s) are still unapplied (pages.0004_membership_is_a_page)" in (
        stderr.getvalue()
    )
    call_command("migrate", "pages", verbosity=0)


def test_an_empty_tier_table_is_reported(make_tier):
    stderr = StringIO()
    runserver.warn_if_no_tiers(stderr, no_style())
    assert "No membership tiers are on offer" in stderr.getvalue()
    make_tier()
    stderr = StringIO()
    runserver.warn_if_no_tiers(stderr, no_style())
    assert stderr.getvalue() == ""
