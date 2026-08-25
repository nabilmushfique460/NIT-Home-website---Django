from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import FormView
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.conf import settings
from .forms import (
    SignUpForm, LoginForm, OTPVerificationForm, 
    ForgotPasswordForm, ResetPasswordForm, ProfileForm, AddressForm
)
from .models import Address, EmailVerification
from .services import OTPService

User = get_user_model()


class SignUpView(FormView):
    """User registration with email verification flow."""
    template_name = 'accounts/signup.html'
    form_class = SignUpForm
    success_url = reverse_lazy('accounts:verify_otp')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.is_active = True
        user.is_verified = False
        user.save()

        # Update profile contact details
        phone = form.cleaned_data.get('phone')
        if phone and hasattr(user, 'profile'):
            user.profile.phone = phone
            user.profile.save()

        # Generate & email hashed OTP
        OTPService.create_and_send_otp(user, purpose='Account Verification')

        # Set pending session variables for verification
        self.request.session['pending_otp_user_id'] = user.id
        self.request.session['pending_otp_email'] = user.email

        messages.success(
            self.request,
            f"Account created! We've sent a 6-digit verification code to {user.email}. Please check your email inbox."
        )
        return super().form_valid(form)


class VerifyOTPView(FormView):
    """OTP Verification View for email activation."""
    template_name = 'accounts/verify_otp.html'
    form_class = OTPVerificationForm
    success_url = reverse_lazy('products:product_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.session.get('pending_otp_user_id')
        user = User.objects.filter(id=user_id).first() if user_id else None
        
        context['pending_user'] = user
        context['email'] = self.request.session.get('pending_otp_email') or (user.email if user else '')
        
        if user:
            can_resend, remaining = EmailVerification.can_resend_otp(user)
            context['resend_cooldown'] = remaining
        else:
            context['resend_cooldown'] = 0
        return context

    def form_valid(self, form):
        user_id = self.request.session.get('pending_otp_user_id')
        if not user_id:
            messages.error(self.request, "Verification session expired. Please sign up or log in again.")
            return redirect('accounts:signup')

        user = get_object_or_404(User, id=user_id)
        otp_code = form.cleaned_data['otp']

        if OTPService.verify_user_otp(user, otp_code):
            user.is_verified = True
            user.save(update_fields=['is_verified'])
            
            # Auto-login after successful verification
            login(self.request, user)
            
            # Clear pending session keys
            self.request.session.pop('pending_otp_user_id', None)
            self.request.session.pop('pending_otp_email', None)
            
            messages.success(self.request, f"Welcome to N-IT Home, {user.first_name or user.email}! Your account is now verified.")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Invalid or expired OTP code. Please check your email and enter the correct 6-digit code.")
            return self.form_invalid(form)


class ResendOTPView(View):
    """Resend OTP code for pending verification session with 60-second cooldown."""
    def post(self, request, *args, **kwargs):
        user_id = request.session.get('pending_otp_user_id')
        if not user_id:
            messages.error(request, "No active verification session found. Please log in or sign up.")
            return redirect('accounts:login')

        user = get_object_or_404(User, id=user_id)
        can_resend, remaining = EmailVerification.can_resend_otp(user)
        if not can_resend:
            messages.warning(request, f"Please wait {remaining} seconds before requesting a new OTP.")
            return redirect('accounts:verify_otp')

        OTPService.create_and_send_otp(user, purpose='Account Verification')
        messages.info(request, f"A fresh 6-digit verification OTP has been sent to {user.email}.")
        return redirect('accounts:verify_otp')


class LoginView(FormView):
    """User authentication view using email and password."""
    template_name = 'accounts/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        email = form.cleaned_data['email'].strip().lower()
        password = form.cleaned_data['password']

        user = authenticate(self.request, email=email, password=password)
        if not user:
            # Fallback for backends expecting username keyword argument
            user = authenticate(self.request, username=email, password=password)

        if user:
            if not user.is_verified:
                # Prompt user to verify email if unverified (respect 60s cooldown)
                can_resend, _ = EmailVerification.can_resend_otp(user)
                if can_resend:
                    OTPService.create_and_send_otp(user, purpose='Account Verification')

                self.request.session['pending_otp_user_id'] = user.id
                self.request.session['pending_otp_email'] = user.email

                messages.warning(self.request, f"Please verify your email address to continue. An OTP has been sent to {user.email}.")
                return redirect('accounts:verify_otp')

            login(self.request, user)
            messages.success(self.request, f"Welcome back, {user.first_name or user.email}!")
            next_url = self.request.GET.get('next') or self.get_success_url()
            return redirect(next_url)
        else:
            messages.error(self.request, "Invalid email address or password. Please verify your credentials.")
            return self.form_invalid(form)


class LogoutView(View):
    """User logout view."""
    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been securely signed out.")
        return redirect('products:product_list')

    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been securely signed out.")
        return redirect('products:product_list')


class ForgotPasswordView(FormView):
    """Password reset request view."""
    template_name = 'accounts/forgot_password.html'
    form_class = ForgotPasswordForm
    success_url = reverse_lazy('accounts:reset_password')

    def form_valid(self, form):
        email = form.cleaned_data['email'].strip().lower()
        user = User.objects.filter(email__iexact=email).first()

        if user:
            can_resend, _ = EmailVerification.can_resend_otp(user)
            if can_resend:
                OTPService.create_and_send_otp(user, purpose='Password Reset')

            self.request.session['reset_password_user_id'] = user.id
            self.request.session['reset_password_email'] = user.email
            messages.success(self.request, f"A 6-digit password reset OTP has been sent to {email}. Please check your email.")
        else:
            # Generic response to prevent user enumeration
            messages.info(self.request, f"If an account with {email} exists, an OTP code has been sent.")

        return super().form_valid(form)


class ResetPasswordView(FormView):
    """Password reset completion view verifying OTP before setting new password."""
    template_name = 'accounts/reset_password.html'
    form_class = ResetPasswordForm
    success_url = reverse_lazy('accounts:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.session.get('reset_password_user_id')
        user = User.objects.filter(id=user_id).first() if user_id else None
        context['reset_email'] = self.request.session.get('reset_password_email')
        
        if user:
            can_resend, remaining = EmailVerification.can_resend_otp(user)
            context['resend_cooldown'] = remaining
        else:
            context['resend_cooldown'] = 0
        return context

    def form_valid(self, form):
        user_id = self.request.session.get('reset_password_user_id')
        if not user_id:
            messages.error(self.request, "Password reset session has expired. Please request a new OTP.")
            return redirect('accounts:forgot_password')

        user = get_object_or_404(User, id=user_id)
        otp_code = form.cleaned_data['otp']
        new_password = form.cleaned_data['new_password']

        if OTPService.verify_user_otp(user, otp_code):
            user.set_password(new_password)
            user.is_verified = True
            user.save()

            # Clear reset session data
            self.request.session.pop('reset_password_user_id', None)
            self.request.session.pop('reset_password_email', None)

            messages.success(self.request, "Your password has been reset successfully! Please sign in with your new password.")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Invalid or expired OTP code. Please check your email and enter the correct code.")
            return self.form_invalid(form)


class ResendResetOTPView(View):
    """Resend password reset OTP with 60-second cooldown."""
    def post(self, request, *args, **kwargs):
        user_id = request.session.get('reset_password_user_id')
        if not user_id:
            messages.error(request, "No active password reset session found. Please request a reset.")
            return redirect('accounts:forgot_password')

        user = get_object_or_404(User, id=user_id)
        can_resend, remaining = EmailVerification.can_resend_otp(user)
        if not can_resend:
            messages.warning(request, f"Please wait {remaining} seconds before requesting a new OTP.")
            return redirect('accounts:reset_password')

        OTPService.create_and_send_otp(user, purpose='Password Reset')
        messages.info(request, f"A fresh 6-digit password reset OTP has been sent to {user.email}.")
        return redirect('accounts:reset_password')


class ProfileView(LoginRequiredMixin, View):
    """Customer profile and shipping address management."""
    def get(self, request, *args, **kwargs):
        user = request.user
        profile_form = ProfileForm(
            instance=user.profile,
            initial={'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email}
        )
        address_form = AddressForm()
        addresses = Address.objects.filter(user=user)
        recent_orders = user.orders.all().order_by('-created_at')[:5] if hasattr(user, 'orders') else []

        return render(request, 'accounts/profile.html', {
            'profile_form': profile_form,
            'address_form': address_form,
            'addresses': addresses,
            'recent_orders': recent_orders,
            'title': 'My Account Profile',
        })

    def post(self, request, *args, **kwargs):
        user = request.user
        action = request.POST.get('action')

        if action == 'update_profile':
            profile_form = ProfileForm(request.POST, instance=user.profile)
            if profile_form.is_valid():
                profile_form.save()
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                user.save()
                messages.success(request, "Profile updated successfully.")
            else:
                messages.error(request, "Failed to update profile. Please check your inputs.")

        elif action == 'add_address':
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                addr = address_form.save(commit=False)
                addr.user = user
                addr.save()
                messages.success(request, "New shipping address saved.")
            else:
                messages.error(request, "Please correct the shipping address form errors.")

        return redirect('accounts:profile')


class AddressDeleteView(LoginRequiredMixin, View):
    """Delete saved shipping address."""
    def post(self, request, pk, *args, **kwargs):
        address = get_object_or_404(Address, id=pk, user=request.user)
        address.delete()
        messages.success(request, "Address removed successfully.")
        return redirect('accounts:profile')
