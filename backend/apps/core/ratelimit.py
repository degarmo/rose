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


def hashed_value(value):
    """Salted hash for anything (an email address, say) used as a cache key."""
    return hashlib.sha256(f"{settings.SECRET_KEY}:{value}".encode()).hexdigest()


def is_over_limit(request, group, limits):
    """Count one attempt against each (key, rate) pair; True if any is exceeded.

    `key` is either the string "ip" or any other value, which is hashed. Every
    limit is incremented, so hitting one does not reset the others.
    """
    from django_ratelimit.core import is_ratelimited

    limited = False
    for key, rate in limits:
        if key == "ip":
            key_fn = hashed_ip_key
        else:
            digest = hashed_value(str(key).strip().lower())

            def key_fn(group, request, digest=digest):
                return digest

        limited |= is_ratelimited(
            request,
            group=f"{group}:{'ip' if key == 'ip' else 'value'}",
            key=key_fn,
            rate=rate,
            method=request.method,
            increment=True,
        )
    return limited
