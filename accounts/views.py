from typing import Any
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import FormView, ListView
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpRequest
from .forms import (
    SignUpForm,
    LoginForm,
    OTPVerificationForm,
    ForgotPasswordForm,
    ResetPasswordForm,
    ProfileForm,
    AddressForm
)
from .models import Address, EmailVerification, Notification, Profile
from .services import OTPService

User = get_user_model()

# View handling user registration and verification OTP dispatch
class SignUpView(FormView):
    template_name = 'accounts/signup.html'
    form_class = SignUpForm
    success_url = reverse_lazy('accounts:verify_otp')

    def form_valid(self, form: SignUpForm) -> HttpResponse:
        # Create unverified user instance with encrypted password
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.is_active = True
        user.is_verified = False
        user.save()

        # Update profile phone if provided during registration
        phone = form.cleaned_data.get('phone')
        if phone and hasattr(user, 'profile'):
            user.profile.phone = phone
            user.profile.save()

        # Generate and dispatch verification OTP
        OTPService.create_and_send_otp(user, purpose='Account Verification')

        # Store pending session attributes for OTP verification step
        self.request.session['pending_otp_user_id'] = user.id
        self.request.session['pending_otp_email'] = user.email

        messages.success(
            self.request,
            f"Account created! We've sent a 6-digit verification code to {user.email}. Please check your email inbox."
        )
        return super().form_valid(form)

# View handling OTP verification and automatic user login upon success
class VerifyOTPView(FormView):
    template_name = 'accounts/verify_otp.html'
    form_class = OTPVerificationForm
    success_url = reverse_lazy('products:product_list')

    def get_context_data(self, **kwargs) -> dict[str, Any]:
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

    def form_valid(self, form: OTPVerificationForm) -> HttpResponse:
        user_id = self.request.session.get('pending_otp_user_id')
        if not user_id:
            messages.error(self.request, 'Verification session expired. Please sign up or log in again.')
            return redirect('accounts:signup')

        user = get_object_or_404(User, id=user_id)
        otp_code = form.cleaned_data['otp']

        # Verify submitted OTP code against stored hash
        if OTPService.verify_user_otp(user, otp_code):
            user.is_verified = True
            user.save(update_fields=['is_verified'])

            # Log user into the session
            login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')

            # Clean up pending session state
            self.request.session.pop('pending_otp_user_id', None)
            self.request.session.pop('pending_otp_email', None)

            # Create welcoming notification
            Notification.objects.create(
                user=user,
                title="Welcome to N-IT HOME!",
                message="Your account has been successfully verified. Welcome to our enthusiast hardware store!",
                link="/products/"
            )
            messages.success(
                self.request,
                f"Email verified successfully! Welcome to N-IT HOME, {user.get_full_name()}."
            )
            return redirect('products:product_list')
        else:
            messages.error(self.request, 'Invalid or expired verification code. Please check and try again.')
            return self.form_invalid(form)

# View handling OTP resend requests with cooldown validation
class ResendOTPView(View):

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user_id = request.session.get('pending_otp_user_id')
        if not user_id:
            messages.error(request, 'Session expired. Please sign up or log in again.')
            return redirect('accounts:signup')

        user = get_object_or_404(User, id=user_id)
        success, message, _ = OTPService.resend_otp(user)
        if success:
            messages.success(request, f"A new verification code has been sent to {user.email}.")
        else:
            messages.warning(request, message)
        return redirect('accounts:verify_otp')

# View handling user authentication and session establishment
class LoginView(FormView):
    template_name = 'accounts/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('products:product_list')

    def get_success_url(self) -> str:
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        return next_url if next_url else str(reverse_lazy('products:product_list'))

    def form_valid(self, form: LoginForm) -> HttpResponse:
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        remember_me = form.cleaned_data.get('remember_me', False)

        # Authenticate user credentials
        user = authenticate(self.request, username=email, password=password)
        if user is None:
            user_check = User.objects.filter(email=email).first()
            if user_check and user_check.check_password(password):
                user = user_check

        if user is not None:
            if not user.is_active:
                messages.error(self.request, 'This account has been deactivated. Please contact support.')
                return self.form_invalid(form)

            login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')

            # Configure session expiration based on remember me preference
            if not remember_me:
                self.request.session.set_expiry(0)
            else:
                self.request.session.set_expiry(60 * 60 * 24 * 14)

            messages.success(self.request, f"Welcome back, {user.get_full_name()}!")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, 'Invalid email or password. Please try again.')
            return self.form_invalid(form)

# View handling user signout and session termination
class LogoutView(View):

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        logout(request)
        messages.info(request, 'You have been signed out safely. Come back soon!')
        return redirect('products:product_list')

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return self.post(request, *args, **kwargs)

