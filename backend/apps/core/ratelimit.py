import hashlib

from django.conf import settings


def client_ip(request):
    """Return the client address, honouring a fixed number of trusted proxies.

    On Render the app sits behind one proxy that appends to X-Forwarded-For.
    Only the entry that proxy added is trusted; anything further left is
    client-supplied and can be forged.
    """
    proxy_count = settings.TRUSTED_PROXY_COUNT
    if proxy_count:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if len(hops) >= proxy_count:
            return hops[-proxy_count]
    return request.META.get("REMOTE_ADDR", "")


def hashed_ip_key(group, request):
    """Ratelimit key that never puts a raw IP address into the cache."""
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:{client_ip(request)}".encode())
    return digest.hexdigest()
