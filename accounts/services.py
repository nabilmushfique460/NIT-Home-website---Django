from django.core.mail import send_mail
from django.conf import settings
from .models import EmailVerification, User

class OTPService:
    EXPIRY_MINUTES = 10

    @classmethod
    def create_and_send_otp(cls, user: User, purpose: str='Account Verification') -> tuple[str, EmailVerification]:
        plain_otp, record = EmailVerification.generate_otp(user)
        cls.send_otp_email(user, plain_otp, purpose)
        return (plain_otp, record)

    @classmethod
    def send_otp_email(cls, user: User, code: str, purpose: str='Account Verification') -> None:
        recipient_name = user.first_name if user.first_name else user.email.split('@')[0]
        subject = f'[N-IT Home] Your {purpose} Code: {code}'
        message = f'Hello {recipient_name},\n\nYour 6-digit One-Time Password (OTP) for {purpose.lower()} is: {code}\nThis code will expire in {cls.EXPIRY_MINUTES} minutes.\n\nIf you did not request this verification code, please ignore this email or change your password immediately.\n\nBest regards,\nN-IT Home Security Team'
        try:
            send_mail(subject=subject, message=message, from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@nithome.com'), recipient_list=[user.email], fail_silently=True)
        except Exception:
            pass

    @classmethod
    def verify_user_otp(cls, user: User, code: str) -> bool:
        verification = EmailVerification.objects.filter(user=user).first()
        if not verification:
            return False
        if verification.check_otp(code):
            verification.delete()
            return True
        return False
