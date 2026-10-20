"""The admin's grouped sidebar (Unfold's SIDEBAR navigation) with Lucide icons.

Each item appears only to staff who may open the page it links to, so a section with
nothing allowed in it disappears. Badges are counts of things waiting for staff, never
names. Sections: Today, Members, Events, Content, Community, Money, Outreach, Settings.
"""

from django.urls import reverse

ICON = "admin/rose/nav_icon.html"


def _perm(codename):
    """A permission check for one item: `app.codename`, as Django's has_perm takes it."""

    def check(request):
        return request.user.has_perm(codename)

    return check


def _images(request):
    from .admin_site import can_review_images

    return can_review_images(request.user)


def _superuser(request):
    return request.user.is_superuser


def _changelist(app, model):
    return reverse(f"admin:{app}_{model}_changelist")


def _item(title, icon, link, permission, badge=None):
    item = {
        "title": title,
        "icon": icon,
        "icon_template": ICON,
        "link": link,
        "permission": permission,
    }
    if badge:
        item["badge"] = badge
    return item


def _model(title, icon, app, model, badge=None):
    return _item(title, icon, _changelist(app, model), _perm(f"{app}.view_{model}"), badge)


# Badges: Unfold calls these with the request and shows a non-empty result.


def desk_badge(request):
    """Paid online and waiting for their ID check at the door."""
    if not request.user.has_perm("memberships.change_membership"):
        return ""
    from apps.memberships.models import Membership

    count = Membership.objects.filter(
        status=Membership.Status.PENDING_PAYMENT, paid_awaiting_id_check=True
    ).count()
    return str(count) if count else ""


def reports_badge(request):
    """Open reports and posts waiting for review."""
    if not request.user.has_perm("feed.view_feedpost"):
        return ""
    from apps.feed.models import FeedPost, Report

    count = (
        Report.objects.filter(resolved_at__isnull=True).count()
        + FeedPost.objects.filter(status=FeedPost.Status.PENDING).count()
    )
    return str(count) if count else ""


def messages_badge(request):
    if not request.user.has_perm("contact.view_contactmessage"):
        return ""
    from apps.contact.models import ContactMessage

    count = ContactMessage.objects.filter(handled=False).count()
    return str(count) if count else ""


def _active(link, links):
    """Highlight one item: the one whose address is the longest match for this page, so the
    door desk (under the memberships list's address) is not also Memberships."""

    def check(request):
        path = request.path
        if link == reverse("admin:index"):
            return path == link
        if not path.startswith(link):
            return False
        return not any(
            other != link and other.startswith(link) and path.startswith(other) for other in links
        )

    return check


def sidebar(request):
    groups = _groups()
    links = [item["link"] for group in groups for item in group["items"]]
    for group in groups:
        for item in group["items"]:
            item["active"] = _active(item["link"], links)
    return groups


def _groups():
    from apps.feed.admin import QUEUE_PERMISSION

    return [
        {
            "title": "Today",
            "items": [
                _item("Dashboard", "layout-dashboard", reverse("admin:index"), None),
                _item(
                    "Door desk",
                    "scan-line",
                    reverse("admin:memberships_door_desk"),
                    _perm("memberships.change_membership"),
                    "apps.core.admin_nav.desk_badge",
                ),
                _item(
                    "Reports",
                    "flag",
                    reverse("admin:feed_moderation"),
                    _perm(QUEUE_PERMISSION),
                    "apps.core.admin_nav.reports_badge",
                ),
            ],
        },
        {
            "title": "Members",
            "items": [
                _model("Members", "users-round", "accounts", "user"),
                _model("Memberships", "id-card", "memberships", "membership"),
                _model("ID checks", "badge-check", "memberships", "idcheck"),
                _model("Tiers", "layers", "memberships", "tier"),
            ],
        },
        {
            "title": "Events",
            "items": [
                _model("Events", "calendar-days", "events", "event"),
                _item(
                    "RSVPs (counts only)",
                    "ticket",
                    reverse("admin:events_rsvp_counts"),
                    _perm("events.view_rsvp"),
                ),
                _model("Event tags", "tags", "events", "eventtag"),
            ],
        },
        {
            "title": "Content",
            "items": [
                _model("Journal", "newspaper", "journal", "post"),
                _model("Announcements", "megaphone", "feed", "announcement"),
                _model("Education", "graduation-cap", "education", "opportunity"),
                _model("Page copy", "file-text", "pages", "pagecontent"),
                _model("FAQ", "circle-question-mark", "pages", "faqitem"),
                _model("Guidelines", "scroll-text", "feed", "guidelines"),
                _model("Agreement", "file-pen-line", "memberships", "membershipagreement"),
            ],
        },
        {
            "title": "Community",
            "items": [
                _model("Feed posts", "images", "feed", "feedpost"),
                _model("Moderation log", "shield-alert", "safety", "memberaction"),
                _model("Appeals", "scale", "safety", "appeal"),
            ],
        },
        {
            "title": "Money",
            "items": [
                _model("Payments", "credit-card", "memberships", "payment"),
                _model("Donations", "hand-heart", "donations", "donation"),
                _item(
                    "Membership summary",
                    "chart-column-big",
                    reverse("admin:memberships_summary"),
                    _perm("memberships.view_membership"),
                ),
            ],
        },
        {
            "title": "Outreach",
            "items": [
                _model("Newsletter", "mail", "newsletter", "newsletter"),
                _model("Subscribers", "mail-check", "newsletter", "subscriber"),
                _model("Rentals", "building", "rentals", "rentalinquiry"),
                _model("Volunteers", "hand-helping", "volunteers", "volunteersignup"),
                _model(
                    "Contact messages",
                    "inbox",
                    "contact",
                    "contactmessage",
                    "apps.core.admin_nav.messages_badge",
                ),
            ],
        },
        {
            "title": "Settings",
            "items": [
                _model("Site settings", "sliders-horizontal", "pages", "sitesettings"),
                _item(
                    "Team and roles",
                    "shield-check",
                    _changelist("auth", "group"),
                    _perm("auth.view_group"),
                ),
                _item("Image review", "image", reverse("admin:image_review"), _images),
                _item("Audit log", "scroll-text", _changelist("core", "auditlog"), _superuser),
            ],
        },
    ]
