from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import ContactMessage

class AboutView(TemplateView):
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'About N-IT Home'
        return context

class ContactView(TemplateView):
    template_name = 'core/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Contact Support'
        return context

    def post(self, request, *args, **kwargs):
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if not (name and email and subject and message):
            messages.error(request, 'Please complete all required fields.')
            return redirect('core:contact')

        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'nabil29089@gmail.com')
        admin_email = 'nabil29089@gmail.com'

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

        messages.success(request, 'Thank you! Your message has been sent successfully. A confirmation email has been dispatched to your inbox.')
        return redirect('core:contact')
