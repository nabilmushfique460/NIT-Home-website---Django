from django.urls import path
from .views import (
    SignUpView, LoginView, LogoutView, VerifyOTPView, ResendOTPView,
    ForgotPasswordView, ResetPasswordView, ProfileView, AddressDeleteView,
    GoogleOAuthSimulateView
)

app_name = 'accounts'

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('address/<int:pk>/delete/', AddressDeleteView.as_view(), name='delete_address'),
    path('google-oauth/', GoogleOAuthSimulateView.as_view(), name='google_oauth'),
]
