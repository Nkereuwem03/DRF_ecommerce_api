from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Token, User
from .services.auth_service import AuthService


class AuthPasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reset@example.com",
            password="StrongPass123!",
            is_email_verified=True,
        )

    @patch("accounts.services.auth_service.send_otp_email.delay_on_commit")
    def test_request_password_reset_creates_pending_token(self, mock_delay):
        otp = AuthService.request_password_reset(email=self.user.email)

        self.assertTrue(
            Token.objects.filter(
                user=self.user,
                purpose=Token.Purpose.PASSWORD_RESET,
                status=Token.Status.PENDING,
            ).exists()
        )
        self.assertTrue(otp.isdigit())
        self.assertTrue(mock_delay.called)

    @patch("accounts.services.auth_service.send_otp_email.delay_on_commit")
    def test_reset_password_updates_user_password(self, _mock_delay):
        otp = AuthService.request_password_reset(email=self.user.email)

        updated_user = AuthService.reset_password(
            email=self.user.email,
            otp=otp,
            new_password="NewStrongPass456!",
        )

        self.assertTrue(updated_user.check_password("NewStrongPass456!"))
        self.assertNotEqual(updated_user.password, self.user.password)

    def test_suspended_user_cannot_login(self):
        self.user.account_status = User.AccountStatus.SUSPENDED
        self.user.save(update_fields=["account_status"])

        with self.assertRaises(ValidationError) as context:
            AuthService.login(
                email=self.user.email,
                password="StrongPass123!",
            )

        self.assertEqual(context.exception.get_codes(), ["account_not_allowed"])

    def test_banned_user_cannot_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.user.account_status = User.AccountStatus.BANNED
        self.user.save(update_fields=["account_status"])

        with self.assertRaises(InvalidToken) as context:
            AuthService.refresh_token(str(refresh))

        self.assertIn(
            "Account is not allowed to authenticate",
            str(context.exception),
        )
