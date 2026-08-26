from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages
from .services import ContactService

# View rendering company background, mission, and hardware lab information
class AboutView(TemplateView):
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'About N-IT Home'
        return context

# View handling contact form display and message processing
class ContactView(TemplateView):
    template_name = 'core/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Contact Support'
        return context

    def post(self, request, *args, **kwargs):
        # Extract and sanitize contact form inputs
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        # Validate presence of all required fields
        if not (name and email and subject and message):
            messages.error(request, 'Please complete all required fields.')
            return redirect('core:contact')

        # Delegate contact persistence and notification to service layer
        ContactService.submit_contact_message(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        messages.success(
            request,
            'Thank you! Your message has been sent successfully. A confirmation email has been dispatched to your inbox.'
        )
        return redirect('core:contact')
