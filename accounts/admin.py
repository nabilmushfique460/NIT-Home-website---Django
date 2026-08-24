from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, EmailOTP, Address

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile Extra Info'

class AddressInline(admin.TabularInline):
    model = Address
    extra = 0

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, AddressInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_phone', 'get_verified', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__is_verified')

    def get_phone(self, obj):
        return obj.profile.phone if hasattr(obj, 'profile') else '-'
    get_phone.short_description = 'Phone'

    def get_verified(self, obj):
        return obj.profile.is_verified if hasattr(obj, 'profile') else False
    get_verified.short_description = 'Verified'
    get_verified.boolean = True

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'is_verified', 'created_at', 'updated_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')
    list_editable = ('is_verified',)
    actions = ['verify_profiles', 'unverify_profiles']

    def verify_profiles(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, "Selected profiles marked as verified.")
    verify_profiles.short_description = "Mark selected profiles as Verified"

    def unverify_profiles(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request, "Selected profiles marked as unverified.")
    unverify_profiles.short_description = "Mark selected profiles as Unverified"

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'purpose', 'created_at', 'expires_at', 'is_used', 'is_valid_status')
    list_filter = ('purpose', 'is_used', 'created_at')
    search_fields = ('user__username', 'user__email', 'code')
    readonly_fields = ('created_at',)

    def is_valid_status(self, obj):
        return obj.is_valid()
    is_valid_status.short_description = 'Valid & Active'
    is_valid_status.boolean = True

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'city', 'country', 'is_default', 'created_at')
    list_filter = ('city', 'country', 'is_default')
    search_fields = ('user__username', 'full_name', 'phone', 'street_address')
