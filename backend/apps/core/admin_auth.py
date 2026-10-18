"""Two-step staff login for the admin and the door desk.

1. Email and password (rate limited per IP, and locked out per email after
   repeated failures, exactly like member login).
2. A code from an authenticator app, or a single-use backup code. A staff
   member without an authenticator is taken through enrolment first, and is
   shown ten backup codes once.

Only after step 2 is the person logged in (with a fresh session key) and
marked verified; RoseAdminSite.has_permission refuses every admin view to a
session that is not verified.
"""

import base64
import secrets
import time
from io import BytesIO
from urllib.parse import quote

import qrcode
import qrcode.image.svg
from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django_otp import login as otp_login
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts import lockout
from apps.accounts.models import User
from apps.accounts.sessions import start_staff_session

from .models import AuditLog, audit
from .ratelimit import is_over_limit

PENDING_USER = "admin_pending_user"
PENDING_AT = "admin_pending_at"
PENDING_NEXT = "admin_pending_next"
ENROL_DEVICE = "admin_enrol_device"
BACKUP_CODES = "admin_backup_codes"
PENDING_SECONDS = 5 * 60
LOCKED_MESSAGE = "Too many attempts. Wait 15 minutes and try again."


class TokenForm(forms.Form):
    token = forms.CharField(
        label="Code",
        max_length=16,
        widget=forms.TextInput(
            attrs={"autocomplete": "one-time-code", "inputmode": "numeric", "autofocus": True}
        ),
    )

    def cleaned_token(self):
        return self.cleaned_data["token"].replace(" ", "").replace("-", "").strip()


def _context(request, site, **extra):
    return {**site.each_context(request), "site_header": site.site_header, **extra}


def _safe_next(request, value):
    if value and url_has_allowed_host_and_scheme(
        value, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return value
    return reverse("admin:index")


def _pending_user(request):
    user_id = request.session.get(PENDING_USER)
    started = request.session.get(PENDING_AT, 0)
    if not user_id or time.time() - started > PENDING_SECONDS:
        return None
    return User.objects.filter(pk=user_id, is_active=True, is_staff=True).first()


def _clear_pending(request):
    for key in (PENDING_USER, PENDING_AT, ENROL_DEVICE):
        request.session.pop(key, None)


def _finish(request, user, device):
    next_url = request.session.get(PENDING_NEXT)
    _clear_pending(request)
    request.session.pop(PENDING_NEXT, None)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    otp_login(request, device)
    start_staff_session(request)
    lockout.clear(user.email)
    return HttpResponseRedirect(_safe_next(request, next_url))


@never_cache
@csrf_protect
def admin_login(request, site):
    """Step 1: email and password. Nobody is logged in yet."""
    if request.user.is_authenticated and request.user.is_staff:
        if request.user.is_verified():
            return HttpResponseRedirect(_safe_next(request, request.GET.get("next")))
        # Signed in through the site but not yet verified: straight to step 2.
        request.session[PENDING_USER] = request.user.pk
        request.session[PENDING_AT] = time.time()
        request.session[PENDING_NEXT] = request.GET.get("next", "")
        return HttpResponseRedirect(reverse("admin:otp_verify"))

    form = AdminAuthenticationForm(request, data=request.POST or None)
    error = ""
    if request.method == "POST":
        email = str(request.POST.get("username", ""))
        if is_over_limit(
            request, "admin-login", [("ip", settings.ADMIN_LOGIN_RATE_LIMIT_IP)]
        ) or lockout.is_locked(email):
            error = LOCKED_MESSAGE
        elif form.is_valid():
            user = form.get_user()
            request.session.cycle_key()
            request.session[PENDING_USER] = user.pk
            request.session[PENDING_AT] = time.time()
            request.session[PENDING_NEXT] = request.POST.get("next", "")
            return HttpResponseRedirect(reverse("admin:otp_verify"))
        else:
            lockout.register_failure(email)
            if lockout.is_locked(email):
                error = LOCKED_MESSAGE
    context = _context(
        request,
        site,
        title="Log in",
        form=form,
        error=error,
        app_path=request.get_full_path(),
        next=request.GET.get("next", ""),
        username=request.user.get_username(),
    )
    return TemplateResponse(request, "admin/login.html", context)


def _confirmed_totp(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).first()


@never_cache
@csrf_protect
def otp_verify(request, site):
    """Step 2: a code from the authenticator app, or a backup code."""
    user = _pending_user(request)
    if user is None:
        return HttpResponseRedirect(reverse("admin:login"))
    totp = _confirmed_totp(user)
    if totp is None:
        return HttpResponseRedirect(reverse("admin:otp_enrol"))

    form = TokenForm(request.POST or None)
    error = ""
    if request.method == "POST":
        if lockout.is_locked(user.email):
            error = LOCKED_MESSAGE
        elif form.is_valid():
            token = form.cleaned_token()
            if totp.verify_token(token):
                return _finish(request, user, totp)
            backup = StaticDevice.objects.filter(user=user, confirmed=True).first()
            if backup is not None and backup.verify_token(token):
                audit(
                    AuditLog.Category.SECURITY,
                    "backup_code_used",
                    user,
                    f"Staff account ({user.display_name})",
                    "user",
                    target_user=user,
                )
                return _finish(request, user, backup)
            lockout.register_failure(user.email)
            error = LOCKED_MESSAGE if lockout.is_locked(user.email) else "That code did not work."
    return TemplateResponse(
        request,
        "admin/otp_verify.html",
        _context(request, site, title="Two-step check", form=form, error=error),
    )


def _otpauth_url(device, user):
    secret = base64.b32encode(device.bin_key).decode().rstrip("=")
    issuer = quote(settings.OTP_TOTP_ISSUER)
    # The authenticator shows the display name, never the email address.
    label = quote(f"{settings.OTP_TOTP_ISSUER}:{user.display_name}")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={issuer}"
        f"&digits={device.digits}&period={device.step}",
        secret,
    )


