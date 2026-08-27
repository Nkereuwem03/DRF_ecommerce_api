class OTPPolicy:
    OTP_LENGTH = 6
    OTP_TTL = 600  # 10 minutes

    RESEND_COOLDOWN = 60  # 1 minute
    MAX_RESEND_PER_HOUR = 5

    MAX_VERIFY_ATTEMPTS = 3
    ACCOUNT_LOCK_DURATION = 600  # 10 minutes

    PASSWORD_RESET_TTL = 900  # 15 minutes