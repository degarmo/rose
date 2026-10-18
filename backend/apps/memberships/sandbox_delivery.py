"""Development only: send a signed sandbox webhook through the real endpoint.

The request goes through URL routing, the webhook view, signature
verification and the event service, exactly like a processor's webhook.
"""

import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory
from django.urls import resolve, reverse

from .providers.sandbox import sign


def deliver(payload):
    if not settings.DEBUG or "sandbox" not in settings.PAYMENT_PROVIDERS:
        raise ImproperlyConfigured("Sandbox webhooks are for development only.")
    body = json.dumps(payload).encode()
    path = reverse("payments-webhook", kwargs={"provider_key": "sandbox"})
    request = RequestFactory().post(
        path,
        data=body,
        content_type="application/json",
        HTTP_X_SANDBOX_SIGNATURE=sign(body),
        REMOTE_ADDR="127.0.0.1",
    )
    match = resolve(path)
    response = match.func(request, *match.args, **match.kwargs)
    return response.status_code
