from django.db import migrations


def copy_to_audit_log(apps, schema_editor):
    """Move every moderation entry into core.AuditLog, keeping its original timestamp."""
    ModerationAction = apps.get_model("feed", "ModerationAction")
    AuditLog = apps.get_model("core", "AuditLog")
    for entry in ModerationAction.objects.order_by("pk"):
        copied = AuditLog.objects.create(
            category="moderation",
            action=entry.action,
            actor_id=entry.actor_id,
            actor_label=entry.actor_label,
            target_user_id=entry.target_user_id,
            target_label=entry.target_label,
            target_type=entry.target_type,
            target_ref=entry.target_ref,
            reason=entry.reason,
        )
        AuditLog.objects.filter(pk=copied.pk).update(created_at=entry.created_at)


def copy_back(apps, schema_editor):
    ModerationAction = apps.get_model("feed", "ModerationAction")
    AuditLog = apps.get_model("core", "AuditLog")
    for entry in AuditLog.objects.filter(category="moderation").order_by("pk"):
        copied = ModerationAction.objects.create(
            action=entry.action,
            actor_id=entry.actor_id,
            actor_label=entry.actor_label,
            target_user_id=entry.target_user_id,
            target_label=entry.target_label,
            target_type=entry.target_type,
            target_ref=entry.target_ref,
            reason=entry.reason,
        )
        ModerationAction.objects.filter(pk=copied.pk).update(created_at=entry.created_at)


class Migration(migrations.Migration):
    dependencies = [
        ("feed", "0002_default_guidelines"),
        ("core", "0001_audit_log"),
    ]

    operations = [
        migrations.RunPython(copy_to_audit_log, copy_back),
        migrations.DeleteModel(name="ModerationAction"),
    ]
