"""Paid membership and paywall (prompt 4).

This app will hold:
- Plan: name, price, billing interval, description, is_active.
- Membership: links accounts.User to a Plan with status (pending, active,
  lapsed, cancelled), current period dates and the payment provider's
  customer and subscription identifiers. No card data is stored here.
- A permission class used by member-only API views (/api/members/...).
"""
