"""
Comprehensive automated tests for N-IT Home E-Commerce platform.
Validates Custom User model, EmailVerification OTP hashing & verification,
Strong Password enforcement, SignUp, Login, Forgot & Reset Password, Cart, and Order flows.
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Category, Product
from orders.models import Order
from payments.models import Payment
from accounts.models import EmailVerification
from accounts.services import OTPService

User = get_user_model()


class NITHomeECommerceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Graphics Card", slug="gpu")
        self.product = Product.objects.create(
            category=self.category,
            name="NVIDIA GeForce RTX 4090",
            slug="nvidia-geforce-rtx-4090",
            brand="NVIDIA",
            price=Decimal("1599.99"),
            stock_qty=10,
            short_description="Flagship gaming graphics card.",
            long_description="In-depth specifications with Ada Lovelace architecture.",
            warranty="3 Years"
        )
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="StrongPassword123!",
            first_name="Test",
            last_name="User",
            is_verified=True
        )

    def test_custom_user_creation_and_superuser(self):
        """Test User manager create_user and create_superuser methods."""
        user = User.objects.create_user(email="normal@nithome.com", password="StrongPassword123!")
        self.assertEqual(user.email, "normal@nithome.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("StrongPassword123!"))

        admin = User.objects.create_superuser(email="admin@nithome.com", password="AdminPassword123!")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_verified)

    def test_email_verification_model_otp_hashing(self):
        """Test that EmailVerification stores hashed OTP and checks securely."""
        user = User.objects.create_user(email="otp_test@nithome.com", password="StrongPassword123!")
        plain_otp, record = EmailVerification.generate_otp(user)
        
        self.assertEqual(len(plain_otp), 6)
        self.assertTrue(plain_otp.isdigit())
        # Hash should not equal plain OTP
        self.assertNotEqual(record.otp_hash, plain_otp)
        # Check valid OTP
        self.assertTrue(record.check_otp(plain_otp))
        # Check invalid OTP
        self.assertFalse(record.check_otp("000000"))

    def test_signup_workflow_and_otp_generation(self):
        """Test user sign up creates pending user and generates OTP."""
        signup_url = reverse('accounts:signup')
        payload = {
            'email': 'newcustomer@nithome.com',
            'first_name': 'New',
            'last_name': 'Customer',
            'phone': '+880 1711-223344',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        response = self.client.post(signup_url, payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/verify_otp.html')

        # Verify user created in DB as unverified
        new_user = User.objects.get(email='newcustomer@nithome.com')
        self.assertFalse(new_user.is_verified)
        self.assertEqual(new_user.first_name, 'New')

        # Verify EmailVerification record exists
        verification = EmailVerification.objects.filter(user=new_user).first()
        self.assertIsNotNone(verification)

    def test_weak_passwords_are_rejected_on_signup(self):
        """Test that weak passwords missing uppercase, lowercase, number, or special char are rejected."""
        signup_url = reverse('accounts:signup')
        
        weak_passwords = [
            'short1!',          # Under 8 chars
            'lowercase123!',    # Missing uppercase
            'UPPERCASE123!',    # Missing lowercase
            'NoNumbersHere!',   # Missing number
            'NoSpecialChar123'  # Missing special character
        ]
        
        for weak_pass in weak_passwords:
            payload = {
                'email': f'weak_{len(weak_pass)}@nithome.com',
                'first_name': 'Weak',
                'last_name': 'Pass',
                'password': weak_pass,
                'confirm_password': weak_pass
            }
            res = self.client.post(signup_url, payload)
            self.assertEqual(res.status_code, 200)
            self.assertFalse(User.objects.filter(email=payload['email']).exists())

    def test_verify_otp_workflow(self):
        """Test verifying OTP activates user account and establishes session."""
        user = User.objects.create_user(email="verify_me@nithome.com", password="StrongPassword123!", is_verified=False)
        plain_otp, _ = OTPService.create_and_send_otp(user, purpose='Verification')

        session = self.client.session
        session['pending_otp_user_id'] = user.id
        session['pending_otp_email'] = user.email
        session.save()

        verify_url = reverse('accounts:verify_otp')
        response = self.client.post(verify_url, {'otp': plain_otp}, follow=True)
        self.assertEqual(response.status_code, 200)

        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_login_workflow(self):
        """Test email-based authentication."""
        login_url = reverse('accounts:login')
        
        # Valid login for verified user
        response = self.client.post(login_url, {'email': 'testuser@example.com', 'password': 'StrongPassword123!'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)

        # Invalid login
        self.client.logout()
        res_fail = self.client.post(login_url, {'email': 'testuser@example.com', 'password': 'wrongpassword'})
        self.assertEqual(res_fail.status_code, 200)
        self.assertContains(res_fail, "Invalid email address or password")

    def test_forgot_and_reset_password_workflow(self):
        """Test forgot password sends OTP and reset password updates password after OTP check."""
        # 1. Request forgot password OTP
        forgot_url = reverse('accounts:forgot_password')
        response = self.client.post(forgot_url, {'email': 'testuser@example.com'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/reset_password.html')

        # Retrieve generated OTP
        verification = EmailVerification.objects.get(user=self.user)
        plain_otp, _ = EmailVerification.generate_otp(self.user)

        session = self.client.session
        session['reset_password_user_id'] = self.user.id
        session['reset_password_email'] = self.user.email
        session.save()

        # 2. Submit new password with OTP
        reset_url = reverse('accounts:reset_password')
        reset_payload = {
            'otp': plain_otp,
            'new_password': 'BrandNewPassword123!',
            'confirm_new_password': 'BrandNewPassword123!'
        }
        res_reset = self.client.post(reset_url, reset_payload, follow=True)
        self.assertEqual(res_reset.status_code, 200)
        self.assertTemplateUsed(res_reset, 'accounts/login.html')

        # Verify new password works
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPassword123!'))

    def test_unverified_user_login_prompts_otp(self):
        """Test unverified user logging in is prompted to verify OTP."""
        unverified_user = User.objects.create_user(email="notverified@nithome.com", password="StrongPassword123!", is_verified=False)
        login_url = reverse('accounts:login')
        response = self.client.post(login_url, {'email': 'notverified@nithome.com', 'password': 'StrongPassword123!'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/verify_otp.html')

    def test_otp_rate_limiting_max_attempts(self):
        """Test that after 5 failed attempts, OTP verification fails permanently."""
        user = User.objects.create_user(email="ratelimit@nithome.com", password="StrongPassword123!")
        plain_otp, record = EmailVerification.generate_otp(user)
        
        # 5 wrong attempts
        for _ in range(5):
            self.assertFalse(record.check_otp("000000"))
        
        # 6th attempt even with correct OTP should fail
        self.assertFalse(record.check_otp(plain_otp))

    def test_resend_otp_workflow(self):
        """Test resending OTP generates new code."""
        user = User.objects.create_user(email="resend@nithome.com", password="StrongPassword123!")
        session = self.client.session
        session['pending_otp_user_id'] = user.id
        session['pending_otp_email'] = user.email
        session.save()

        resend_url = reverse('accounts:resend_otp')
        response = self.client.post(resend_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/verify_otp.html')
        self.assertTrue(EmailVerification.objects.filter(user=user).exists())

    def test_resend_otp_cooldown_enforcement(self):
        """Test that resend OTP blocks requests made within 60 seconds."""
        user = User.objects.create_user(email="cooldown@nithome.com", password="StrongPassword123!")
        EmailVerification.generate_otp(user)

        session = self.client.session
        session['pending_otp_user_id'] = user.id
        session['pending_otp_email'] = user.email
        session.save()

        # Immediate resend attempt should be blocked by cooldown
        resend_url = reverse('accounts:resend_otp')
        response = self.client.post(resend_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please wait")

        # Check can_resend_otp returns False
        can_resend, remaining = EmailVerification.can_resend_otp(user)
        self.assertFalse(can_resend)
        self.assertGreater(remaining, 0)

    def test_resend_reset_otp_workflow(self):
        """Test resending password reset OTP with cooldown."""
        session = self.client.session
        session['reset_password_user_id'] = self.user.id
        session['reset_password_email'] = self.user.email
        session.save()

        resend_reset_url = reverse('accounts:resend_reset_otp')
        response = self.client.post(resend_reset_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/reset_password.html')

        # Immediate second attempt blocked by cooldown
        response_blocked = self.client.post(resend_reset_url, follow=True)
        self.assertContains(response_blocked, "Please wait")

    def test_reset_password_with_invalid_otp_fails(self):
        """Test reset password fails when invalid OTP is provided."""
        session = self.client.session
        session['reset_password_user_id'] = self.user.id
        session['reset_password_email'] = self.user.email
        session.save()

        reset_url = reverse('accounts:reset_password')
        payload = {
            'otp': '999999',
            'new_password': 'SomeNewPassword123!',
            'confirm_new_password': 'SomeNewPassword123!'
        }
        res = self.client.post(reset_url, payload, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Invalid or expired OTP code")
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('SomeNewPassword123!'))

    def test_product_list_view(self):
        """Test product listing and filtering."""
        response = self.client.get(reverse('products:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NVIDIA GeForce RTX 4090")
        self.assertContains(response, "N-IT")

    def test_product_detail_view(self):
        """Test product detail page renders."""
        response = self.client.get(reverse('products:product_detail', kwargs={'slug': self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Technical Specifications")
        self.assertContains(response, "Add to Cart")
        self.assertContains(response, "Buy Now")

    def test_cart_workflow(self):
        """Test adding item to cart, updating quantity, and viewing cart."""
        add_url = reverse('cart:cart_add', kwargs={'product_id': self.product.id})
        response = self.client.post(add_url, {'quantity': 2}, follow=True)
        self.assertEqual(response.status_code, 200)

        cart_url = reverse('cart:cart_detail')
        response = self.client.get(cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NVIDIA GeForce RTX 4090")
        self.assertContains(response, "3199.98")

        update_url = reverse('cart:cart_update', kwargs={'product_id': self.product.id})
        response = self.client.post(update_url, {'action': 'decrease'}, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_checkout_cod_order_creation(self):
        """Test creating an atomic COD order."""
        self.client.post(reverse('cart:cart_add', kwargs={'product_id': self.product.id}), {'quantity': 1})
        
        checkout_url = reverse('orders:checkout')
        payload = {
            'full_name': 'Nabil Hasan',
            'email': 'nabil@example.com',
            'phone': '+880 1812345678',
            'street_address': 'House 10, Road 4, Banani',
            'city': 'Dhaka',
            'state_or_division': 'Dhaka Division',
            'postal_code': '1213',
            'payment_method': 'COD',
        }
        response = self.client.post(checkout_url, payload, follow=True)
        self.assertEqual(response.status_code, 200)

        order = Order.objects.get(email='nabil@example.com')
        self.assertEqual(order.payment_method, 'COD')
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertFalse(order.is_paid)
        self.assertEqual(order.items.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, 9)

    def test_checkout_bkash_strategy_payment(self):
        """Test bKash payment strategy flow."""
        self.client.post(reverse('cart:cart_add', kwargs={'product_id': self.product.id}), {'quantity': 1})
        
        checkout_url = reverse('orders:checkout')
        payload = {
            'full_name': 'Imtiaz Ahmed',
            'email': 'imtiaz@example.com',
            'phone': '+880 1712345678',
            'street_address': 'Sector 3, Uttara',
            'city': 'Dhaka',
            'postal_code': '1230',
            'payment_method': 'BKASH',
        }
        response = self.client.post(checkout_url, payload, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/payments/bkash/', response.url)

        order = Order.objects.get(email='imtiaz@example.com')
        payment = Payment.objects.get(order=order)
        callback_url = reverse('payments:bkash_callback', kwargs={'transaction_id': payment.transaction_id})
        cb_res = self.client.post(callback_url, {'wallet_number': '01712345678', 'otp': '123456', 'pin': '12345'}, follow=True)
        self.assertEqual(cb_res.status_code, 200)

        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertTrue(order.is_paid)
        self.assertEqual(payment.status, 'SUCCESS')