def _qr_data_uri(text):
    image = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    buffer = BytesIO()
    image.save(buffer)
    return "data:image/svg+xml;base64," + base64.b64encode(buffer.getvalue()).decode()


@never_cache
@csrf_protect
def otp_enrol(request, site):
    """First staff login: set up an authenticator app. There is no way to skip this."""
    user = _pending_user(request)
    if user is None:
        return HttpResponseRedirect(reverse("admin:login"))
    if _confirmed_totp(user) is not None:
        return HttpResponseRedirect(reverse("admin:otp_verify"))

    device = TOTPDevice.objects.filter(
        pk=request.session.get(ENROL_DEVICE), user=user, confirmed=False
    ).first()
    if device is None:
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        device = TOTPDevice.objects.create(user=user, name="Authenticator app", confirmed=False)
        request.session[ENROL_DEVICE] = device.pk

    form = TokenForm(request.POST or None)
    error = ""
    if request.method == "POST" and form.is_valid():
        if device.verify_token(form.cleaned_token()):
            device.confirmed = True
            device.save(update_fields=["confirmed"])
            StaticDevice.objects.filter(user=user).delete()
            backup = StaticDevice.objects.create(user=user, name="Backup codes", confirmed=True)
            codes = [secrets.token_hex(5) for _ in range(settings.OTP_BACKUP_CODE_COUNT)]
            StaticToken.objects.bulk_create(StaticToken(device=backup, token=c) for c in codes)
            audit(
                AuditLog.Category.SECURITY,
                "two_factor_enrolled",
                user,
                f"Staff account ({user.display_name})",
                "user",
                target_user=user,
            )
            _finish(request, user, device)
            request.session[BACKUP_CODES] = codes
            return HttpResponseRedirect(reverse("admin:otp_backup_codes"))
        error = "That code did not work. Check the time on your phone and try the newest code."

    url, secret = _otpauth_url(device, user)
    context = _context(
        request,
        site,
        title="Set up two-step login",
        form=form,
        error=error,
        qr=_qr_data_uri(url),
        secret=" ".join(secret[i : i + 4] for i in range(0, len(secret), 4)),
    )
    return TemplateResponse(request, "admin/otp_enrol.html", context)


@never_cache
def otp_backup_codes(request, site):
    """Shown once, straight after enrolment."""
    codes = request.session.pop(BACKUP_CODES, None)
    if not codes or not request.user.is_authenticated:
        return HttpResponseRedirect(resolve_url("admin:index"))
    context = _context(request, site, title="Your backup codes", codes=codes)
    return TemplateResponse(request, "admin/otp_backup_codes.html", context)
