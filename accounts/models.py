import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    objects = UserManager()

    MAX_LOGIN_ATTEMPTS = 5

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, max_length=254)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(blank=True, null=True)

    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(blank=True, null=True)

    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["-date_joined"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(failed_login_attempts__gte=0),
                name="failed_login_attempts_non_negative",
            ),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email

    def is_account_locked(self):
        return bool(
            self.account_locked_until and self.account_locked_until > timezone.now()
        )

    def lock_account(self, duration=None):
        seconds = duration if duration is not None else settings.LOGIN_ATTEMPTS_TIMEOUT
        self.account_locked_until = timezone.now() + timedelta(seconds=seconds)
        self.save(update_fields=["account_locked_until"])

    def unlock_account(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save(update_fields=["failed_login_attempts", "account_locked_until"])

    def record_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
            self.lock_account()
        else:
            self.save(update_fields=["failed_login_attempts"])

    def can_login(self):
        return self.is_active and not self.is_account_locked()


class Token(models.Model):
    class Purpose(models.TextChoices):
        SIGN_UP_VERIFICATION = "sign_up_verification", "Sign Up Verification"
        PASSWORD_RESET = "password_reset", "Password Reset"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tokens"
    )
    token = models.CharField(max_length=255)
    purpose = models.CharField(max_length=50, choices=Purpose.choices)
    reset_token = models.CharField(max_length=255, blank=True, null=True, unique=True)
    reset_token_expires_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "purpose", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "purpose"],
                condition=models.Q(status="pending"),
                name="unique_pending_token_per_user_purpose",
            ),
        ]

    def __str__(self):
        return f"{self.purpose} for {self.user.email}"

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_reset_token_expired(self):
        return (
            self.reset_token_expires_at is None
            or timezone.now() > self.reset_token_expires_at
        )

    def mark_verified(self):
        self.status = self.Status.VERIFIED
        self.verified_at = timezone.now()
        self.save(update_fields=["status", "verified_at"])

    def mark_expired(self):
        self.status = self.Status.EXPIRED
        self.save(update_fields=["status"])

    def set_reset_token(self, reset_token: str, expires_at):
        self.reset_token = reset_token
        self.reset_token_expires_at = expires_at
        self.save(update_fields=["reset_token", "reset_token_expires_at"])
