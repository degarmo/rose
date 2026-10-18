from datetime import datetime, time, timedelta

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.api import CsrfProtectedAPIView

from .ics import build_ics
from .models import RSVP, Event
from .serializers import (
    EventDetailSerializer,
    EventSerializer,
    MyRSVPSerializer,
    RSVPInputSerializer,
    rsvp_state,
)
from .services import RSVPError, cancel_rsvp, submit_rsvp
from .tasks import rsvp_from_cancel_token

MAX_CALENDAR_DAYS = 62


def my_rsvps_for(request, events):
    if not request.user.is_authenticated:
        return {}
    rsvps = RSVP.objects.filter(user=request.user, event__in=[e.pk for e in events])
    return {rsvp.event_id: rsvp for rsvp in rsvps}


class EventListMixin:
    def list(self, request, *args, **kwargs):
        events = list(self.filter_queryset(self.get_queryset()))
        context = {**self.get_serializer_context(), "my_rsvps": my_rsvps_for(request, events)}
        return Response(EventSerializer(events, many=True, context=context).data)


class EventListView(EventListMixin, generics.ListAPIView):
    """Upcoming events by default; `?past=1` for past ones; `?category=` to filter."""

    def get_queryset(self):
        events = Event.objects.visible_to(self.request.user).with_going_total()
        category = self.request.query_params.get("category")
        if category:
            if category not in Event.Category.values:
                raise ValidationError({"category": "Unknown category."})
            events = events.filter(category=category)
        now = timezone.now()
        if self.request.query_params.get("past") == "1":
            return events.filter(ends_at__lt=now).order_by("-starts_at")[:50]
        # Aggregate annotations drop Meta.ordering, so order explicitly.
        return events.upcoming(now).order_by("starts_at", "title")


class EventCalendarView(EventListMixin, generics.ListAPIView):
    """Events overlapping `start`..`end` (YYYY-MM-DD, at most 62 days)."""

    def get_queryset(self):
        try:
            start = datetime.fromisoformat(self.request.query_params["start"]).date()
            end = datetime.fromisoformat(self.request.query_params["end"]).date()
        except (KeyError, ValueError) as exc:
            raise ValidationError({"detail": "Give start and end as YYYY-MM-DD."}) from exc
        if end < start or (end - start).days > MAX_CALENDAR_DAYS:
            raise ValidationError({"detail": f"Use a range of up to {MAX_CALENDAR_DAYS} days."})
        range_start = timezone.make_aware(datetime.combine(start, time.min))
        range_end = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))
        events = Event.objects.visible_to(self.request.user).with_going_total()
        category = self.request.query_params.get("category")
        if category:
            events = events.filter(category=category)
        return events.filter(starts_at__lt=range_end, ends_at__gte=range_start).order_by(
            "starts_at", "title"
        )


class EventDetailView(generics.RetrieveAPIView):
    serializer_class = EventDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Event.objects.visible_to(self.request.user).with_going_total()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context["my_rsvps"] = {
                rsvp.event_id: rsvp
                for rsvp in RSVP.objects.filter(
                    user=self.request.user, event__slug=self.kwargs["slug"]
                )
            }
        return context


class EventRSVPView(CsrfProtectedAPIView):
    """POST to RSVP or change party size and note; DELETE to cancel."""

    write_limit = "ACCOUNT_WRITE_RATE_LIMIT"

    permission_classes = [IsAuthenticated]

    def get_event(self, slug):
        return get_object_or_404(Event.objects.visible_to(self.request.user), slug=slug)

    def respond(self, event, http_status=status.HTTP_200_OK):
        event = Event.objects.with_going_total().get(pk=event.pk)
        mine = RSVP.objects.filter(event=event, user=self.request.user).first()
        return Response({"rsvp": rsvp_state(self.request.user, event, mine)}, status=http_status)

    def post(self, request, slug):
        event = self.get_event(slug)
        serializer = RSVPInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            submit_rsvp(
                request.user,
                event,
                serializer.validated_data["party_size"],
                serializer.validated_data["note_to_hosts"].strip(),
            )
        except RSVPError as exc:
            return Response(
                {"detail": exc.message, "code": exc.code}, status=status.HTTP_409_CONFLICT
            )
        return self.respond(event)

    def delete(self, request, slug):
        event = self.get_event(slug)
        rsvp = RSVP.objects.filter(event=event, user=request.user).first()
        if rsvp is not None:
            cancel_rsvp(rsvp)
        return self.respond(event)


class CancelByTokenView(CsrfProtectedAPIView):
    """Cancel from the link in an email, without signing in."""

    write_limit = "TOKEN_RATE_LIMIT"

    def post(self, request):
        rsvp = rsvp_from_cancel_token(str(request.data.get("token", "")))
        if rsvp is None:
            return Response(
                {"detail": "This link is no longer valid."}, status=status.HTTP_400_BAD_REQUEST
            )
        result = cancel_rsvp(rsvp)
        return Response(
            {
                "detail": "Your RSVP is cancelled."
                if result.outcome == "cancelled"
                else "This RSVP was already cancelled.",
                "event": {
                    "slug": rsvp.event.slug,
                    "title": rsvp.event.title,
                    "starts_at": rsvp.event.starts_at,
                },
            }
        )


class EventICSView(generics.GenericAPIView):
    lookup_field = "slug"

    def get_queryset(self):
        return Event.objects.visible_to(self.request.user)

    def get(self, request, slug):
        event = self.get_object()
        include_details = request.query_params.get("details") == "1"
        response = HttpResponse(
            build_ics(event, include_details=include_details),
            content_type="text/calendar; charset=utf-8",
        )
        response["Content-Disposition"] = 'attachment; filename="evening.ics"'
        response["Cache-Control"] = "private, no-store"
        return response


class MyRSVPListView(generics.ListAPIView):
    """Upcoming RSVPs for the signed-in person only."""

    permission_classes = [IsAuthenticated]
    serializer_class = MyRSVPSerializer

    def get_queryset(self):
        return (
            RSVP.objects.filter(
                user=self.request.user,
                status__in=[RSVP.Status.GOING, RSVP.Status.WAITLIST],
                event__ends_at__gte=timezone.now(),
            )
            .select_related("event")
            .order_by("event__starts_at")
        )
