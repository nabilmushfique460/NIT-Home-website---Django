from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile, Address

class SignUpForm(forms.ModelForm):
    """User registration form."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'name@example.com', 'class': 'form-input'})
    )
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-input'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-input'})
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '+880 1700-000000', 'class': 'form-input'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Create strong password', 'class': 'form-input'}),
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password', 'class': 'form-input'}),
        min_length=6
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Choose username', 'class': 'form-input'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email').strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

class LoginForm(forms.Form):
    """Standard authentication form."""
    username_or_email = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username or Email', 'class': 'form-input', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-input'})
    )

class OTPVerificationForm(forms.Form):
    """OTP code submission form."""
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': '6-digit OTP',
            'class': 'form-input text-center tracking-widest text-2xl font-mono',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'autocomplete': 'one-time-code',
            'autofocus': True,
        })
    )

class ForgotPasswordForm(forms.Form):
    """Password reset request form."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your registered email', 'class': 'form-input', 'autofocus': True})
    )

class ResetPasswordForm(forms.Form):
    """New password configuration form."""
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'placeholder': '6-digit OTP', 'class': 'form-input font-mono', 'maxlength': '6'})
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'New password', 'class': 'form-input'}),
        min_length=6
    )
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password', 'class': 'form-input'}),
        min_length=6
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_new_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_new_password', "Passwords do not match.")
        return cleaned_data

class ProfileForm(forms.ModelForm):
    """User profile update form."""
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'readonly': True}))

    class Meta:
        model = Profile
        fields = ['phone']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Contact phone'}),
        }

class AddressForm(forms.ModelForm):
    """Shipping Address creation & edit form."""
    class Meta:
        model = Address
        fields = ['full_name', 'phone', 'street_address', 'city', 'state_or_division', 'postal_code', 'country', 'is_default']
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
