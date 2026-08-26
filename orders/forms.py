from django import forms
from .models import Order

# Form capturing delivery address and order details during checkout
class CheckoutForm(forms.Form):
    full_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={'placeholder': 'Full Name', 'class': 'form-input', 'required': 'required'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email Address for Order Updates', 'class': 'form-input', 'required': 'required'})
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Mobile Number (e.g. +880 1700-000000)', 'class': 'form-input', 'required': 'required'})
    )
    street_address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'House / Flat / Road / Street address', 'class': 'form-input', 'required': 'required'})
    )
    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'City (e.g. Dhaka, Chittagong)', 'class': 'form-input', 'required': 'required'})
    )
    state_or_division = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Division / State (Optional)', 'class': 'form-input'})
    )
    postal_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Postal / ZIP Code', 'class': 'form-input', 'required': 'required'})
    )
    country = forms.CharField(
        max_length=100,
        required=False,
        initial='Bangladesh',
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    order_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'placeholder': 'Special delivery notes or PC assembly instructions...', 'rows': 3, 'class': 'form-textarea'})
    )
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        required=False,
        initial='COD'
    )
    save_address_to_profile = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
