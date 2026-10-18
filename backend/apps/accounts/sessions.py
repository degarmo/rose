"""Session rules. Members: idle sessions end after MEMBER_SESSION_DAYS (Django
refreshes the expiry on every request). Staff: sessions end when the browser
closes and at most STAFF_SESSION_HOURS after the two-step login."""

import time

STAFF_STARTED = "staff_session_started"


def start_staff_session(request):
    request.session[STAFF_STARTED] = time.time()
    request.session.set_expiry(0)
