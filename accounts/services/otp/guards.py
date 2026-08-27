from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from ...models import Token, User
from .cache_keys import resend_key
from .policy import OTPPolicy


def verify_account_locked(user: User):
    if user.is_account_locked():
        raise ValidationError(
            "Account temporarily locked. Try again later.",
            code="account_locked",
        )


def verify_resend_abuse(
    user: User,
    purpose: str,
):
    one_hour_ago = timezone.now() - timedelta(hours=1)

    resend_count = Token.objects.filter(
        user=user,
        purpose=purpose,
        created_at__gte=one_hour_ago,
    ).count()

    if resend_count >= OTPPolicy.MAX_RESEND_PER_HOUR:
        raise Throttled(detail=("Too many OTP requests. Please try again later."))


def verify_resend_cooldown(
    email: str,
    purpose: str,
):
    key = resend_key(email, purpose)

    if not cache.get(key):
        return

    ttl = cache.ttl(key)

    raise Throttled(
        wait=ttl if ttl and ttl > 0 else None,
        detail=("Please wait before requesting another OTP."),
    )
