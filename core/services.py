from typing import Optional
from django.core.mail import send_mail
from django.conf import settings
from .models import ContactMessage
from accounts.models import Notification, User

# Service class handling contact submissions, ticket generation, and email notifications
class ContactService:

    @classmethod
    def submit_contact_message(
        cls,
        name: str,
        email: str,
        subject: str,
        message: str,
        phone: str = '',
        user: Optional[User] = None
    ) -> ContactMessage:
        # Create and persist support ticket record in database
        contact = ContactMessage.objects.create(
            user=user if user and user.is_authenticated else None,
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message
        )

        # Dispatch automated confirmation email to the user with ticket tracking ID
        cls.send_user_acknowledgment(contact)

        # Dispatch alert notification email to store administrators
        cls.send_admin_alert(contact)

        # Create in-app notification for authenticated buyers
        if contact.user:
            Notification.objects.create(
                user=contact.user,
                title=f"Support Ticket #{contact.ticket_number} Received",
                message=f"Your inquiry regarding '{subject}' has been submitted. Our bench engineers will respond shortly.",
                link="/contact/"
            )

        return contact

    @classmethod
    def send_user_acknowledgment(cls, contact: ContactMessage) -> None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com')
        client_subject = f"[N-IT HOME] Support Ticket Confirmation: {contact.subject} [#{contact.ticket_number}]"
        client_body = (
            f"Hello {contact.name},\n\n"
            f"Thank you for reaching out to N-IT HOME Bench Support & RMA Lab.\n"
            f"We have received your support inquiry and assigned Ticket Reference: {contact.ticket_number}.\n\n"
            f"Ticket Details:\n"
            f"----------------------------------------\n"
            f"Ticket Number : {contact.ticket_number}\n"
            f"Subject       : {contact.subject}\n"
            f"Sender Name   : {contact.name}\n"
            f"Sender Email  : {contact.email}\n"
            f"{f'Contact Phone : {contact.phone}' + chr(10) if contact.phone else ''}"
            f"----------------------------------------\n\n"
            f"Your Inquiry Message:\n"
            f"{contact.message}\n\n"
            f"Our dedicated hardware engineering team will review your inquiry and respond within 24 hours.\n\n"
            f"Best regards,\n"
            f"N-IT HOME Support Team\n"
            f"Banani, Dhaka-1213, Bangladesh\n"
            f"support@nithome.com | +880 1797529625"
        )
        try:
            send_mail(
                subject=client_subject,
                message=client_body,
                from_email=from_email,
                recipient_list=[contact.email],
                fail_silently=False
            )
        except Exception:
            pass

    @classmethod
    def send_admin_alert(cls, contact: ContactMessage) -> None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com')
        admin_email = 'nabil29089@gmail.com'
        admin_subject = f"[N-IT HOME Support Ticket #{contact.ticket_number}] {contact.name}: {contact.subject}"
        admin_body = (
            f"A new support ticket has been submitted via the website contact form:\n\n"
            f"Ticket Reference : {contact.ticket_number}\n"
            f"Customer Name    : {contact.name}\n"
            f"Customer Email   : {contact.email}\n"
            f"{f'Customer Phone   : {contact.phone}' + chr(10) if contact.phone else ''}"
            f"Subject          : {contact.subject}\n\n"
            f"Message Content:\n"
            f"{contact.message}\n\n"
            f"Manage and resolve this ticket in Django Admin:\n"
            f"http://127.0.0.1:8000/admin/core/contactmessage/{contact.id}/change/"
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

    @classmethod
    def send_admin_reply(cls, contact: ContactMessage, reply_message: str) -> None:
        contact.admin_reply = reply_message
        contact.is_resolved = True
        contact.save(update_fields=['admin_reply', 'is_resolved', 'updated_at'])

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com')
        subject = f"[N-IT HOME] Update on Support Ticket #{contact.ticket_number}: {contact.subject}"
        body = (
            f"Dear {contact.name},\n\n"
            f"Our N-IT HOME Support Team has responded to your inquiry (Ticket #{contact.ticket_number}):\n\n"
            f"----------------------------------------\n"
            f"Response from Support Team:\n"
            f"{reply_message}\n"
            f"----------------------------------------\n\n"
            f"Original Inquiry:\n"
            f"{contact.message}\n\n"
            f"If you have further questions, feel free to reply to this email.\n\n"
            f"Best regards,\n"
            f"N-IT HOME Support & RMA Team"
        )
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=from_email,
                recipient_list=[contact.email],
                fail_silently=False
            )
        except Exception:
            pass

        if contact.user:
            Notification.objects.create(
                user=contact.user,
                title=f"Update on Support Ticket #{contact.ticket_number}",
                message=f"Our team has responded to your inquiry '{contact.subject}'.",
                link="/contact/"
            )

