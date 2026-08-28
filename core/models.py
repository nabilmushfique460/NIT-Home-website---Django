import uuid
from django.db import models
from django.conf import settings

# Model representing user inquiries and support tickets submitted through the contact form
class ContactMessage(models.Model):
    ticket_number = models.CharField(max_length=32, unique=True, editable=False, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets'
    )
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    admin_reply = models.TextField(blank=True, null=True, help_text='Internal or dispatched reply from support team')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Support Ticket / Inquiry'
        verbose_name_plural = 'Support Tickets & Inquiries'

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = f"NIT-TKT-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"[{self.ticket_number}] {self.name} - {self.subject}"
