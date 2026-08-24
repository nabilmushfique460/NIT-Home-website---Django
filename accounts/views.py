from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import FormView, CreateView, UpdateView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from .forms import (
    SignUpForm, LoginForm, OTPVerificationForm, 
    ForgotPasswordForm, ResetPasswordForm, ProfileForm, AddressForm
)
from .models import Profile, EmailOTP, Address
from .services import OTPService

class SignUpView(FormView):
    """User registration Class-Based View."""
    template_name = 'accounts/signup.html'
    form_class = SignUpForm
    success_url = reverse_lazy('accounts:verify_otp')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.is_active = True
        user.save()

        # Update profile phone
        profile = user.profile
        profile.phone = form.cleaned_data.get('phone')
        profile.is_verified = False
        profile.save()

        # Generate & Send OTP
        otp = OTPService.create_otp(user, purpose='SIGNUP')

        # Store pending user ID in session for verification
        self.request.session['pending_otp_user_id'] = user.id
        self.request.session['pending_otp_purpose'] = 'SIGNUP'

        messages.success(
            self.request,
            f"Account created! We've sent a 6-digit OTP code to {user.email}. (Demo Code: {otp.code})"
        )
        return super().form_valid(form)

class VerifyOTPView(FormView):
    """OTP Verification Class-Based View."""
    template_name = 'accounts/verify_otp.html'
    form_class = OTPVerificationForm
    success_url = reverse_lazy('products:product_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.session.get('pending_otp_user_id')
        user = User.objects.filter(id=user_id).first() if user_id else None
        
        # Look up latest active OTP to display in sandbox notice
        latest_otp = None
        if user:
            latest_otp = EmailOTP.objects.filter(user=user, is_used=False).order_by('-created_at').first()
            
        context['pending_user'] = user
        context['latest_demo_otp'] = latest_otp.code if latest_otp else None
        return context

    def form_valid(self, form):
        user_id = self.request.session.get('pending_otp_user_id')
        purpose = self.request.session.get('pending_otp_purpose', 'SIGNUP')

        if not user_id:
            messages.error(self.request, "Session expired. Please sign up or log in again.")
            return redirect('accounts:signup')

        user = get_object_or_404(User, id=user_id)
        otp_code = form.cleaned_data['otp']

        if OTPService.verify_otp(user, otp_code, purpose=purpose):
            login(self.request, user)
            # Clear pending session keys
            self.request.session.pop('pending_otp_user_id', None)
            self.request.session.pop('pending_otp_purpose', None)
            messages.success(self.request, f"Welcome, {user.first_name or user.username}! Your email has been verified successfully.")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Invalid or expired OTP code. Please try again.")
            return self.form_invalid(form)

class ResendOTPView(View):
    """Resend OTP code Class-Based View."""
    def post(self, request, *args, **kwargs):
        user_id = request.session.get('pending_otp_user_id')
        purpose = request.session.get('pending_otp_purpose', 'SIGNUP')

        if not user_id:
            messages.error(request, "No pending verification session found.")
            return redirect('accounts:login')

        user = get_object_or_404(User, id=user_id)
        otp = OTPService.create_otp(user, purpose=purpose)
        messages.info(request, f"A fresh OTP code has been generated. (Demo Code: {otp.code})")
        return redirect('accounts:verify_otp')

class LoginView(FormView):
    """User authentication Class-Based View."""
    template_name = 'accounts/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        username_or_email = form.cleaned_data['username_or_email'].strip()
        password = form.cleaned_data['password']

        user = authenticate(self.request, username=username_or_email, password=password)
        if not user:
            # Check if username is an email
            user_obj = User.objects.filter(email__iexact=username_or_email).first()
            if user_obj:
                user = authenticate(self.request, username=user_obj.username, password=password)

        if user:
            login(self.request, user)
            messages.success(self.request, f"Welcome back, {user.first_name or user.username}!")
            next_url = self.request.GET.get('next') or self.get_success_url()
            return redirect(next_url)
        else:
            messages.error(self.request, "Invalid username/email or password.")
            return self.form_invalid(form)

class LogoutView(View):
    """User logout Class-Based View."""
    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been logged out safely.")
        return redirect('products:product_list')

    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been logged out safely.")
        return redirect('products:product_list')

class ForgotPasswordView(FormView):
    """Password reset initiation Class-Based View."""
    template_name = 'accounts/forgot_password.html'
    form_class = ForgotPasswordForm
    success_url = reverse_lazy('accounts:reset_password')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = User.objects.filter(email__iexact=email).first()

        if user:
            otp = OTPService.create_otp(user, purpose='RESET')
            self.request.session['reset_password_user_id'] = user.id
            messages.success(self.request, f"Password reset OTP sent to {email}. (Demo Code: {otp.code})")
        else:
            # Mask user existence for security
            messages.info(self.request, f"If an account with {email} exists, an OTP code has been sent.")

        return super().form_valid(form)

class ResetPasswordView(FormView):
    """Password reset completion Class-Based View."""
    template_name = 'accounts/reset_password.html'
    form_class = ResetPasswordForm
    success_url = reverse_lazy('accounts:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.session.get('reset_password_user_id')
        user = User.objects.filter(id=user_id).first() if user_id else None
        latest_otp = None
        if user:
            latest_otp = EmailOTP.objects.filter(user=user, purpose='RESET', is_used=False).order_by('-created_at').first()
        context['latest_demo_otp'] = latest_otp.code if latest_otp else None
        return context

    def form_valid(self, form):
        user_id = self.request.session.get('reset_password_user_id')
        if not user_id:
            messages.error(self.request, "Password reset session has expired.")
            return redirect('accounts:forgot_password')

        user = get_object_or_404(User, id=user_id)
        otp_code = form.cleaned_data['otp']
        new_password = form.cleaned_data['new_password']

        if OTPService.verify_otp(user, otp_code, purpose='RESET'):
            user.set_password(new_password)
            user.save()
            self.request.session.pop('reset_password_user_id', None)
            messages.success(self.request, "Your password has been reset successfully! Please log in.")
            return super().form_valid(form)
        else:
            messages.error(self.request, "Invalid or expired OTP code.")
            return self.form_invalid(form)

class ProfileView(LoginRequiredMixin, View):
    """Customer profile and addresses management Class-Based View."""
    def get(self, request, *args, **kwargs):
        user = request.user
        profile_form = ProfileForm(
            instance=user.profile,
            initial={'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email}
        )
        address_form = AddressForm()
        addresses = Address.objects.filter(user=user)
        recent_orders = user.orders.all().order_by('-created_at')[:5]

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
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.save()
                messages.success(request, "Profile updated successfully.")
            else:
                messages.error(request, "Failed to update profile. Please verify your inputs.")

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

class GoogleOAuthSimulateView(View):
    """OAuth 2.0 Google Account Sign-In / Flow."""
    def get(self, request, *args, **kwargs):
        # Render Google OAuth consent / account selection screen
        return render(request, 'accounts/google_oauth.html', {
            'title': 'Sign in with Google - N-IT Home'
        })

    def post(self, request, *args, **kwargs):
        google_email = request.POST.get('email', 'google.user@example.com')
        full_name = request.POST.get('name', 'Google Customer')
        
        # Look up or create user with this Google account
        username = google_email.split('@')[0]
        user, created = User.objects.get_or_create(
            email=google_email,
            defaults={
                'username': f"google_{username}",
                'first_name': full_name.split()[0] if full_name else 'Google',
                'last_name': " ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else 'User',
            }
        )
        if created:
            user.set_unusable_password()
            user.save()
            user.profile.is_verified = True
            user.profile.save()

        login(request, user)
        messages.success(request, f"Successfully authenticated via Google as {user.email}!")
        return redirect('products:product_list')
