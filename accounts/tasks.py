from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Token, User

OTP_EMAIL_CONFIG = {
    Token.Purpose.SIGN_UP_VERIFICATION: {
        "subject": "Verify your email address",
        "template": "emails/signup_otp.html",
        "expiry": 10,
    },
    Token.Purpose.PASSWORD_RESET: {
        "subject": "Your password reset code",
        "template": "emails/password_reset_otp.html",
        "expiry": 10,
    },
}

@shared_task(
    bind=True,
    max_retries=3,
)
def send_otp_email(
    self,
    email: str,
    otp: str,
    purpose: str,
):

    config = OTP_EMAIL_CONFIG.get(purpose)

    if config is None:
        raise ValueError(f"Unsupported OTP purpose: {purpose}")

    user = User.objects.filter(email=email).first()

    if user is None:
        return

    app_name = getattr(
        settings,
        "APP_NAME",
        "ecommerce API",
    )

    context = {
        "subject": config["subject"],
        "otp": otp,
        "expiry_mins": config["expiry"],
        "year": timezone.now().year,
        "app_name": app_name,
        "full_name": user.get_full_name(),
    }

    text_content = render_to_string(
        config["template"].replace(".html", ".txt"),
        context,
    )

    html_content = render_to_string(
        config["template"],
        context,
    )

    message = EmailMultiAlternatives(
        subject=config["subject"],
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
        headers={"List-Unsubscribe": "<mailto:unsub@example.com>"},
    )

    message.attach_alternative(
        html_content,
        "text/html",
    )

    try:
        message.send()

    except OSError as exc:
        raise self.retry(
            exc=exc,
            countdown=60,
        )

    except ConnectionError as exc:
        raise self.retry(
            exc=exc,
            countdown=60,
        )
