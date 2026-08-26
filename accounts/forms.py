from typing import Any
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Profile, Address
from .validators import validate_strong_password

User = get_user_model()

# Form for user registration
class SignUpForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'name@example.com', 'class': 'form-input', 'autofocus': True})
    )
    first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-input'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-input'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+880 1700-000000', 'class': 'form-input'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Create strong password', 'class': 'form-input'}),
        min_length=8,
        help_text='Must be at least 8 characters and include uppercase, lowercase, number, and special character.'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password', 'class': 'form-input'}),
        min_length=8
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']

    def clean_email(self) -> str:
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('A user with this email address already exists.')
        return email

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', 'Passwords do not match.')
            else:
                try:
                    validate_strong_password(password)
                    validate_password(password)
                except ValidationError as e:
                    self.add_error('password', e)
        return cleaned_data

# Form for user authentication
class LoginForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'name@example.com', 'class': 'form-input', 'autofocus': True})
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••', 'class': 'form-input'})
    )

# Form for OTP entry during verification
class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                'placeholder': '123456',
                'class': 'form-input font-mono text-center',
                'maxlength': '6',
                'pattern': '[0-9]{6}',
                'autocomplete': 'one-time-code',
                'autofocus': True,
                'onpaste': 'return false;',
            }
        )
    )

# Form for initiating password reset requests
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your registered email', 'class': 'form-input', 'autofocus': True})
    )

# Form for setting a new password after OTP verification
class ResetPasswordForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                'placeholder': '123456',
                'class': 'form-input font-mono text-center',
                'maxlength': '6',
                'pattern': '[0-9]{6}',
                'autofocus': True,
                'onpaste': 'return false;',
            }
        )
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'New password (min 8 characters)', 'class': 'form-input'}),
        min_length=8,
        help_text='Must be at least 8 characters and include uppercase, lowercase, number, and special character.'
    )
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Re-enter new password', 'class': 'form-input'}),
        min_length=8
    )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_new_password')
        if p1 and p2:
            if p1 != p2:
                self.add_error('confirm_new_password', 'Passwords do not match.')
            else:
                try:
                    validate_strong_password(p1)
                    validate_password(p1)
                except ValidationError as e:
                    self.add_error('new_password', e)
        return cleaned_data

# Form for updating user profile settings
class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'readonly': True})
    )

    class Meta:
        model = Profile
        fields = ['phone', 'street_address', 'city', 'postal_code']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+880 1812-345678'}),
            'street_address': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Street / House / Road'}),
            'city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'City'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Postal Code'}),
        }

# Form for managing customer shipping addresses
class AddressForm(forms.ModelForm):

    class Meta:
        model = Address
        fields = [
            'full_name',
            'phone',
            'street_address',
            'city',
            'state_or_division',
            'postal_code',
            'country',
            'is_default',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Receiver Full Name', 'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Delivery Phone Number', 'class': 'form-input'}),
            'street_address': forms.TextInput(attrs={'placeholder': 'House / Flat / Road / Street info', 'class': 'form-input'}),
            'city': forms.TextInput(attrs={'placeholder': 'City (e.g. Dhaka, Chittagong)', 'class': 'form-input'}),
            'state_or_division': forms.TextInput(attrs={'placeholder': 'State / Division', 'class': 'form-input'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'Postal Code', 'class': 'form-input'}),
            'country': forms.TextInput(attrs={'placeholder': 'Country', 'class': 'form-input'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
