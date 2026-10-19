"""The admin's left sidebar (an icon rail on narrow screens) and its Settings menu.

Each item appears only to staff who may open the page it links to. Badges are
counts of things waiting for staff, never names.
"""

from dataclasses import dataclass

from django.urls import reverse


@dataclass
class NavItem:
    key: str
    label: str
    icon: str
    url: str
    badge: int = 0
    # "count" shows the number on the icon; "dot" just marks that something is waiting.
    badge_style: str = "count"
    active: bool = False


def _waiting_counts(user):
    """Cheap counts for badges, only for what this person may see."""
    counts = {"moderation": 0, "messages": 0, "desk": 0}
    if user.has_perm("feed.view_feedpost"):
        from apps.feed.models import FeedPost, Report

        counts["moderation"] = (
            Report.objects.filter(resolved_at__isnull=True).count()
            + FeedPost.objects.filter(status=FeedPost.Status.PENDING).count()
        )
    if user.has_perm("contact.view_contactmessage"):
        from apps.contact.models import ContactMessage

        counts["messages"] = ContactMessage.objects.filter(handled=False).count()
    if user.has_perm("memberships.change_membership"):
        from apps.memberships.models import Membership

        counts["desk"] = Membership.objects.filter(
            status=Membership.Status.PENDING_PAYMENT, paid_awaiting_id_check=True
        ).count()
    return counts


def build_nav(request):
    from apps.feed.admin import QUEUE_PERMISSION

    user = request.user
    counts = _waiting_counts(user)
    home = reverse("admin:index")
    items = [NavItem("home", "Home", "house", home)]
    if user.has_perm("memberships.change_membership"):
        items.append(
            NavItem(
                "desk",
                "Door desk",
                "scan-line",
                reverse("admin:memberships_door_desk"),
                counts["desk"],
            )
        )
    if user.has_perm("contact.view_contactmessage"):
        changelist = reverse("admin:contact_contactmessage_changelist")
        items.append(
            NavItem(
                "messages", "Messages", "send", f"{changelist}?handled__exact=0", counts["messages"]
            )
        )
    items.append(
        NavItem(
            "notifications",
            "Notifications",
            "heart",
            f"{home}#needs-attention",
            badge=counts["moderation"] + counts["messages"] + counts["desk"],
            badge_style="dot",
        )
    )
    if user.has_perm("journal.add_post"):
        items.append(NavItem("create", "Create", "plus", reverse("admin:journal_post_add")))
    if user.has_perm("events.view_event"):
        items.append(
            NavItem("events", "Events", "calendar-days", reverse("admin:events_event_changelist"))
        )
    if user.has_perm(QUEUE_PERMISSION):
        items.append(
            NavItem(
                "moderation",
                "Moderation",
                "shield-alert",
                reverse("admin:feed_moderation"),
                counts["moderation"],
            )
        )
    items.append(NavItem("images", "Images", "images", reverse("admin:image_review")))
    if user.has_perm("memberships.view_membership"):
        items.append(
            NavItem(
                "dashboard", "Dashboard", "chart-column-big", reverse("admin:memberships_summary")
            )
        )
    items.append(NavItem("all", "All sections", "layout-grid", f"{home}#all-sections"))

    path = request.path
    for item in items:
        target = item.url.split("?")[0].split("#")[0]
        if item.key in ("notifications", "all"):
            continue
        item.active = path == target if item.key == "home" else path.startswith(target)

    settings_menu = []
    if user.has_perm("pages.change_sitesettings"):
        settings_menu.append(
            ("Site settings", "sliders-horizontal", reverse("admin:pages_sitesettings_changelist"))
        )
    if user.has_usable_password():
        settings_menu.append(("Change password", "key-round", reverse("admin:password_change")))
    if user.is_superuser:
        settings_menu.append(
            ("Audit log", "scroll-text", reverse("admin:core_auditlog_changelist"))
        )
    settings_menu.append(("View site", "external-link", "/"))
    return {"items": items, "settings": settings_menu}
