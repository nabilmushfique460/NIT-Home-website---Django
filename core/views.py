from django.views.generic import TemplateView

class AboutView(TemplateView):
    """About page Class-Based View."""
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'About N-IT Home'
        return context

class ContactView(TemplateView):
    """Contact page Class-Based View."""
    template_name = 'core/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Contact Support'
        return context
