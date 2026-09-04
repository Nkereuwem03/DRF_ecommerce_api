import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import (
    InvalidToken,
    TokenError,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import Token, User
from ..serializers import CustomTokenObtainPairSerializer
from ..tasks import send_otp_email
from .otp.policy import OTPPolicy
from .otp.service import OTPService


class AuthService:
    @staticmethod
    def _verify_account_can_authenticate(
        user: User,
    ) -> None:

        if not user.is_active:
            raise InvalidToken(
                "Account is deactivated",
            )

        if user.account_status in {
            User.AccountStatus.SUSPENDED,
            User.AccountStatus.BANNED,
        }:
            raise InvalidToken(
                "Account is not allowed to authenticate",
            )

    @staticmethod
    @transaction.atomic
    def register(
        email: str,
        password: str,
    ) -> User:

        email = email.strip().lower()

        try:
            user = User.objects.create_user(
                email=email,
                password=password,
            )
        except IntegrityError:
            raise ValidationError(
                {"email": ("An account with this email already exists.")},
                code="email_already_exists",
            )

        otp = OTPService.create_otp_token(
            user=user,
            purpose=Token.Purpose.SIGN_UP_VERIFICATION,
        )

        send_otp_email.delay_on_commit(
            email=user.email,
            otp=otp,
            purpose=Token.Purpose.SIGN_UP_VERIFICATION,
        )

        return user

    @staticmethod
    @transaction.atomic
    def request_password_reset(
        email: str,
    ) -> str:

        normalized_email = email.strip().lower()

        user = User.objects.filter(
            email=normalized_email,
        ).first()

        if user is None:
            raise ValidationError(
                "No account found with this email.",
                code="email_not_found",
            )

        otp = OTPService.create_otp_token(
            user=user,
            purpose=Token.Purpose.PASSWORD_RESET,
        )

        send_otp_email.delay_on_commit(
            email=user.email,
            otp=otp,
            purpose=Token.Purpose.PASSWORD_RESET,
        )

        return otp

    @staticmethod
    @transaction.atomic
    def reset_password(
        email: str,
        otp: str,
        new_password: str,
    ) -> User:

        normalized_email = email.strip().lower()

        user = (
            User.objects.select_for_update()
            .filter(
                email=normalized_email,
            )
            .first()
        )

        if user is None:
            raise ValidationError(
                "No account found with this email.",
                code="email_not_found",
            )

        token = OTPService.verify_otp(
            email=normalized_email,
            otp=otp,
            purpose=Token.Purpose.PASSWORD_RESET,
        )

        if token.user_id != user.id:
            raise ValidationError(
                "Invalid password reset request.",
                code="invalid_password_reset",
            )

        reset_token = secrets.token_urlsafe(32)

        token.set_reset_token(
            reset_token=reset_token,
            expires_at=timezone.now()
            + timedelta(
                seconds=OTPPolicy.PASSWORD_RESET_TTL,
            ),
        )

        if token.is_reset_token_expired():
            raise ValidationError(
                "Password reset token has expired.",
                code="reset_token_expired",
            )

        user.set_password(
            new_password,
        )

        user.account_status = User.AccountStatus.ACTIVE

        user.save(
            update_fields=[
                "password",
                "account_status",
            ],
        )

        token.status = Token.Status.EXPIRED

        token.save(
            update_fields=[
                "status",
            ],
        )

        return user

    @staticmethod
    def verify_email(
        email: str,
        otp: str,
    ) -> User:

        return OTPService.verify_sign_up_otp(
            email=email,
            otp=otp,
        )

    @staticmethod
    @transaction.atomic
    def login(
        email: str,
        password: str,
    ) -> dict:

        email = email.strip().lower()

        user = User.objects.filter(
            email=email,
        ).first()

        if user is None:
            authenticate(
                email=email,
                password=password,
            )

            raise ValidationError(
                "No active account found with the given credentials",
                code="no_active_account",
            )

        user = User.objects.select_for_update().get(
            pk=user.pk,
        )

        if user.is_account_locked():
            raise ValidationError(
                "Account temporarily locked due to failed login attempts. "
                "Please try again later.",
                code="account_locked",
            )

        if not user.is_active:
            raise ValidationError(
                "No active account found with the given credentials",
                code="no_active_account",
            )

        if user.account_status in {
            User.AccountStatus.SUSPENDED,
            User.AccountStatus.BANNED,
        }:
            raise ValidationError(
                "Account is not allowed to authenticate",
                code="account_not_allowed",
            )

        authenticated_user = authenticate(
            email=email,
            password=password,
        )

        if authenticated_user is None:
            user.record_failed_login()

            raise ValidationError(
                "No active account found with the given credentials",
                code="no_active_account",
            )

        if not authenticated_user.is_email_verified:
            raise ValidationError(
                "Email not verified. Please verify your email before logging in.",
                code="email_not_verified",
            )

        if authenticated_user.failed_login_attempts > 0:
            authenticated_user.failed_login_attempts = 0

            authenticated_user.save(
                update_fields=[
                    "failed_login_attempts",
                ],
            )

        refresh = CustomTokenObtainPairSerializer.get_token(
            authenticated_user,
        )

        return {
            "user": authenticated_user,
            "access": str(
                refresh.access_token,
            ),
            "refresh": str(
                refresh,
            ),
        }

    @staticmethod
    def refresh_token(
        refresh_token: str,
    ) -> dict:

        try:
            token = RefreshToken(
                refresh_token,
            )
        except TokenError as exc:
            raise InvalidToken(
                str(exc),
            )

        user = User.objects.filter(
            id=token.payload.get("user_id"),
        ).first()

        if user is None:
            raise InvalidToken(
                "User no longer exists",
            )

        AuthService._verify_account_can_authenticate(
            user,
        )

        data = {
            "access": str(
                token.access_token,
            ),
        }

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    token.blacklist()
                except AttributeError:
                    pass

            token.set_jti()
            token.set_exp()
            token.set_iat()

            data["refresh"] = str(
                token,
            )

        return data
