from django.core.mail import send_mail
from django.conf import settings
from .models import ContactMessage

# Service class handling contact submissions and email notifications
class ContactService:

    @classmethod
    def submit_contact_message(cls, name: str, email: str, subject: str, message: str) -> ContactMessage:
        # Create and persist contact record in database
        contact = ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        # Dispatch automated confirmation email to the user
        cls.send_user_acknowledgment(name, email, subject, message)

        # Dispatch alert notification email to store administrators
        cls.send_admin_alert(name, email, subject, message)

        return contact

    @classmethod
    def send_user_acknowledgment(cls, name: str, email: str, subject: str, message: str) -> None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com')
        client_subject = f"[N-IT HOME] Message Received: {subject}"
        client_body = (
            f"Hello {name},\n\n"
            f"Thank you for contacting N-IT HOME Support. We have received your inquiry:\n\n"
            f"Subject: {subject}\n"
            f"Message:\n{message}\n\n"
            f"Our team will review your inquiry and get back to you shortly.\n\n"
            f"Best regards,\n"
            f"N-IT HOME Support Team\n"
            f"support@nithome.com"
        )
        try:
            send_mail(
                subject=client_subject,
                message=client_body,
                from_email=from_email,
                recipient_list=[email],
                fail_silently=False
            )
        except Exception:
            pass

    @classmethod
    def send_admin_alert(cls, name: str, email: str, subject: str, message: str) -> None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com')
        admin_email = 'nabil29089@gmail.com'
        admin_subject = f"[N-IT HOME Contact Ticket] {name}: {subject}"
        admin_body = (
            f"New support ticket submitted via website contact form:\n\n"
            f"Sender Name: {name}\n"
            f"Sender Email: {email}\n"
            f"Subject: {subject}\n\n"
            f"Message Content:\n"
            f"{message}"
        )
        try:
            send_mail(
                subject=admin_subject,
                message=admin_body,
                from_email=from_email,
                recipient_list=[admin_email],
                fail_silently=False
            )
        except Exception:
            pass
