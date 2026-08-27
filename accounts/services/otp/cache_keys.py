def resend_key(email: str, purpose: str) -> str:
    return f"otp_resend:{email}:{purpose}"


def attempt_key(email: str, purpose: str) -> str:
    return f"otp_attempts:{email}:{purpose}"
