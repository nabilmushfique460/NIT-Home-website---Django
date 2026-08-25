from django.core.mail import send_mail
from django.conf import settings
from .models import EmailVerification, User


class OTPService:
    """Service layer for OTP generation, email notification, and verification."""

    EXPIRY_MINUTES = 10

    @classmethod
    def create_and_send_otp(cls, user: User, purpose: str = 'Account Verification') -> tuple[str, EmailVerification]:
        """Generates a hashed OTP record in database and emails the plain code to the user."""
        plain_otp, record = EmailVerification.generate_otp(user)
        cls.send_otp_email(user, plain_otp, purpose)
        return plain_otp, record

    @classmethod
    def send_otp_email(cls, user: User, code: str, purpose: str = 'Account Verification') -> None:
        """Sends the 6-digit OTP code to the user's email address."""
        recipient_name = user.first_name if user.first_name else user.email.split('@')[0]
        subject = f"[N-IT Home] Your {purpose} Code: {code}"
        message = (
            f"Hello {recipient_name},\n\n"
            f"Your 6-digit One-Time Password (OTP) for {purpose.lower()} is: {code}\n"
            f"This code will expire in {cls.EXPIRY_MINUTES} minutes.\n\n"
            f"If you did not request this verification code, please ignore this email or change your password immediately.\n\n"
            f"Best regards,\n"
            f"N-IT Home Security Team"
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
    def verify_user_otp(cls, user: User, code: str) -> bool:
        """Verifies the OTP code for the user using the latest EmailVerification record."""
        verification = EmailVerification.objects.filter(user=user).first()
        if not verification:
            return False

        if verification.check_otp(code):
            # Clean up used verification record
            verification.delete()
            return True
        return False
