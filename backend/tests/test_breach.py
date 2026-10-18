"""Optional breached-password check: off by default, k-anonymity when on."""

import hashlib
import urllib.error

import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.accounts import breach

PASSWORD = "correct-horse-battery-9"
SHA1 = hashlib.sha1(PASSWORD.encode()).hexdigest().upper()


class FakeReply:
    def __init__(self, body):
        self.body = body.encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def calls(monkeypatch):
    seen = []

    def fake_urlopen(request, timeout):
        seen.append(request)
        return FakeReply(f"0000000000000000000000000000000000A:0\r\n{SHA1[5:]}:42\r\n")

    monkeypatch.setattr(breach.urllib.request, "urlopen", fake_urlopen)
    return seen


def test_off_by_default_and_never_calls_out(settings, calls):
    assert settings.PASSWORD_BREACH_CHECK is False
    validate_password(PASSWORD)
    assert calls == []


def test_only_a_five_character_prefix_leaves_the_server(settings, calls):
    settings.PASSWORD_BREACH_CHECK = True
    with pytest.raises(ValidationError, match="data breach"):
        validate_password(PASSWORD)
    (request,) = calls
    assert request.full_url == f"https://api.pwnedpasswords.com/range/{SHA1[:5]}"
    assert SHA1[5:] not in request.full_url and PASSWORD not in request.full_url
    assert request.get_header("Add-padding") == "true"


def test_unknown_passwords_pass(settings, monkeypatch):
    settings.PASSWORD_BREACH_CHECK = True
    monkeypatch.setattr(
        breach.urllib.request, "urlopen", lambda request, timeout: FakeReply("ABCDEF:3\r\n")
    )
    validate_password(PASSWORD)


def test_service_down_accepts_the_password(settings, monkeypatch, caplog):
    settings.PASSWORD_BREACH_CHECK = True

    def down(request, timeout):
        raise urllib.error.URLError("unreachable")

    monkeypatch.setattr(breach.urllib.request, "urlopen", down)
    validate_password(PASSWORD)
    assert "unreachable" in caplog.text
    assert PASSWORD not in caplog.text
