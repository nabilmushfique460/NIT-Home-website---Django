from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    list_filter = ('action_flag', 'content_type', 'action_time')
    search_fields = ('object_repr', 'change_message', 'user__username')
    date_hierarchy = 'action_time'
    readonly_fields = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

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
