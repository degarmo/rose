"""The development runserver: migrations first, loud warnings, and the empty-tiers notice."""

from io import StringIO

import pytest
from django.core.management import call_command, get_commands
from django.core.management.color import no_style
from django.db import connection
from django.db.migrations.loader import MigrationLoader

from apps.core.management.commands import runserver

pytestmark = pytest.mark.django_db(transaction=True)


def unapply_latest_pages_migration():
    """Roll back the newest pages migration and return its name."""
    loader = MigrationLoader(connection)
    (latest,) = loader.graph.leaf_nodes("pages")
    (parent,) = loader.graph.node_map[latest].parents
    call_command("migrate", "pages", parent.key[1], verbosity=0)
    return latest[1]


def outputs():
    return StringIO(), StringIO()


def test_the_project_runserver_is_the_one_used():
    assert get_commands()["runserver"] == "apps.core"


def test_unapplied_migrations_are_applied_before_starting():
    name = unapply_latest_pages_migration()
    assert runserver.pending_migrations() == [("pages", name)]
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
    name = unapply_latest_pages_migration()

    def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(runserver, "call_command", broken)
    stdout, stderr = outputs()
    assert runserver.migrate_for_development(stdout, stderr, no_style()) == 1
    assert "Migrations failed: boom" in stderr.getvalue()
    assert f"WARNING: 1 migration(s) are still unapplied (pages.{name})" in stderr.getvalue()
    call_command("migrate", "pages", verbosity=0)


def test_an_empty_tier_table_is_reported(make_tier):
    stderr = StringIO()
    runserver.warn_if_no_tiers(stderr, no_style())
    assert "No membership tiers are on offer" in stderr.getvalue()
    make_tier()
    stderr = StringIO()
    runserver.warn_if_no_tiers(stderr, no_style())
    assert stderr.getvalue() == ""
