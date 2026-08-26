from django.core.mail import send_mail
from django.conf import settings
from .models import EmailVerification, User

# Service class encapsulating OTP creation, sending, rate limiting, and verification
class OTPService:
    EXPIRY_MINUTES = 10

    @classmethod
    def create_and_send_otp(cls, user: User, purpose: str = 'Account Verification') -> tuple[str, EmailVerification]:
        # Generate numeric one time passcode
        plain_otp, record = EmailVerification.generate_otp(user)
        # Dispatch notification email with the OTP code
        cls.send_otp_email(user, plain_otp, purpose)
        return (plain_otp, record)

    @classmethod
    def resend_otp(cls, user: User, purpose: str = 'Account Verification') -> tuple[bool, str, int]:
        # Check cooldown throttle before generating a new code
        can_resend, remaining = EmailVerification.can_resend_otp(user)
        if not can_resend:
            return (False, f"Please wait {remaining} seconds before requesting a new code.", remaining)
        cls.create_and_send_otp(user, purpose=purpose)
        return (True, "A new verification code has been sent.", 0)

    @classmethod
    def send_otp_email(cls, user: User, code: str, purpose: str = 'Account Verification') -> None:
        recipient_name = user.first_name if user.first_name else user.email.split('@')[0]
        subject = f"[N-IT HOME] Your {purpose} Code: {code}"
        message = (
            f"Hello {recipient_name},\n\n"
            f"Your 6-digit One-Time Password (OTP) for {purpose.lower()} is: {code}\n"
            f"This code will expire in {cls.EXPIRY_MINUTES} minutes.\n\n"
            f"If you did not request this verification code, please ignore this email or change your password immediately.\n\n"
            f"Best regards,\n"
            f"N-IT HOME Security Team"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com'),
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception:
            pass

    @classmethod
    def verify_user_otp(cls, user: User, code: str) -> bool:
        # Retrieve the latest verification record for the user
        verification = EmailVerification.objects.filter(user=user).first()
        if not verification:
            return False
        if verification.check_otp(code):
            verification.delete()
            return True
        return False
