from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from products.models import Category, Product, ProductReview, ProductSpecification
from orders.models import Order
from orders.services import OrderService
from accounts.models import EmailVerification, Notification
from accounts.services import OTPService
from core.models import ContactMessage
from core.services import ContactService

User = get_user_model()

# Comprehensive test suite covering accounts, products, cart, checkout, orders, and payments
class NITHomeECommerceTests(TestCase):

    def setUp(self):
        self.client = Client()

        # Seed categories
        self.category = Category.objects.create(name='Graphics Card', slug='gpu')
        self.cpu_category = Category.objects.create(name='Processor', slug='cpu')
        self.ram_category = Category.objects.create(name='Memory', slug='ram')
        self.ssd_category = Category.objects.create(name='Storage', slug='ssd')

        # Seed GPU product
        self.product = Product.objects.create(
            category=self.category,
            name='NVIDIA GeForce RTX 4090',
            slug='nvidia-geforce-rtx-4090',
            brand='NVIDIA',
            price=Decimal('1599.99'),
            stock_qty=10,
            gpu_vram='24gb',
            generation='gen4',
            short_description='Flagship gaming graphics card.',
            long_description='In-depth specifications with Ada Lovelace architecture.',
            warranty='3 Years'
        )
        ProductSpecification.objects.create(
            product=self.product,
            spec_name='VRAM',
            spec_value='24GB GDDR6X'
        )

        # Seed AMD CPU product
        self.cpu_product = Product.objects.create(
            category=self.cpu_category,
            name='AMD Ryzen 7 7800X3D',
            slug='amd-ryzen-7-7800x3d',
            brand='AMD',
            price=Decimal('449.99'),
            stock_qty=5,
            cpu_series='ryzen7',
            cpu_cores=8,
            cpu_threads=16,
            generation='gen5',
            short_description='Zen 4 gaming processor with 3D V-Cache.',
            long_description='Unmatched gaming efficiency with 104MB cache.',
            warranty='3 Years'
        )
        ProductSpecification.objects.create(
            product=self.cpu_product,
            spec_name='Socket',
            spec_value='AM5'
        )

        # Seed Intel CPU product
        self.intel_product = Product.objects.create(
            category=self.cpu_category,
            name='Intel Core i9-14900K 24-Core',
            slug='intel-core-i9-14900k',
            brand='Intel',
            price=Decimal('549.99'),
            stock_qty=15,
            cpu_series='i9',
            cpu_cores=24,
            cpu_threads=32,
            generation='gen5',
            short_description='24 cores Intel flagship desktop CPU.',
            long_description='Raptor Lake Refresh processor.',
            warranty='3 Years'
        )

        # Seed Out of Stock RAM product
        self.ram_product = Product.objects.create(
            category=self.ram_category,
            name='Corsair Vengeance DDR5 32GB 6000MHz',
            slug='corsair-vengeance-ddr5-32gb',
            brand='Corsair',
            price=Decimal('124.99'),
            stock_qty=0,
            ram_capacity='32gb',
            generation='gen5',
            short_description='Low latency DDR5 memory kit.',
            long_description='High speed overclocking RAM with XMP profile.',
            warranty='Lifetime'
        )

        # Seed NVMe SSD product
        self.ssd_product = Product.objects.create(
            category=self.ssd_category,
            name='Samsung 990 PRO 2TB NVMe SSD',
            slug='samsung-990-pro-2tb',
            brand='Samsung',
            price=Decimal('179.99'),
            stock_qty=20,
            ssd_capacity='2tb',
            generation='gen4',
            short_description='Fast PCIe 4.0 NVMe SSD.',
            long_description='Sequential read speeds up to 7450 MB/s.',
            warranty='5 Years'
        )

        # Seed verified test user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='StrongPassword123!',
            first_name='Test',
            last_name='User',
            is_verified=True
        )

    # Test custom user creation and superuser flags
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

    # Test OTP generation and password hashing
    def test_email_verification_model_otp_hashing(self):
        user = User.objects.create_user(email='otp_test@nithome.com', password='StrongPassword123!')
        plain_otp, record = EmailVerification.generate_otp(user)
        self.assertEqual(len(plain_otp), 6)
        self.assertTrue(plain_otp.isdigit())
        self.assertNotEqual(record.otp_hash, plain_otp)
        self.assertTrue(record.check_otp(plain_otp))
        self.assertFalse(record.check_otp('000000'))

    # Test user signup workflow and verification token dispatch
    def test_signup_workflow_and_otp_generation(self):
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

        new_user = User.objects.get(email='newcustomer@nithome.com')
        self.assertFalse(new_user.is_verified)
        self.assertEqual(new_user.first_name, 'New')
        verification = EmailVerification.objects.filter(user=new_user).first()
        self.assertIsNotNone(verification)

    # Test that weak passwords violating complexity policy are rejected
    def test_weak_passwords_are_rejected_on_signup(self):
        signup_url = reverse('accounts:signup')
        weak_passwords = [
            'short1!',
            'lowercase123!',
            'UPPERCASE123!',
            'NoNumbersHere!',
            'NoSpecialChar123'
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

    # Test verifying OTP code updates verification status
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

    # Test user login workflow with valid and invalid credentials
    def test_login_workflow(self):
        login_url = reverse('accounts:login')
        response = self.client.post(
            login_url,
            {'email': 'testuser@example.com', 'password': 'StrongPassword123!'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)

        self.client.logout()
        res_fail = self.client.post(
            login_url,
            {'email': 'testuser@example.com', 'password': 'wrongpassword'}
        )
        self.assertEqual(res_fail.status_code, 200)
        self.assertContains(res_fail, 'Invalid email or password')

    # Test password reset flow with OTP verification
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
        reset_payload = {
            'otp': plain_otp,
            'new_password': 'BrandNewPassword123!',
            'confirm_new_password': 'BrandNewPassword123!'
        }
        res_reset = self.client.post(reset_url, reset_payload, follow=True)
        self.assertEqual(res_reset.status_code, 200)
        self.assertTemplateUsed(res_reset, 'accounts/login.html')

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPassword123!'))

    # Test OTP rate limiting after maximum failed attempts
    def test_otp_rate_limiting_max_attempts(self):
        user = User.objects.create_user(email='ratelimit@nithome.com', password='StrongPassword123!')
        plain_otp, record = EmailVerification.generate_otp(user)
        for _ in range(5):
            self.assertFalse(record.check_otp('000000'))
        self.assertFalse(record.check_otp(plain_otp))

    # Test resend OTP workflow
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

    # Test resend OTP cooldown enforcement
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

    # Test resend reset OTP workflow
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

    # Test reset password failure with invalid OTP
    def test_reset_password_with_invalid_otp_fails(self):
        session = self.client.session
        session['reset_user_id'] = self.user.id
        session['reset_email'] = self.user.email
        session.save()

        reset_url = reverse('accounts:reset_password')
        payload = {
            'otp': '999999',
            'new_password': 'SomeNewPassword123!',
            'confirm_new_password': 'SomeNewPassword123!'
        }
        res = self.client.post(reset_url, payload, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Invalid or expired OTP code')

        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('SomeNewPassword123!'))

    # Test product listing page view
    def test_product_list_view(self):
        response = self.client.get(reverse('products:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NVIDIA GeForce RTX 4090')
        self.assertContains(response, 'N-IT HOME')

    # Test searching products by name and brand
    def test_product_search_by_name_and_brand(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'q': 'GeForce'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'NVIDIA GeForce RTX 4090')
        self.assertNotContains(res, 'AMD Ryzen 7 7800X3D')

        res = self.client.get(url, {'q': 'AMD'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'AMD Ryzen 7 7800X3D')
        self.assertNotContains(res, 'NVIDIA GeForce RTX 4090')

    # Test searching products by multi-word query
    def test_product_search_by_multi_word_query(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'q': 'NVIDIA 4090'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'NVIDIA GeForce RTX 4090')
        self.assertNotContains(res, 'AMD Ryzen 7 7800X3D')

    # Test searching products by technical specifications
    def test_product_search_by_specifications(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'q': 'GDDR6X'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'NVIDIA GeForce RTX 4090')
        self.assertNotContains(res, 'AMD Ryzen 7 7800X3D')

        res = self.client.get(url, {'q': 'AM5'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'AMD Ryzen 7 7800X3D')

    # Test filtering products by category
    def test_product_filter_by_category(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'category': 'gpu'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'NVIDIA GeForce RTX 4090')
        self.assertNotContains(res, 'AMD Ryzen 7 7800X3D')

    # Test filtering products by brand
    def test_product_filter_by_brand(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'brand': 'Corsair'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Corsair Vengeance DDR5')
        self.assertNotContains(res, 'NVIDIA GeForce RTX 4090')

    # Test filtering products by price range
    def test_product_filter_by_price_range(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'min_price': '400', 'max_price': '600'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'AMD Ryzen 7 7800X3D')
        self.assertNotContains(res, 'NVIDIA GeForce RTX 4090')
        self.assertNotContains(res, 'Corsair Vengeance DDR5')

    # Test filtering products for in-stock items
    def test_product_filter_by_in_stock(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'in_stock': '1'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'NVIDIA GeForce RTX 4090')
        self.assertContains(res, 'AMD Ryzen 7 7800X3D')
        self.assertNotContains(res, 'Corsair Vengeance DDR5')

    # Test sorting products by price
    def test_product_sorting(self):
        url = reverse('products:product_list')
        res_low = self.client.get(url, {'sort': 'price_low'})
        self.assertEqual(res_low.status_code, 200)
        products_low = list(res_low.context['products'])
        self.assertEqual(products_low[0].name, 'Corsair Vengeance DDR5 32GB 6000MHz')
        self.assertEqual(products_low[-1].name, 'NVIDIA GeForce RTX 4090')

        res_high = self.client.get(url, {'sort': 'price_high'})
        self.assertEqual(res_high.status_code, 200)
        products_high = list(res_high.context['products'])
        self.assertEqual(products_high[0].name, 'NVIDIA GeForce RTX 4090')

    # Test combined search and multi-facet filtering
    def test_combined_search_and_filter(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {
            'q': 'GeForce',
            'category': 'gpu',
            'brand': 'NVIDIA',
            'min_price': '1000',
            'in_stock': '1',
            'sort': 'price_low'
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'NVIDIA GeForce RTX 4090')
        self.assertEqual(res.context['active_filters_count'], 6)

    # Test filtering products by RAM capacity
    def test_product_filter_by_ram_capacity(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'ram': '32gb'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Corsair Vengeance DDR5 32GB')
        self.assertNotContains(res, 'NVIDIA GeForce RTX 4090')

    # Test filtering products by GPU VRAM
    def test_product_filter_by_gpu_vram(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'gpu_vram': '24gb'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'NVIDIA GeForce RTX 4090')
        self.assertNotContains(res, 'AMD Ryzen 7 7800X3D')

    # Test filtering products by SSD capacity and PCIe generation
    def test_product_filter_by_ssd_capacity_and_generation(self):
        url = reverse('products:product_list')
        res = self.client.get(url, {'ssd': '2tb', 'generation': 'gen4'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Samsung 990 PRO 2TB')
        self.assertNotContains(res, 'Intel Core i9-14900K')

    # Test filtering products by CPU series, cores, and threads
    def test_product_filter_by_cpu_series_cores_threads(self):
        url = reverse('products:product_list')
        res_i9 = self.client.get(url, {'cpu_series': 'i9', 'cpu_cores': '24', 'cpu_threads': '32'})
        self.assertEqual(res_i9.status_code, 200)
        self.assertContains(res_i9, 'Intel Core i9-14900K')
        self.assertNotContains(res_i9, 'AMD Ryzen 7 7800X3D')

        res_ryzen = self.client.get(url, {'cpu_series': 'ryzen7', 'cpu_cores': '8'})
        self.assertEqual(res_ryzen.status_code, 200)
        self.assertContains(res_ryzen, 'AMD Ryzen 7 7800X3D')
        self.assertNotContains(res_ryzen, 'Intel Core i9-14900K')

    # Test admin product creation form contains specification fields
    def test_admin_product_creation_with_specs(self):
        admin_user = User.objects.create_superuser(
            email='admin_specs@nithome.com',
            password='AdminPassword123!',
            is_verified=True
        )
        self.client.force_login(admin_user)
        add_url = reverse('admin:products_product_add')
        res_page = self.client.get(add_url)
        self.assertEqual(res_page.status_code, 200)
        self.assertContains(res_page, 'ram_capacity')
        self.assertContains(res_page, 'gpu_vram')
        self.assertContains(res_page, 'ssd_capacity')
        self.assertContains(res_page, 'cpu_series')
        self.assertContains(res_page, 'cpu_cores')
        self.assertContains(res_page, 'cpu_threads')

    # Test admin changelists and search functionality
    def test_admin_views_and_logentry_search(self):
        admin_user = User.objects.create_superuser(
            email='admin_dash@nithome.com',
            password='AdminPassword123!',
            is_verified=True
        )
        self.client.force_login(admin_user)

        # Verify main admin index
        res_index = self.client.get(reverse('admin:index'))
        self.assertEqual(res_index.status_code, 200)

        # Verify LogEntry changelist and search (ensuring user__email lookup works without user__username error)
        res_logentry_search = self.client.get(reverse('admin:admin_logentry_changelist') + '?q=admin')
        self.assertEqual(res_logentry_search.status_code, 200)

        # Verify Orders changelist with all order status states
        for status_code, _ in Order.STATUS_CHOICES:
            Order.objects.create(
                order_number=f'NIT-TST-{status_code}',
                full_name='Test Buyer',
                email='buyer@nithome.com',
                phone='+8801700000000',
                street_address='123 Tech Lane',
                city='Dhaka',
                postal_code='1200',
                subtotal=500.00,
                shipping_fee=50.00,
                total_amount=550.00,
                status=status_code
            )
        res_orders = self.client.get(reverse('admin:orders_order_changelist'))
        self.assertEqual(res_orders.status_code, 200)
        self.assertContains(res_orders, 'Delivered')
        self.assertContains(res_orders, 'Cancelled')


    # Test product detail page rendering
    def test_product_detail_view(self):
        response = self.client.get(reverse('products:product_detail', kwargs={'slug': self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Technical Specifications')
        self.assertContains(response, 'Add to Cart')
        self.assertContains(response, 'Buy Now')

    # Test shopping cart addition, view, and quantity updates
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

    # Test checkout and complete order lifecycle step advancement
    def test_checkout_cod_order_creation_and_step_advancement(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:cart_add', kwargs={'product_id': self.product.id}), {'quantity': 1})

        checkout_url = reverse('orders:checkout')
        payload = {
            'full_name': 'Nabil Hasan',
            'email': self.user.email,
            'phone': '+880 1812345678',
            'street_address': 'House 10, Road 4, Banani',
            'city': 'Dhaka',
            'state_or_division': 'Dhaka Division',
            'postal_code': '1213'
        }
        response = self.client.post(checkout_url, payload, follow=True)
        self.assertEqual(response.status_code, 200)

        order = Order.objects.get(email=self.user.email)
        cod_res = self.client.post(
            reverse('payments:choose_payment', kwargs={'order_number': order.order_number}),
            {'payment_method': 'COD'},
            follow=True
        )
        self.assertEqual(cod_res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'PENDING')
        self.assertEqual(order.status_step_index, 1)

        # Advance order to Confirmed
        OrderService.advance_order_status(order, 'CONFIRMED')
        order.refresh_from_db()
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertEqual(order.status_step_index, 2)

        # Advance order to Packaging
        OrderService.advance_order_status(order, 'PACKAGING')
        order.refresh_from_db()
        self.assertEqual(order.status, 'PACKAGING')
        self.assertEqual(order.status_step_index, 3)

        # Advance order to In Transit
        OrderService.advance_order_status(order, 'SHIPPED')
        order.refresh_from_db()
        self.assertEqual(order.status, 'SHIPPED')
        self.assertEqual(order.status_step_index, 4)

        # Advance order to Delivered
        OrderService.advance_order_status(order, 'DELIVERED')
        order.refresh_from_db()
        self.assertEqual(order.status, 'DELIVERED')
        self.assertEqual(order.status_step_index, 5)
        self.assertTrue(order.is_paid)

        notifications = Notification.objects.filter(user=self.user)
        self.assertGreaterEqual(notifications.count(), 5)

    # Test product review submission and order cancellation with inventory restoration
    def test_product_review_and_order_cancellation(self):
        self.client.force_login(self.user)
        rev_url = reverse('products:add_review', kwargs={'slug': self.product.slug})
        rev_res = self.client.post(
            rev_url,
            {
                'author_name': 'Test User',
                'author_email': self.user.email,
                'rating': '5',
                'title': 'Great GPU',
                'comment': 'Super fast performance.'
            },
            follow=True
        )
        self.assertEqual(rev_res.status_code, 200)
        self.assertTrue(ProductReview.objects.filter(product=self.product, title='Great GPU').exists())

        self.client.post(reverse('cart:cart_add', kwargs={'product_id': self.product.id}), {'quantity': 1})
        self.client.post(
            reverse('orders:checkout'),
            {
                'full_name': 'Test User',
                'email': self.user.email,
                'phone': '+880 1812345678',
                'street_address': 'House 10, Road 4',
                'city': 'Dhaka',
                'postal_code': '1213'
            },
            follow=True
        )
        order = Order.objects.latest('id')
        self.client.post(
            reverse('payments:choose_payment', kwargs={'order_number': order.order_number}),
            {'payment_method': 'COD'},
            follow=True
        )
        self.product.refresh_from_db()
        stock_before_cancel = self.product.stock_qty

        cancel_res = self.client.post(
            reverse('orders:order_cancel', kwargs={'order_number': order.order_number}),
            follow=True
        )
        self.assertEqual(cancel_res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'CANCEL_REQUESTED')

        OrderService.approve_order_cancellation(order)
        order.refresh_from_db()
        self.assertEqual(order.status, 'CANCELLED')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, stock_before_cancel + 1)

    # Test contact message submission and service handling
    def test_contact_service_and_message_submission(self):
        contact = ContactService.submit_contact_message(
            name='Customer John',
            email='john@example.com',
            subject='GPU Availability Inquiry',
            message='When will the RTX 4090 be restocked in large quantities?'
        )
        self.assertEqual(contact.name, 'Customer John')
        self.assertEqual(contact.subject, 'GPU Availability Inquiry')
        self.assertFalse(contact.is_resolved)
        self.assertTrue(ContactMessage.objects.filter(email='john@example.com').exists())
