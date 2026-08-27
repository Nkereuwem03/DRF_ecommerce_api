import secrets
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ...models import Token, User
from .cache_keys import attempt_key, resend_key
from .crypto import generate_otp, hash_otp, verify_otp_hash
from .guards import (
    verify_account_locked,
    verify_resend_abuse,
    verify_resend_cooldown,
)
from .policy import OTPPolicy
from .verification import (
    cleanup_attempts,
    increment_attempts,
)


class OTPService:
    @classmethod
    def create_otp_token(
        cls,
        user: User,
        purpose: str,
        otp_length: int = OTPPolicy.OTP_LENGTH,
    ) -> str:

        verify_account_locked(user)
        verify_resend_abuse(user, purpose)
        verify_resend_cooldown(
            user.email,
            purpose,
        )

        otp = generate_otp(otp_length)
        otp_hash = hash_otp(otp)

        now = timezone.now()

        Token.objects.filter(
            user=user,
            purpose=purpose,
            status=Token.Status.PENDING,
        ).update(
            status=Token.Status.EXPIRED,
            expires_at=now,
        )

        Token.objects.create(
            user=user,
            token=otp_hash,
            purpose=purpose,
            status=Token.Status.PENDING,
            expires_at=now + timedelta(seconds=OTPPolicy.OTP_TTL),
        )

        transaction.on_commit(
            lambda: cls._initialize_cache(
                email=user.email,
                purpose=purpose,
            )
        )

        return otp

    @staticmethod
    def _initialize_cache(
        email: str,
        purpose: str,
    ):
        cache.set(
            resend_key(email, purpose),
            True,
            timeout=OTPPolicy.RESEND_COOLDOWN,
        )

        cache.set(
            attempt_key(email, purpose),
            0,
            timeout=OTPPolicy.OTP_TTL,
        )

    @classmethod
    def verify_otp(
        cls,
        email: str,
        otp: str,
        purpose: str,
    ) -> Token:

        user = cls._get_user(email)

        verify_account_locked(user)

        token = (
            Token.objects.filter(
                user=user,
                purpose=purpose,
                status=Token.Status.PENDING,
            )
            .order_by("-created_at")
            .first()
        )

        if token is None:
            raise ValidationError(
                "OTP expired or not found. Please request a new one.",
                code="otp_not_found",
            )

        if token.is_expired():
            token.mark_expired()

            cleanup_attempts(
                email,
                purpose,
            )

            raise ValidationError(
                "OTP has expired. Please request a new one.",
                code="otp_expired",
            )

        if not verify_otp_hash(
            otp,
            token.token,
        ):
            attempts = increment_attempts(
                email,
                purpose,
            )

            if attempts >= OTPPolicy.MAX_VERIFY_ATTEMPTS:
                user.lock_account(duration=OTPPolicy.ACCOUNT_LOCK_DURATION)

                cleanup_attempts(
                    email,
                    purpose,
                )

                raise ValidationError(
                    "Too many failed attempts. Account temporarily locked.",
                    code="account_locked",
                )

            remaining = OTPPolicy.MAX_VERIFY_ATTEMPTS - attempts

            raise ValidationError(
                f"Invalid OTP. {remaining} attempt(s) remaining.",
                code="invalid_otp",
            )

        with transaction.atomic():
            token.mark_verified()

        cleanup_attempts(
            email,
            purpose,
        )

        return token

    @classmethod
    def verify_sign_up_otp(
        cls,
        email: str,
        otp: str,
    ) -> User:

        token = cls.verify_otp(
            email=email,
            otp=otp,
            purpose=Token.Purpose.SIGN_UP_VERIFICATION,
        )

        user = token.user

        with transaction.atomic():
            user.unlock_account()

            user.is_email_verified = True
            user.email_verified_at = timezone.now()

            user.save(
                update_fields=[
                    "is_email_verified",
                    "email_verified_at",
                ]
            )

        return user

    @classmethod
    def verify_password_reset_otp(
        cls,
        email: str,
        otp: str,
    ) -> str:

        token = cls.verify_otp(
            email=email,
            otp=otp,
            purpose=Token.Purpose.PASSWORD_RESET,
        )

        reset_token = secrets.token_urlsafe(32)

        token.set_reset_token(
            reset_token=reset_token,
            expires_at=timezone.now() + timedelta(seconds=OTPPolicy.PASSWORD_RESET_TTL),
        )

        return reset_token

    @staticmethod
    def _get_user(email: str) -> User:
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError(
                "Invalid email or OTP.",
                code="invalid_credentials",
            )
