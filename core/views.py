from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages
from .services import ContactService
from .models import ContactMessage

# View rendering company background, mission, and hardware lab information
class AboutView(TemplateView):
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'About N-IT Home'
        return context

# View handling contact form display, support ticket submission, and inquiry processing
class ContactView(TemplateView):
    template_name = 'core/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Contact Support & RMA'
        if self.request.user.is_authenticated:
            context['user_tickets'] = ContactMessage.objects.filter(user=self.request.user).order_by('-created_at')[:5]
        return context

    def post(self, request, *args, **kwargs):
        # Extract and sanitize contact form inputs
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        # Prefill from authenticated session if not manually provided
        if request.user.is_authenticated:
            if not name:
                name = request.user.get_full_name() or request.user.email
            if not email:
                email = request.user.email

        # Validate presence of required fields
        if not (name and email and subject and message):
            messages.error(request, 'Please complete all required fields.')
            return redirect('core:contact')

        # Delegate ticket creation, email confirmations, and admin notifications to service layer
        contact = ContactService.submit_contact_message(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
            user=request.user if request.user.is_authenticated else None
        )

        messages.success(
            request,
            f"Thank you! Your support ticket (#{contact.ticket_number}) has been created successfully. A confirmation email has been dispatched to {contact.email}."
        )
        return redirect('core:contact')

