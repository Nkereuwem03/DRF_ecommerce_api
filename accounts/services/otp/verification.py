from django.core.cache import cache

from .cache_keys import attempt_key
from .policy import OTPPolicy


def increment_attempts(email: str, purpose: str) -> int:
    key = attempt_key(email, purpose)

    cache.add(
        key,
        0,
        timeout=OTPPolicy.OTP_TTL,
    )

    try:
        return cache.incr(key)
    except ValueError:
        cache.set(
            key,
            1,
            timeout=OTPPolicy.OTP_TTL,
        )
        return 1


def get_attempts(email: str, purpose: str) -> int:
    return cache.get(
        attempt_key(email, purpose),
        0,
    )


def cleanup_attempts(email: str, purpose: str):
    cache.delete(attempt_key(email, purpose))
