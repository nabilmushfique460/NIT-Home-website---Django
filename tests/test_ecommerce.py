from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Category, Product, ProductReview
from orders.models import Order
from orders.services import OrderService
from payments.models import Payment
from accounts.models import EmailVerification, Notification
from accounts.services import OTPService
User = get_user_model()

class NITHomeECommerceTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Graphics Card', slug='gpu')
        self.product = Product.objects.create(category=self.category, name='NVIDIA GeForce RTX 4090', slug='nvidia-geforce-rtx-4090', brand='NVIDIA', price=Decimal('1599.99'), stock_qty=10, short_description='Flagship gaming graphics card.', long_description='In-depth specifications with Ada Lovelace architecture.', warranty='3 Years')
        self.user = User.objects.create_user(email='testuser@example.com', password='StrongPassword123!', first_name='Test', last_name='User', is_verified=True)

    def test_custom_user_creation_and_superuser(self):
        user = User.objects.create_user(email='normal@nithome.com', password='StrongPassword123!')
        self.assertEqual(user.email, 'normal@nithome.com')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('StrongPassword123!'))
        admin = User.objects.create_superuser(email='admin@nithome.com', password='AdminPassword123!')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_verified)

    def test_email_verification_model_otp_hashing(self):
        user = User.objects.create_user(email='otp_test@nithome.com', password='StrongPassword123!')
        plain_otp, record = EmailVerification.generate_otp(user)
        self.assertEqual(len(plain_otp), 6)
        self.assertTrue(plain_otp.isdigit())
        self.assertNotEqual(record.otp_hash, plain_otp)
        self.assertTrue(record.check_otp(plain_otp))
        self.assertFalse(record.check_otp('000000'))

    def test_signup_workflow_and_otp_generation(self):
        signup_url = reverse('accounts:signup')
        payload = {'email': 'newcustomer@nithome.com', 'first_name': 'New', 'last_name': 'Customer', 'phone': '+880 1711-223344', 'password': 'StrongPassword123!', 'confirm_password': 'StrongPassword123!'}
        response = self.client.post(signup_url, payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/verify_otp.html')
        new_user = User.objects.get(email='newcustomer@nithome.com')
        self.assertFalse(new_user.is_verified)
        self.assertEqual(new_user.first_name, 'New')
        verification = EmailVerification.objects.filter(user=new_user).first()
        self.assertIsNotNone(verification)

    def test_weak_passwords_are_rejected_on_signup(self):
        signup_url = reverse('accounts:signup')
        weak_passwords = ['short1!', 'lowercase123!', 'UPPERCASE123!', 'NoNumbersHere!', 'NoSpecialChar123']
        for weak_pass in weak_passwords:
            payload = {'email': f'weak_{len(weak_pass)}@nithome.com', 'first_name': 'Weak', 'last_name': 'Pass', 'password': weak_pass, 'confirm_password': weak_pass}
            res = self.client.post(signup_url, payload)
            self.assertEqual(res.status_code, 200)
            self.assertFalse(User.objects.filter(email=payload['email']).exists())

    def test_verify_otp_workflow(self):
        user = User.objects.create_user(email='verify_me@nithome.com', password='StrongPassword123!', is_verified=False)
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
        login_url = reverse('accounts:login')
        response = self.client.post(login_url, {'email': 'testuser@example.com', 'password': 'StrongPassword123!'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.client.logout()
        res_fail = self.client.post(login_url, {'email': 'testuser@example.com', 'password': 'wrongpassword'})
        self.assertEqual(res_fail.status_code, 200)
        self.assertContains(res_fail, 'Invalid email or password')

    def test_forgot_and_reset_password_workflow(self):
        forgot_url = reverse('accounts:forgot_password')
        response = self.client.post(forgot_url, {'email': 'testuser@example.com'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/reset_password.html')
        plain_otp, _ = EmailVerification.generate_otp(self.user)
        session = self.client.session
        session['reset_user_id'] = self.user.id
        session['reset_email'] = self.user.email
        session.save()
        reset_url = reverse('accounts:reset_password')
        reset_payload = {'otp': plain_otp, 'new_password': 'BrandNewPassword123!', 'confirm_new_password': 'BrandNewPassword123!'}
        res_reset = self.client.post(reset_url, reset_payload, follow=True)
        self.assertEqual(res_reset.status_code, 200)
        self.assertTemplateUsed(res_reset, 'accounts/login.html')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPassword123!'))

    def test_otp_rate_limiting_max_attempts(self):
        user = User.objects.create_user(email='ratelimit@nithome.com', password='StrongPassword123!')
        plain_otp, record = EmailVerification.generate_otp(user)
        for _ in range(5):
            self.assertFalse(record.check_otp('000000'))
        self.assertFalse(record.check_otp(plain_otp))

    def test_resend_otp_workflow(self):
        user = User.objects.create_user(email='resend@nithome.com', password='StrongPassword123!')
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
        user = User.objects.create_user(email='cooldown@nithome.com', password='StrongPassword123!')
        EmailVerification.generate_otp(user)
        session = self.client.session
        session['pending_otp_user_id'] = user.id
        session['pending_otp_email'] = user.email
        session.save()
        resend_url = reverse('accounts:resend_otp')
        response = self.client.post(resend_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please wait')
        can_resend, remaining = EmailVerification.can_resend_otp(user)
        self.assertFalse(can_resend)
        self.assertGreater(remaining, 0)

    def test_resend_reset_otp_workflow(self):
        session = self.client.session
        session['reset_user_id'] = self.user.id
        session['reset_email'] = self.user.email
        session.save()
        resend_reset_url = reverse('accounts:resend_reset_otp')
        response = self.client.post(resend_reset_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/reset_password.html')
        response_blocked = self.client.post(resend_reset_url, follow=True)
        self.assertContains(response_blocked, 'Please wait')

    def test_reset_password_with_invalid_otp_fails(self):
        session = self.client.session
        session['reset_user_id'] = self.user.id
        session['reset_email'] = self.user.email
        session.save()
        reset_url = reverse('accounts:reset_password')
        payload = {'otp': '999999', 'new_password': 'SomeNewPassword123!', 'confirm_new_password': 'SomeNewPassword123!'}
        res = self.client.post(reset_url, payload, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Invalid or expired OTP code')
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('SomeNewPassword123!'))

    def test_product_list_view(self):
        response = self.client.get(reverse('products:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NVIDIA GeForce RTX 4090')
        self.assertContains(response, 'N-IT HOME')

    def test_product_detail_view(self):
        response = self.client.get(reverse('products:product_detail', kwargs={'slug': self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Technical Specifications')
        self.assertContains(response, 'Add to Cart')
        self.assertContains(response, 'Buy Now')

    def test_cart_workflow(self):
        add_url = reverse('cart:cart_add', kwargs={'product_id': self.product.id})
        response = self.client.post(add_url, {'quantity': 2}, follow=True)
        self.assertEqual(response.status_code, 200)
        cart_url = reverse('cart:cart_detail')
        response = self.client.get(cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NVIDIA GeForce RTX 4090')
        self.assertContains(response, '3199.98')
        update_url = reverse('cart:cart_update', kwargs={'product_id': self.product.id})
        response = self.client.post(update_url, {'action': 'decrease'}, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_checkout_cod_order_creation_and_step_advancement(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:cart_add', kwargs={'product_id': self.product.id}), {'quantity': 1})
        checkout_url = reverse('orders:checkout')
        payload = {'full_name': 'Nabil Hasan', 'email': self.user.email, 'phone': '+880 1812345678', 'street_address': 'House 10, Road 4, Banani', 'city': 'Dhaka', 'state_or_division': 'Dhaka Division', 'postal_code': '1213'}
        response = self.client.post(checkout_url, payload, follow=True)
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(email=self.user.email)
        cod_res = self.client.post(reverse('payments:choose_payment', kwargs={'order_number': order.order_number}), {'payment_method': 'COD'}, follow=True)
        self.assertEqual(cod_res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'PENDING')
        self.assertEqual(order.status_step_index, 1)

        OrderService.advance_order_status(order, 'CONFIRMED')
        order.refresh_from_db()
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertEqual(order.status_step_index, 2)

        OrderService.advance_order_status(order, 'PACKAGING')
        order.refresh_from_db()
        self.assertEqual(order.status, 'PACKAGING')
        self.assertEqual(order.status_step_index, 3)

        OrderService.advance_order_status(order, 'SHIPPED')
        order.refresh_from_db()
        self.assertEqual(order.status, 'SHIPPED')
        self.assertEqual(order.status_step_index, 4)

        OrderService.advance_order_status(order, 'DELIVERED')
        order.refresh_from_db()
        self.assertEqual(order.status, 'DELIVERED')
        self.assertEqual(order.status_step_index, 5)
        self.assertTrue(order.is_paid)

        notifications = Notification.objects.filter(user=self.user)
        self.assertGreaterEqual(notifications.count(), 5)

    def test_product_review_and_order_cancellation(self):
        self.client.force_login(self.user)
        rev_url = reverse('products:add_review', kwargs={'slug': self.product.slug})
        rev_res = self.client.post(rev_url, {'author_name': 'Test User', 'author_email': self.user.email, 'rating': '5', 'title': 'Great GPU', 'comment': 'Super fast performance.'}, follow=True)
        self.assertEqual(rev_res.status_code, 200)
        self.assertTrue(ProductReview.objects.filter(product=self.product, title='Great GPU').exists())

        self.client.post(reverse('cart:cart_add', kwargs={'product_id': self.product.id}), {'quantity': 1})
        self.client.post(reverse('orders:checkout'), {'full_name': 'Test User', 'email': self.user.email, 'phone': '+880 1812345678', 'street_address': 'House 10, Road 4', 'city': 'Dhaka', 'postal_code': '1213'}, follow=True)
        order = Order.objects.latest('id')
        self.client.post(reverse('payments:choose_payment', kwargs={'order_number': order.order_number}), {'payment_method': 'COD'}, follow=True)
        self.product.refresh_from_db()
        stock_before_cancel = self.product.stock_qty

        cancel_res = self.client.post(reverse('orders:order_cancel', kwargs={'order_number': order.order_number}), follow=True)
        self.assertEqual(cancel_res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'CANCEL_REQUESTED')

        OrderService.approve_order_cancellation(order)
        order.refresh_from_db()
        self.assertEqual(order.status, 'CANCELLED')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, stock_before_cancel + 1)
