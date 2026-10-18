"""Events and posts with RSVP (prompt 2).

This app will hold:
- Event: title, slug, summary, body, starts_at, ends_at, location_label,
  capacity, audience (public or members), is_published, hero_image using
  apps.core.images.SanitizedImageField.
- Post: news-style announcements from staff, published or draft.
- RSVP: links accounts.User to Event with a status (going, waitlist,
  cancelled). Attendee lists only ever expose display names through
  apps.accounts.serializers.PublicUserSerializer.
"""
