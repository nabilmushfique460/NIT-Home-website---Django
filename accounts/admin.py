from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerification, Profile, Address


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile Extra Info'


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, AddressInline)
    list_display = ('email', 'first_name', 'last_name', 'get_phone', 'is_verified', 'is_staff', 'is_active', 'created_at')
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
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'first_name', 'last_name', 'is_verified', 'is_staff', 'is_superuser', 'is_active'),
        }),
    )

    def get_phone(self, obj):
        return obj.profile.phone if hasattr(obj, 'profile') and obj.profile.phone else '-'
    get_phone.short_description = 'Phone'


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'attempts', 'is_valid_status', 'created_at')
    list_filter = ('expires_at', 'created_at')
    search_fields = ('user__email', 'otp_hash')
    readonly_fields = ('otp_hash', 'expires_at', 'created_at', 'attempts')

    def is_valid_status(self, obj):
        return obj.is_valid()
    is_valid_status.short_description = 'Valid & Active'
    is_valid_status.boolean = True


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'phone', 'city')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'city', 'country', 'is_default', 'created_at')
    list_filter = ('city', 'country', 'is_default')
    search_fields = ('user__email', 'full_name', 'phone', 'street_address')
