"""Load drafted site copy from YAML into the database.

One file per page or section, in SITE_CONTENT_DIR (default: /content). Each
file starts with a status and the source pages it was drafted from:

    status: draft - needs club approval
    source_url:
      - https://example.org/about
    page: about                  # where the copy below goes (PageContent)
    copy:                        # nested keys become "hero.title", "steps.1.body"
      hero:
        title: Plain text
        lede:
          rich: <p>Formatted text</p>
    site_settings: {hours_text: ..., ...}
    social_links: [{label: Discord, url: https://...}]
    faqs: [{slug: parking, question: ..., answer: ...}]
    staff: [{slug: venus, display_name: Venus, role_title: ..., bio: ...}]
    tiers: [{slug: rose, name: ..., price_cents: 4000, allowed_event_tags: [community]}]
    redirects: [{from: /old-path, to: /new-path}]

Loading is idempotent: rows are matched on slug (or page and key, or old path)
and updated. Nothing is ever deleted.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.models import AuditLog, audit
from apps.core.text import sanitize_rich_text
from apps.events.models import EventTag
from apps.memberships.models import Tier

from .models import FAQItem, PageContent, Redirect, SiteSettings, SocialLink, StaffProfile

SITE_SETTINGS_FIELDS = {
    "tagline",
    "hours_text",
    "address_text",
    "phone_text",
    "directions_text",
    "contact_email",
    "quick_exit_url",
    "nonprofit_status_text",
    "check_payable_to",
    "mailing_address",
    "legal_name",
    "ein",
}
TIER_FIELDS = {
    "name",
    "description",
    "perks",
    "price_cents",
    "interval",
    "duration_days",
    "renews",
    "events_per_month",
    "guests_included_per_event",
    "guest_discount",
    "premium_discord",
    "event_access",
    "grants_feed_access",
    "grants_members_events",
    "grants_members_education",
    "is_featured",
    "is_guest_pass",
    "is_active",
    "sort_order",
}
KNOWN_SECTIONS = {
    "status",
    "source_url",
    "page",
    "copy",
    "site_settings",
    "social_links",
    "faqs",
    "staff",
    "tiers",
    "redirects",
    "notes",
}


class ContentError(Exception):
    """A file cannot be loaded. Nothing is written when any file has one."""


@dataclass
class ContentFile:
    path: Path
    data: dict

    @property
    def name(self):
        return self.path.name

    @property
    def status(self):
        return str(self.data.get("status", ""))

    @property
    def is_draft(self):
        return self.status.strip().lower().startswith("draft")


@dataclass
class Report:
    counts: dict = field(default_factory=dict)

    def add(self, file_name, outcome):
        per_file = self.counts.setdefault(file_name, {"created": 0, "updated": 0, "unchanged": 0})
        per_file[outcome] += 1

    def lines(self):
        for name, c in self.counts.items():
            yield f"{name}: {c['created']} new, {c['updated']} changed, {c['unchanged']} unchanged"


def read_files(directory, names=None):
    directory = Path(directory)
    if names:
        paths = [directory / name if not Path(name).is_absolute() else Path(name) for name in names]
    else:
        paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise ContentError(f"No .yaml files found in {directory}.")
    texts = []
    for path in paths:
        try:
            texts.append((path, path.read_text(encoding="utf-8")))
        except OSError as exc:
            raise ContentError(f"{path.name}: cannot be read ({exc}).") from exc
    return parse_texts(texts)


def parse_texts(texts):
    """[(path or name, YAML text)] -> validated ContentFiles. Used for uploads too."""
    files = []
    for path, text in texts:
        path = Path(path)
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ContentError(f"{path.name}: cannot be read ({exc}).") from exc
        if not isinstance(data, dict):
            raise ContentError(f"{path.name}: expected a mapping at the top level.")
        files.append(ContentFile(path, data))
    for content in files:
        validate_shape(content)
    return files


def validate_shape(content):
    data = content.data
    if not content.status:
        raise ContentError(f"{content.name}: missing `status`.")
    sources = data.get("source_url")
    if not isinstance(sources, list) or not all(isinstance(s, str) for s in sources):
        raise ContentError(f"{content.name}: `source_url` must be a list of addresses.")
    unknown = set(data) - KNOWN_SECTIONS
    if unknown:
        raise ContentError(f"{content.name}: unknown sections {', '.join(sorted(unknown))}.")
    if "copy" in data and not data.get("page"):
        raise ContentError(f"{content.name}: `copy` needs a `page` to go on.")
    for section in ("social_links", "faqs", "staff", "tiers", "redirects"):
        items = data.get(section, [])
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise ContentError(f"{content.name}: `{section}` must be a list of mappings.")
    settings_section = data.get("site_settings", {})
    if not isinstance(settings_section, dict):
        raise ContentError(f"{content.name}: `site_settings` must be a mapping.")
    unknown = set(settings_section) - SITE_SETTINGS_FIELDS
    if unknown:
        raise ContentError(f"{content.name}: unknown site settings {', '.join(sorted(unknown))}.")


def flatten_copy(value, prefix=""):
    """Yield (key, text, format) for a nested copy section."""
    if isinstance(value, dict) and set(value) == {"rich"}:
        # Sanitised here as on save, so an unchanged value compares equal next time.
        yield prefix, sanitize_rich_text(str(value["rich"]).strip()), PageContent.Format.RICH
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from flatten_copy(child, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value, start=1):
            yield from flatten_copy(child, f"{prefix}.{index}")
    elif value is None:
        yield prefix, "", PageContent.Format.PLAIN
    else:
        yield prefix, str(value).strip(), PageContent.Format.PLAIN


def _save(report, file_name, obj, values, created, partial=False):
    """Set values and save if anything changed. `partial` validates only the
    fields given, for records (site settings) that a file fills in piece by piece."""
    changed = created
    for name, value in values.items():
        if getattr(obj, name) != value:
            setattr(obj, name, value)
            changed = True
    if not changed:
        report.add(file_name, "unchanged")
        return
    exclude = [f.name for f in obj._meta.fields if f.name not in values] if partial else None
    try:
        obj.full_clean(exclude=exclude)
    except ValidationError as exc:
        raise ContentError(f"{file_name}: {obj!r} is not valid: {exc.messages}") from exc
    obj.save()
    report.add(file_name, "created" if created else "updated")


def _upsert(report, file_name, model, lookup, values):
    obj = model.objects.filter(**lookup).first()
    created = obj is None
    if created:
        obj = model(**lookup)
    _save(report, file_name, obj, values, created)
    return obj


def apply_file(content, report):
    data = content.data
    name = content.name

    if data.get("copy"):
        page = str(data["page"])
        for key, text, fmt in flatten_copy(data["copy"]):
            _upsert(
                report,
                name,
                PageContent,
                {"page": page, "key": key},
                {"value": text, "format": fmt},
            )

    if data.get("site_settings"):
        site = SiteSettings.load()
        values = {
            k: ("" if v is None else str(v).strip()) for k, v in data["site_settings"].items()
        }
        _save(report, name, site, values, created=False, partial=True)

    if data.get("social_links"):
        site = SiteSettings.load()
        for index, item in enumerate(data["social_links"], start=1):
            _upsert(
                report,
                name,
                SocialLink,
                {"settings": site, "url": str(item["url"])},
                {"label": str(item["label"]), "sort_order": item.get("sort_order", index * 10)},
            )

    for index, item in enumerate(data.get("faqs", []), start=1):
        _require(name, item, ("slug", "question", "answer"))
        _upsert(
            report,
            name,
            FAQItem,
            {"slug": item["slug"]},
            {
                "question": str(item["question"]).strip(),
                "answer": str(item["answer"]).strip(),
                "sort_order": item.get("sort_order", index * 10),
                "is_published": item.get("is_published", True),
            },
        )

    for index, item in enumerate(data.get("staff", []), start=1):
        _require(name, item, ("slug", "display_name", "role_title"))
        _upsert(
            report,
            name,
            StaffProfile,
            {"slug": item["slug"]},
            {
                "display_name": str(item["display_name"]).strip(),
                "role_title": str(item["role_title"]).strip(),
                "bio": str(item.get("bio") or "").strip(),
                "sort_order": item.get("sort_order", index * 10),
                "is_published": item.get("is_published", True),
            },
        )

    for item in data.get("tiers", []):
        _require(name, item, ("slug",))
        values = {k: v for k, v in item.items() if k in TIER_FIELDS}
        unknown = set(item) - TIER_FIELDS - {"slug", "allowed_event_tags"}
        if unknown:
            raise ContentError(f"{name}: tier {item['slug']} has unknown fields {sorted(unknown)}.")
        tier = Tier.objects.filter(slug=item["slug"]).first()
        if tier is None and not {"name", "price_cents", "interval"} <= set(values):
            raise ContentError(
                f"{name}: tier {item['slug']} does not exist yet; a new tier needs a name, "
                "an interval and a price."
            )
        _upsert(report, name, Tier, {"slug": item["slug"]}, values)
        if "allowed_event_tags" in item:
            slugs = [str(slug) for slug in item["allowed_event_tags"] or []]
            tags = list(EventTag.objects.filter(slug__in=slugs))
            missing = sorted(set(slugs) - {tag.slug for tag in tags})
            if missing:
                raise ContentError(
                    f"{name}: tier {item['slug']} names unknown event tags {missing}."
                )
            Tier.objects.get(slug=item["slug"]).allowed_event_tags.set(tags)

    for item in data.get("redirects", []):
        _require(name, item, ("from", "to"))
        target = str(item["to"]).strip()
        _upsert(
            report, name, Redirect, {"old_path": _normalised(item["from"])}, {"new_path": target}
        )


def _normalised(path):
    from .models import normalise_path

    return normalise_path(str(path))


def _require(file_name, item, keys):
    missing = [key for key in keys if not item.get(key)]
    if missing:
        raise ContentError(f"{file_name}: an entry is missing {', '.join(missing)}: {item!r}")


def load(files, commit=False):
    """Apply every file in one transaction. A dry run rolls everything back."""
    report = Report()
    with transaction.atomic():
        for content in files:
            apply_file(content, report)
        if not commit:
            transaction.set_rollback(True)
    return report


def load_guarded(contents, commit=False, allow_draft=False, actor=None):
    """The production draft guard, the load, and the audit entries, in one place.

    In production, files still marked as drafts are refused unless allow_draft is
    given; that use is logged. Every committed load is logged too.
    """
    drafts = [content.name for content in contents if content.is_draft]
    production = settings.DJANGO_ENV == "production"
    if production and drafts and not allow_draft:
        raise ContentError(
            "These files are still drafts and need the club's approval before they go "
            f"live: {', '.join(drafts)}. Change their status, or allow drafts."
        )
    report = load(contents, commit=commit)
    if commit:
        names = ", ".join(content.name for content in contents)
        audit(
            AuditLog.Category.CONTENT,
            "load_site_content",
            actor,
            f"Site content ({len(contents)} files)",
            "content",
            reason=names[:2000],
        )
        if production and drafts:
            audit(
                AuditLog.Category.CONTENT,
                "load_draft_content",
                actor,
                f"Draft site content ({len(drafts)} files)",
                "content",
                reason=f"Loaded with drafts allowed: {', '.join(drafts)}"[:2000],
            )
    return report
