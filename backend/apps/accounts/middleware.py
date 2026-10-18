import time

from django.conf import settings
from django.contrib.auth import logout

from .sessions import STAFF_STARTED


class SessionPolicyMiddleware:
    """Staff sessions close with the browser and last at most STAFF_SESSION_HOURS."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.is_staff:
            started = request.session.get(STAFF_STARTED)
            if started is None:
                request.session[STAFF_STARTED] = time.time()
                request.session.set_expiry(0)
            elif time.time() - started > settings.STAFF_SESSION_SECONDS:
                logout(request)
            elif not request.session.get_expire_at_browser_close():
                request.session.set_expiry(0)
        return self.get_response(request)
