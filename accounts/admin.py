from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerification, Profile, Address, Notification

# Inline configuration for User profile in admin
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile Extra Info'

# Inline configuration for User addresses in admin
class AddressInline(admin.TabularInline):
    model = Address
    extra = 0

# Custom User Admin configuration
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, AddressInline)
    list_display = (
        'email',
        'first_name',
        'last_name',
        'get_phone',
        'is_verified',
        'is_staff',
        'is_active',
        'created_at'
    )
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'is_active', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'profile__phone')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'last_login')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'password', 'first_name', 'last_name', 'is_verified', 'is_staff', 'is_superuser', 'is_active'),
            }
        ),
    )

    def get_phone(self, obj: User) -> str:
        return obj.profile.phone if hasattr(obj, 'profile') and obj.profile.phone else '-'
    get_phone.short_description = 'Phone'

# Admin configuration for EmailVerification tokens
@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'attempts', 'is_valid_status', 'created_at')
    list_filter = ('expires_at', 'created_at')
    search_fields = ('user__email', 'otp_hash')
    readonly_fields = ('otp_hash', 'expires_at', 'created_at', 'attempts')

    def is_valid_status(self, obj: EmailVerification) -> bool:
        return obj.is_valid()
    is_valid_status.short_description = 'Valid & Active'
    is_valid_status.boolean = True

# Admin configuration for Profile
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'phone', 'city')

# Admin configuration for Address
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'city', 'country', 'is_default', 'created_at')
    list_filter = ('city', 'country', 'is_default')
    search_fields = ('user__email', 'full_name', 'phone', 'street_address')

# Admin configuration for Notification
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__email', 'title', 'message')
