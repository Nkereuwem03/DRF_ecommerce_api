import hashlib
import hmac
import secrets

from django.conf import settings

from .policy import OTPPolicy


def generate_otp(length: int = OTPPolicy.OTP_LENGTH) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def hash_otp(otp: str) -> str:
    return hmac.new(
        settings.OTP_HASH_SECRET.encode(),
        otp.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_otp_hash(otp: str, otp_hash: str) -> bool:
    return hmac.compare_digest(
        hash_otp(otp),
        otp_hash,
    )
