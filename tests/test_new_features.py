import json
from io import StringIO
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.management import call_command
from django.contrib.auth import get_user_model

from orders.models import Order, OrderItem
from orders.services import OrderService
from products.models import Product, Category
from payments.models import Payment
from payments.services import SSLCommerzGatewayService
from courier.models import Shipment
from courier.services import SteadfastService
from accounts.models import PhoneVerification
from accounts.services import SMSOTPService

User = get_user_model()


class NewFeaturesIntegrationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='testcustomer@nithome.com',
            password='TestPassword123!',
            first_name='Nabil',
            last_name='Customer'
        )
        self.other_user = User.objects.create_user(
            email='other@nithome.com',
            password='OtherPassword123!',
            first_name='Other',
            last_name='Customer'
        )
        self.staff_user = User.objects.create_superuser(
            email='admin@nithome.com',
            password='AdminPassword123!',
            first_name='Admin',
            last_name='User'
        )
        self.category = Category.objects.create(name='Graphics Cards', slug='gpus')
        self.product = Product.objects.create(
            name='GeForce RTX 4080',
            slug='geforce-rtx-4080',
            category=self.category,
            brand='NVIDIA',
            price=Decimal('125000.00'),
            stock_qty=4,
            short_description='High performance GPU',
            long_description='Flagship GPU'
        )
        self.order = Order.objects.create(
            user=self.user,
            full_name='Nabil Customer',
            email='testcustomer@nithome.com',
            phone='01711223344',
            street_address='House 12, Road 5, Banani',
            city='Dhaka',
            postal_code='1213',
            subtotal=Decimal('125000.00'),
            shipping_fee=Decimal('0.00'),
            total_amount=Decimal('125000.00'),
            payment_method='SSLCOMMERZ',
            status='PENDING',
            is_paid=False
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=1,
            line_total=self.product.price
        )

    # 1. SSLCommerz IPN and Payment Verification Tests
    @patch('payments.services.SSLCommerzGatewayService.validate_transaction_with_gateway')
    def test_sslcommerz_ipn_valid_updates_order_and_payment(self, mock_validate):
        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TEST-IPN-TXN-1',
            amount=self.order.total_amount,
            status='PENDING'
        )

        mock_validate.return_value = (True, {
            'status': 'VALID',
            'tran_id': payment.transaction_id,
            'amount': '125000.00',
            'currency': 'BDT',
            'bank_tran_id': 'BANK-TXN-9999',
            'card_type': 'BKASH-BKash',
            'risk_level': '0',
            'risk_title': 'Safe',
        })

        ipn_url = reverse('payments:sslcommerz_ipn')
        resp = self.client.post(ipn_url, {
            'val_id': 'VALIDATION-12345',
            'tran_id': payment.transaction_id,
        })

        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'SUCCESS')
        self.assertEqual(payment.val_id, 'VALIDATION-12345')
        self.assertEqual(payment.bank_tran_id, 'BANK-TXN-9999')

        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.status, 'CONFIRMED')

        # Exactly 1 shipment created
        self.assertEqual(Shipment.objects.filter(order=self.order).count(), 1)

    @patch('payments.services.SSLCommerzGatewayService.validate_transaction_with_gateway')
    def test_sslcommerz_ipn_idempotent_on_repeated_delivery(self, mock_validate):
        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TEST-IPN-TXN-2',
            amount=self.order.total_amount,
            status='PENDING'
        )

        mock_validate.return_value = (True, {
            'status': 'VALID',
            'tran_id': payment.transaction_id,
            'amount': '125000.00',
            'currency': 'BDT',
            'bank_tran_id': 'BANK-TXN-2222',
            'card_type': 'VISA-City Bank',
            'risk_level': '0',
        })

        ipn_url = reverse('payments:sslcommerz_ipn')

        # First IPN delivery
        resp1 = self.client.post(ipn_url, {'val_id': 'VAL-1', 'tran_id': payment.transaction_id})
        self.assertEqual(resp1.status_code, 200)

        # Second repeated IPN delivery
        resp2 = self.client.post(ipn_url, {'val_id': 'VAL-1', 'tran_id': payment.transaction_id})
        self.assertEqual(resp2.status_code, 200)

        # Third repeated IPN delivery
        resp3 = self.client.post(ipn_url, {'val_id': 'VAL-1', 'tran_id': payment.transaction_id})
        self.assertEqual(resp3.status_code, 200)

        # Confirm shipment is NOT duplicated
        self.assertEqual(Shipment.objects.filter(order=self.order).count(), 1)

    @patch('payments.services.SSLCommerzGatewayService.validate_transaction_with_gateway')
    def test_sslcommerz_ipn_rejects_amount_mismatch(self, mock_validate):
        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TEST-IPN-TAMPER-AMT',
            amount=self.order.total_amount,  # 125000.00
            status='PENDING'
        )

        # Gateway reports customer only paid 10.00 BDT
        mock_validate.return_value = (True, {
            'status': 'VALID',
            'tran_id': payment.transaction_id,
            'amount': '10.00',
            'currency': 'BDT',
            'bank_tran_id': 'BANK-FAKE-0001',
            'risk_level': '0',
        })

        ipn_url = reverse('payments:sslcommerz_ipn')
        resp = self.client.post(ipn_url, {
            'val_id': 'VAL-FAKE',
            'tran_id': payment.transaction_id,
        })

        self.assertEqual(resp.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'FAILED')
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)
        self.assertEqual(self.order.status, 'PENDING')

    @patch('payments.services.SSLCommerzGatewayService.validate_transaction_with_gateway')
    def test_sslcommerz_ipn_rejects_currency_mismatch(self, mock_validate):
        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TEST-IPN-TAMPER-CURR',
            amount=self.order.total_amount,
            currency='BDT',
            status='PENDING'
        )

        mock_validate.return_value = (True, {
            'status': 'VALID',
            'tran_id': payment.transaction_id,
            'amount': '125000.00',
            'currency': 'USD',  # Mismatched currency
            'risk_level': '0',
        })

        ipn_url = reverse('payments:sslcommerz_ipn')
        resp = self.client.post(ipn_url, {
            'val_id': 'VAL-FAKE-CURR',
            'tran_id': payment.transaction_id,
        })

        self.assertEqual(resp.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'FAILED')
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)

    @patch('payments.services.SSLCommerzGatewayService.validate_transaction_with_gateway')
    def test_sslcommerz_ipn_rejects_tran_id_mismatch(self, mock_validate):
        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TARGET-ORDER-TXN',
            amount=self.order.total_amount,
            status='PENDING'
        )

        mock_validate.return_value = (True, {
            'status': 'VALID',
            'tran_id': 'NIT-DIFFERENT-UNRELATED-TXN',  # Different transaction id from gateway!
            'amount': '125000.00',
            'currency': 'BDT',
            'risk_level': '0',
        })

        ipn_url = reverse('payments:sslcommerz_ipn')
        resp = self.client.post(ipn_url, {
            'val_id': 'VAL-DIFF-TXN',
            'tran_id': payment.transaction_id,
        })

        self.assertEqual(resp.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'FAILED')
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)

    @patch('payments.services.SSLCommerzGatewayService.validate_transaction_with_gateway')
    def test_sslcommerz_ipn_flags_risky_transaction(self, mock_validate):
        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TEST-RISKY-TXN',
            amount=self.order.total_amount,
            status='PENDING'
        )

        mock_validate.return_value = (True, {
            'status': 'VALID',
            'tran_id': payment.transaction_id,
            'amount': '125000.00',
            'currency': 'BDT',
            'risk_level': '1',  # Flagged by SSLCOMMERZ anti-fraud
            'risk_title': 'Suspicious Activity Detected',
        })

        ipn_url = reverse('payments:sslcommerz_ipn')
        resp = self.client.post(ipn_url, {
            'val_id': 'VAL-RISK-1',
            'tran_id': payment.transaction_id,
        })

        self.assertEqual(resp.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'PENDING')
        self.assertIn('Risk Level 1', payment.gateway_reference)
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_paid)

    # 2. Payment Initiation & Ownership Guards
    def test_payment_initiation_guards_prevent_paying_already_paid_order(self):
        self.order.is_paid = True
        self.order.save()

        self.client.force_login(self.user)
        initiate_url = reverse('payments:sslcommerz_initiate', kwargs={'order_number': self.order.order_number})
        resp = self.client.post(initiate_url)
        self.assertRedirects(resp, reverse('orders:order_detail', kwargs={'order_number': self.order.order_number}))

    def test_payment_initiation_rejects_unauthorized_user(self):
        self.client.force_login(self.other_user)
        select_url = reverse('payments:payment_select', kwargs={'order_number': self.order.order_number})
        resp = self.client.get(select_url)
        self.assertEqual(resp.status_code, 404)

    # 3. Callbacks: Success, Fail, Cancel
    @patch('payments.services.SSLCommerzGatewayService.validate_transaction_with_gateway')
    def test_browser_success_callback_validates_delayed_ipn(self, mock_validate):
        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TEST-BROWSER-RETURN',
            amount=self.order.total_amount,
            status='PENDING'
        )

        mock_validate.return_value = (True, {
            'status': 'VALID',
            'tran_id': payment.transaction_id,
            'amount': '125000.00',
            'currency': 'BDT',
            'bank_tran_id': 'BANK-TXN-BROWSER',
            'card_type': 'NAGAD-Nagad',
            'risk_level': '0',
        })

        self.client.force_login(self.user)
        success_url = reverse('payments:sslcommerz_success', kwargs={'order_number': self.order.order_number})
        resp = self.client.post(success_url, {
            'val_id': 'VAL-BROWSER-1',
            'tran_id': payment.transaction_id,
        })

        self.assertRedirects(resp, reverse('orders:order_success', kwargs={'order_number': self.order.order_number}))
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'SUCCESS')

    def test_fail_callback_marks_payment_failed(self):
        self.client.force_login(self.user)
        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TEST-FAIL-CB',
            amount=self.order.total_amount,
            status='PENDING'
        )

        fail_url = reverse('payments:sslcommerz_fail', kwargs={'order_number': self.order.order_number})
        resp = self.client.post(fail_url, {
            'tran_id': payment.transaction_id,
            'error': 'Card issuer declined transaction'
        })
        self.assertRedirects(resp, reverse('payments:payment_select', kwargs={'order_number': self.order.order_number}))
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'FAILED')

    def test_cancel_callback_marks_payment_cancelled(self):
        self.client.force_login(self.user)
        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TEST-CANCEL-CB',
            amount=self.order.total_amount,
            status='PENDING'
        )

        cancel_url = reverse('payments:sslcommerz_cancel', kwargs={'order_number': self.order.order_number})
        resp = self.client.post(cancel_url, {
            'tran_id': payment.transaction_id,
        })
        self.assertRedirects(resp, reverse('payments:payment_select', kwargs={'order_number': self.order.order_number}))
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'CANCELLED')

    # 4. Steadfast Courier Idempotency Tests
    @override_settings(STEADFAST_WEBHOOK_TOKEN='test-token-123')
    def test_steadfast_webhook_updates_order_status_to_shipped_and_delivered(self):
        shipment = Shipment.objects.create(
            order=self.order,
            consignment_id='STEADFAST-CID-1001',
            tracking_code='TRK-987654',
            status='pending'
        )

        webhook_url = reverse('courier:steadfast_webhook', kwargs={'token': 'test-token-123'})

        # Test in_transit event
        payload_transit = {
            'consignment_id': 'STEADFAST-CID-1001',
            'delivery_status': 'in_transit'
        }
        res1 = self.client.post(webhook_url, data=json.dumps(payload_transit), content_type='application/json')
        self.assertEqual(res1.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'SHIPPED')

        # Test delivered event
        payload_delivered = {
            'consignment_id': 'STEADFAST-CID-1001',
            'delivery_status': 'delivered'
        }
        res2 = self.client.post(webhook_url, data=json.dumps(payload_delivered), content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'DELIVERED')
        self.assertTrue(self.order.is_paid)

    @override_settings(STEADFAST_WEBHOOK_TOKEN='test-token-123')
    def test_steadfast_webhook_rejects_invalid_token(self):
        webhook_url = reverse('courier:steadfast_webhook', kwargs={'token': 'wrong-fake-token'})
        res = self.client.post(webhook_url, data=json.dumps({'consignment_id': '123'}), content_type='application/json')
        self.assertEqual(res.status_code, 403)

    def test_steadfast_service_create_order_is_strictly_idempotent(self):
        # Create an existing shipment with real consignment ID
        Shipment.objects.create(
            order=self.order,
            consignment_id='REAL-STEADFAST-CID-555',
            tracking_code='TRK-555',
            status='pending'
        )

        # Call create_order again
        with patch('requests.post') as mock_post:
            result = SteadfastService.create_order(self.order)
            # Must NOT make an HTTP request
            mock_post.assert_not_called()
            self.assertEqual(result['status'], 200)
            self.assertEqual(result['consignment']['consignment_id'], 'REAL-STEADFAST-CID-555')

    # 5. Owner Dashboard Tests
    def test_owner_dashboard_accessible_only_to_staff(self):
        dashboard_url = reverse('dashboard:overview')

        # Anonymous user denied
        res_anon = self.client.get(dashboard_url)
        self.assertNotEqual(res_anon.status_code, 200)

        # Standard customer denied
        self.client.force_login(self.user)
        res_cust = self.client.get(dashboard_url)
        self.assertEqual(res_cust.status_code, 403)

        # Staff user allowed
        self.client.force_login(self.staff_user)
        res_staff = self.client.get(dashboard_url)
        self.assertEqual(res_staff.status_code, 200)
        self.assertIn('monthly_revenue', res_staff.context)
        self.assertIn('low_stock_products', res_staff.context)
        low_stock = list(res_staff.context['low_stock_products'])
        self.assertTrue(any(p.id == self.product.id for p in low_stock))

    # 6. Phone OTP Verification Tests
    def test_phone_otp_dispatch_and_verification(self):
        phone_number = '01899887766'
        otp, record = SMSOTPService.create_and_send_otp(self.user, phone_number)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        self.assertFalse(self.user.is_phone_verified)

        # Invalid OTP fails
        self.assertFalse(SMSOTPService.verify_user_otp(self.user, '000000'))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_phone_verified)

        # Valid OTP succeeds
        self.assertTrue(SMSOTPService.verify_user_otp(self.user, otp))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_phone_verified)
        self.assertEqual(self.user.profile.phone, phone_number)
        self.assertFalse(PhoneVerification.objects.filter(user=self.user).exists())

    # 7. Admin Order Alert Email Test
    @patch('orders.services.send_mail')
    def test_admin_alert_email_sent_on_order_placement(self, mock_send_mail):
        OrderService.send_admin_new_order_email(self.order)
        self.assertTrue(mock_send_mail.called)
        call_kwargs = mock_send_mail.call_args[1]
        self.assertIn(f"New Order #{self.order.order_number}", call_kwargs['subject'])
        self.assertIn(self.order.full_name, call_kwargs['message'])
        self.assertIn(str(self.order.total_amount), call_kwargs['message'])
        self.assertIn(self.product.name, call_kwargs['message'])
        self.assertEqual(call_kwargs['recipient_list'], ['nabil29089@gmail.com'])

    # 8. Sandbox Configuration and Initiation Error Handling Tests
    @override_settings(SSLCOMMERZ_STORE_ID='test_sandbox_store', SSLCOMMERZ_STORE_PASS='test_sandbox_pass', SSLCOMMERZ_IS_SANDBOX=True)
    @patch('payments.services.SSLCommerzGatewayService.get_service_client')
    def test_payment_initiation_valid_sandbox_session(self, mock_client_factory):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 'SUCCESS'
        mock_response.session_key = 'TEST-SESSION-KEY-999'
        mock_response.gateway_url = 'https://sandbox.sslcommerz.com/EasyCheckOut/testcheckout'
        mock_client.initiate_payment.return_value = mock_response
        mock_client_factory.return_value = mock_client

        url, payment = SSLCommerzGatewayService.initiate_payment(self.order)
        self.assertEqual(url, 'https://sandbox.sslcommerz.com/EasyCheckOut/testcheckout')
        self.assertEqual(payment.status, 'PENDING')
        self.assertEqual(payment.gateway_session_key, 'TEST-SESSION-KEY-999')
        self.assertTrue(payment.transaction_id.startswith(f"NIT{self.order.id}X"))
        self.assertLessEqual(len(payment.transaction_id), 30)

    @override_settings(SSLCOMMERZ_STORE_ID='', SSLCOMMERZ_STORE_PASS='test_pass')
    def test_payment_initiation_fails_when_store_id_missing(self):
        url, payment = SSLCommerzGatewayService.initiate_payment(self.order)
        self.assertIsNone(url)
        self.assertEqual(payment.status, 'FAILED')
        self.assertIn('missing', payment.raw_response.lower())

    @override_settings(SSLCOMMERZ_STORE_ID='test_store', SSLCOMMERZ_STORE_PASS='')
    def test_payment_initiation_fails_when_store_pass_missing(self):
        url, payment = SSLCommerzGatewayService.initiate_payment(self.order)
        self.assertIsNone(url)
        self.assertEqual(payment.status, 'FAILED')
        self.assertIn('missing', payment.raw_response.lower())

    @override_settings(SSLCOMMERZ_STORE_ID='testbox', SSLCOMMERZ_STORE_PASS='qwerty', SSLCOMMERZ_IS_SANDBOX=False)
    def test_payment_initiation_fails_when_production_uses_sandbox_creds(self):
        url, payment = SSLCommerzGatewayService.initiate_payment(self.order)
        self.assertIsNone(url)
        self.assertEqual(payment.status, 'FAILED')
        self.assertIn('sandbox credentials used in production', payment.raw_response.lower())

    @patch('payments.services.SSLCommerzGatewayService.get_service_client')
    def test_sslcommerz_ipn_signature_verification_rejects_invalid_hash(self, mock_client_factory):
        from sslcommerz_python_api.exceptions import SSLCommerzValidationError
        mock_client = MagicMock()
        mock_client.verify_ipn.side_effect = SSLCommerzValidationError("Signature mismatch")
        mock_client_factory.return_value = mock_client

        payment = Payment.objects.create(
            order=self.order,
            method='SSLCOMMERZ',
            transaction_id='NIT-TEST-SIG-FAIL',
            amount=self.order.total_amount,
            status='PENDING'
        )

        ipn_url = reverse('payments:sslcommerz_ipn')
        resp = self.client.post(ipn_url, {
            'val_id': 'VAL-SIG-1',
            'tran_id': payment.transaction_id,
            'verify_sign': 'fake_tampered_sign',
            'verify_key': 'amount,currency',
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Invalid IPN signature', resp.content.decode())

    @override_settings(
        SSLCOMMERZ_STORE_ID='test_sandbox_id',
        SSLCOMMERZ_STORE_PASS='test_sandbox_secret',
        SSLCOMMERZ_IS_SANDBOX=True,
        SITE_URL='http://127.0.0.1:8000'
    )
    def test_check_payment_config_management_command(self):
        out = StringIO()
        call_command('check_payment_config', stdout=out)
        output = out.getvalue()
        self.assertIn('SSLCOMMERZ Mode         : SANDBOX', output)
        self.assertIn('Store ID                : CONFIGURED', output)
        self.assertIn('Store Password          : CONFIGURED', output)
        self.assertIn('Initiate Route', output)
        self.assertIn('IPN Webhook Route', output)
        self.assertIn('READY FOR PAYMENT FLOW TESTING', output)
        # Verify store password secret is NEVER printed
        self.assertNotIn('test_sandbox_secret', output)

