"""The staff section's door desk (/members/staff/door): the admin's door desk as an API.

Search, the card and every action come from apps.memberships.desk, the same code the
admin's door desk runs, so the two always agree; every action and signature reveal is
logged there. Anyone without the door desk permission and the two-step login gets the
same 404 as an unknown address, before CSRF or anything else is checked.
"""

from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.admin_auth import qr_data_uri
from apps.core.api import check_write_limit
from apps.core.email import site_link
from apps.feed.api import SessionWithoutCsrf, enforce_csrf
from apps.safety import roles

from . import desk


def _when(moment):
    return moment.isoformat() if moment else None


def card_payload(row, staff):
    m = row["membership"]
    tier = m.tier
    flags = row["flags"]
    return {
        "id": m.pk,
        "reference_code": m.reference_code,
        "display_name": m.user.display_name if m.user else "Deleted account",
        "tier": {
            "name": tier.name,
            "price": row["default_amount"],
            "currency": tier.currency,
            "interval": tier.get_interval_display(),
            "guests_included": tier.guests_included_per_event,
            "guest_discount": tier.guest_discount,
            "is_free": tier.is_free,
        },
        "status": m.status,
        "status_label": m.get_status_display(),
        "source_label": m.get_source_display(),
        "is_guest_pass": row["is_guest_pass"],
        "id_checked": row["id_checked"],
        "paid_awaiting_id_check": m.paid_awaiting_id_check,
        "period_end": _when(m.current_period_end),
        "events_remaining": row["events_remaining"],
        "team_account": row["team_account"],
        "is_you": m.user_id == staff.pk,
        "do_not_admit": flags["do_not_admit"],
        "events_suspended_until": _when(flags["events_suspended_until"]),
        "default_amount": row["default_amount"],
        "actions": row["actions"],
        "payments": [
            {
                "id": payment.pk,
                "date": _when(payment.created_at),
                "status": payment.status,
                "status_label": payment.get_status_display(),
                "method_label": payment.get_method_display(),
                "amount": payment.amount_display,
                "refundable": payment.status == payment.Status.SUCCEEDED
                and payment.method != payment.Method.COMP,
            }
            for payment in row["payments"]
        ],
    }


def person_payload(row, staff):
    user = row["person"]
    flags = row["flags"]
    return {
        "id": user.pk,
        "display_name": user.display_name,
        "team_account": row["team_account"],
        "feed_granted": row["feed_granted"],
        "is_you": user.pk == staff.pk,
        "id_checked": row["id_checked"],
        "do_not_admit": flags["do_not_admit"],
        "actions": row["actions"],
    }


class DoorDeskView(APIView):
    authentication_classes = [SessionWithoutCsrf]
    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    def initial(self, request, *args, **kwargs):
        if not roles.can_use_door_desk(request.user):
            raise Http404
        if request.method not in SAFE_METHODS:
            enforce_csrf(request._request)
        super().initial(request, *args, **kwargs)
        check_write_limit(self, request)

    def get(self, request):
        query = request.query_params.get("q", "")
        needs_id = request.query_params.get("needs_id") == "1"
        if needs_id:
            memberships, people = desk.needing_id_check()
        else:
            memberships, people = desk.find_memberships(query), desk.find_people(query)
        rows = [desk.card(m) for m in memberships]
        persons = [desk.person_card(user) for user in people]
        guest = any(row["is_guest_pass"] for row in rows)
        mine = any(user.pk == request.user.pk for user in people) or any(
            row["membership"].user_id == request.user.pk for row in rows
        )
        return Response(
            {
                "query": query,
                "needs_id": needs_id,
                "results": [card_payload(row, request.user) for row in rows],
                "people": [person_payload(row, request.user) for row in persons],
                # Only for checking your own ID: everyone else on the team, as witnesses.
                "witnesses": [
                    {"id": user.pk, "display_name": user.display_name}
                    for user in desk.witnesses_for(request.user)
                ]
                if mine
                else [],
                "tonight_events": [
                    {"id": event.pk, "title": event.title, "starts_at": _when(event.starts_at)}
                    for event in (desk.tonight_events() if rows and not needs_id else [])
                ],
                "donation_methods": [
                    {"value": value, "label": label} for value, label in desk.DONATION_METHODS
                ],
                # "Convert to member": the guest scans this on their own phone.
                "join_url": site_link("/join") if guest else None,
                "join_qr": qr_data_uri(site_link("/join")) if guest else None,
                "today": timezone.localdate().isoformat(),
            }
        )

    def post(self, request):
        try:
            outcome = desk.perform(request.user, request.data)
        except desk.DeskError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if outcome.signature:
            membership_id, name = next(iter(outcome.signature.items()))
            return Response({"signature": {"membership": membership_id, "name": name}})
        return Response({"message": outcome.message})