# View handling initial password reset request by email
class ForgotPasswordView(FormView):
    template_name = 'accounts/forgot_password.html'
    form_class = ForgotPasswordForm
    success_url = reverse_lazy('accounts:reset_password')

    def form_valid(self, form: ForgotPasswordForm) -> HttpResponse:
        email = form.cleaned_data['email']
        user = User.objects.filter(email=email).first()
        if user:
            OTPService.create_and_send_otp(user, purpose='Password Reset')
            self.request.session['reset_user_id'] = user.id
            self.request.session['reset_email'] = user.email
        else:
            self.request.session['reset_email'] = email

        messages.info(
            self.request,
            f"If an account exists with {email}, a 6-digit password reset code has been dispatched."
        )
        return super().form_valid(form)

# View handling password reset verification and new password setting
class ResetPasswordView(FormView):
    template_name = 'accounts/reset_password.html'
    form_class = ResetPasswordForm
    success_url = reverse_lazy('accounts:login')

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['email'] = self.request.session.get('reset_email', '')
        user_id = self.request.session.get('reset_user_id')
        if user_id:
            user = User.objects.filter(id=user_id).first()
            if user:
                can_resend, remaining = EmailVerification.can_resend_otp(user)
                context['resend_cooldown'] = remaining
        return context

    def form_valid(self, form: ResetPasswordForm) -> HttpResponse:
        user_id = self.request.session.get('reset_user_id')
        if not user_id:
            messages.error(self.request, 'Password reset session expired. Please submit your request again.')
            return redirect('accounts:forgot_password')

        user = get_object_or_404(User, id=user_id)
        otp = form.cleaned_data['otp']
        new_password = form.cleaned_data['new_password']

        # Validate provided OTP code
        if not OTPService.verify_user_otp(user, otp):
            messages.error(self.request, 'Invalid or expired OTP code. Please try again.')
            return self.form_invalid(form)

        # Update user password
        user.set_password(new_password)
        user.save()

        # Clean up reset session attributes
        self.request.session.pop('reset_user_id', None)
        self.request.session.pop('reset_email', None)

        messages.success(self.request, 'Your password has been successfully reset! You can now log in.')
        return super().form_valid(form)

# View handling password reset OTP resend requests
class ResendResetOTPView(View):

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user_id = request.session.get('reset_user_id')
        if not user_id:
            messages.error(request, 'Session expired. Please request a new password reset.')
            return redirect('accounts:forgot_password')

        user = get_object_or_404(User, id=user_id)
        success, message, _ = OTPService.resend_otp(user, purpose='Password Reset')
        if success:
            messages.success(request, f"A new reset code has been sent to {user.email}.")
        else:
            messages.warning(request, message)
        return redirect('accounts:reset_password')

# View managing customer profile, personal info, and saved shipping addresses
class ProfileView(LoginRequiredMixin, View):

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)
        user_form = ProfileForm(
            instance=profile,
            initial={
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
        )
        address_form = AddressForm()
        addresses = Address.objects.filter(user=user)
        recent_orders = user.orders.all()[:5]

        return render(
            request,
            'accounts/profile.html',
            {
                'user_form': user_form,
                'address_form': address_form,
                'addresses': addresses,
                'recent_orders': recent_orders,
                'title': 'My Profile & Account Settings'
            }
        )

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)
        action = request.POST.get('action')

        if action == 'update_profile':
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.save(update_fields=['first_name', 'last_name'])
            profile_form = ProfileForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully.')
            else:
                messages.error(request, 'Failed to update profile. Please check your inputs.')

        elif action == 'add_address':
            address_form = AddressForm(request.POST)
            if address_form.is_valid():
                addr = address_form.save(commit=False)
                addr.user = user
                addr.save()
                messages.success(request, 'New shipping address saved.')
            else:
                messages.error(request, 'Please correct the shipping address form errors.')

        return redirect('accounts:profile')

# View handling deletion of saved customer shipping address
class AddressDeleteView(LoginRequiredMixin, View):

    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        address = get_object_or_404(Address, id=pk, user=request.user)
        address.delete()
        messages.success(request, 'Address removed successfully.')
        return redirect('accounts:profile')

# View rendering user notifications with pagination
class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'accounts/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 15

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['title'] = 'Notifications'
        # Mark all unread notifications as read when opening notification list
        Notification.objects.filter(user=self.request.user, is_read=False).update(is_read=True)
        return context

# View handling individual notification read state and redirecting to target link
class NotificationMarkReadView(LoginRequiredMixin, View):

    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        notification = get_object_or_404(Notification, id=pk, user=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        if notification.link:
            return redirect(notification.link)
        return redirect('accounts:notifications')
