from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import Token, User
from ..serializers import CustomTokenObtainPairSerializer
from ..tasks import send_otp_email
from .otp.service import OTPService


class AuthService:
    @staticmethod
    @transaction.atomic
    def register(email: str, password: str) -> User:
        try:
            user = User.objects.create_user(
                email=email,
                password=password,
            )

        except IntegrityError:
            raise ValidationError(
                {
                    "email": "An account with this email already exists.",
                },
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
    def verify_email(email: str, otp: str) -> User:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid email or OTP.", code="invalid_credentials")

        if not OTPService.verify_otp(
            email=email,
            otp=otp,
            purpose=Token.Purpose.SIGN_UP_VERIFICATION,
        ):
            raise ValidationError("Invalid email or OTP.", code="invalid_credentials")

        user.email_verified = True
        user.save(update_fields=["email_verified"])

        return user

    @staticmethod
    def login(email: str, password: str) -> dict:
        email = email.strip().lower()

        user = User.objects.filter(email=email).first()

        authenticated_user = authenticate(email=email, password=password)

        if authenticated_user is None:
            if user is not None:
                user.record_failed_login()

            raise ValidationError(
                "No active account found with the given credentials",
                code="no_active_account",
            )

        if authenticated_user.is_account_locked():
            raise ValidationError(
                "Account temporarily locked due to failed login attempts. Please try again later.",
                code="account_locked",
            )

        if not authenticated_user.is_email_verified:
            raise ValidationError(
                "Email not verified. Please verify your email before logging in.",
                code="email_not_verified",
            )

        if authenticated_user.failed_login_attempts > 0:
            authenticated_user.failed_login_attempts = 0
            authenticated_user.save(update_fields=["failed_login_attempts"])

        refresh = CustomTokenObtainPairSerializer.get_token(authenticated_user)

        return {
            "user": authenticated_user,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def refresh_token(refresh_token: str) -> dict:
        try:
            token = RefreshToken(refresh_token)
        except TokenError as e:
            raise InvalidToken(str(e))

        user = User.objects.filter(id=token.payload.get("user_id")).first()

        if user is None:
            raise InvalidToken("User no longer exists")

        if not user.is_active:
            raise InvalidToken("Account is deactivated")

        data = {"access": str(token.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    token.blacklist()
                except AttributeError:
                    pass
            token.set_jti()
            token.set_exp()
            token.set_iat()
            data["refresh"] = str(token)

        return data
