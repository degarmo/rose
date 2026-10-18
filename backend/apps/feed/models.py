"""Opt-in member social feed (prompt 3).

This app will hold:
- FeedPost and FeedComment, each with an `author` foreign key to
  accounts.User and images through apps.core.images.SanitizedImageField.
- Every feed query filters with apps.accounts.models.feed_visible_q(), so a
  member who sets Profile.participates_in_feed to False has all of their
  posts and comments hidden at once. Nothing is deleted on opt-out, and it
  all reappears if they opt back in.
- Moderation: reports, hide-by-staff, and per-member blocks.
"""
