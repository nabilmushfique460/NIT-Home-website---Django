from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session
from .models import ContactMessage

# Admin view for inspecting Django audit logs
@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    list_filter = ('action_flag', 'content_type', 'action_time')
    search_fields = ('object_repr', 'change_message', 'user__email')
    date_hierarchy = 'action_time'
    readonly_fields = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# Admin view for inspecting active user sessions
@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'get_decoded_data', 'expire_date')
    readonly_fields = ('session_key', 'session_data', 'expire_date')
    search_fields = ('session_key',)
    date_hierarchy = 'expire_date'

    def get_decoded_data(self, obj):
        try:
            data = obj.get_decoded()
            user_id = data.get('_auth_user_id')
            if user_id:
                return f"User ID: {user_id} | Cart items: {len(data.get('nit_cart', {}))}"
            return f"Guest session | Cart items: {len(data.get('nit_cart', {}))}"
        except Exception:
            return 'Encrypted session'
    get_decoded_data.short_description = 'Session Summary'

# Admin view for managing customer support tickets and contact inquiries
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'name', 'email', 'phone', 'subject', 'is_resolved', 'created_at')
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('ticket_number', 'name', 'email', 'phone', 'subject', 'message', 'admin_reply')
    list_editable = ('is_resolved',)
    readonly_fields = ('ticket_number', 'user', 'name', 'email', 'phone', 'subject', 'message', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    actions = ['mark_as_resolved', 'mark_as_unresolved']

    fieldsets = (
        ('Support Ticket Identifier', {
            'fields': ('ticket_number', 'user', 'is_resolved')
        }),
        ('Customer Contact Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Inquiry Details', {
            'fields': ('subject', 'message', 'created_at', 'updated_at')
        }),
        ('Support Team Response & Resolution', {
            'fields': ('admin_reply',),
            'description': 'Add a response note or resolution record for this ticket.'
        }),
    )

    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
        self.message_user(request, f"{queryset.count()} support tickets marked as Resolved.")
    mark_as_resolved.short_description = 'Mark selected tickets as Resolved'

    def mark_as_unresolved(self, request, queryset):
        queryset.update(is_resolved=False)
        self.message_user(request, f"{queryset.count()} support tickets marked as Open / Pending.")
    mark_as_unresolved.short_description = 'Mark selected tickets as Open / Pending'

