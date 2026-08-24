import random
import string
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from .models import EmailOTP, Profile

class OTPService:
    """Service layer for OTP generation, expiration management, and verification."""

    EXPIRY_MINUTES = 10
    COOLDOWN_SECONDS = 30

    @classmethod
    def generate_code(cls, length: int = 6) -> str:
        """Generates a cryptographically secure-like 6 digit numeric code."""
        return "".join(random.choices(string.digits, k=length))

    @classmethod
    def create_otp(cls, user: User, purpose: str = 'SIGNUP') -> EmailOTP:
        """Invalidates older active OTPs for this purpose and creates a fresh OTP."""
        EmailOTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(minutes=cls.EXPIRY_MINUTES)
        otp = EmailOTP.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
            is_used=False
        )
        cls.send_otp_email(user, code, purpose)
        return otp

    @classmethod
    def send_otp_email(cls, user: User, code: str, purpose: str) -> None:
        """Sends the OTP to the user email."""
        subject = f"[{settings.ROOT_URLCONF.split('.')[0].upper()}] Your Verification Code: {code}"
        message = (
            f"Hello {user.first_name or user.username},\n\n"
            f"Your One-Time Password (OTP) for {purpose.lower()} is: {code}\n"
            f"This code will expire in {cls.EXPIRY_MINUTES} minutes.\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Best regards,\nN-IT Home Team"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@nithome.com'),
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception:
            pass

    @classmethod
    def verify_otp(cls, user: User, code: str, purpose: str = 'SIGNUP') -> bool:
        """Verifies the code and marks it as used upon success."""
        otp = EmailOTP.objects.filter(
            user=user,
            code=code.strip(),
            purpose=purpose,
            is_used=False
        ).first()

        if otp and otp.is_valid():
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            if purpose == 'SIGNUP':
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.is_verified = True
                profile.save(update_fields=['is_verified'])
            return True
        return False
