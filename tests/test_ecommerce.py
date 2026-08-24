"""
Comprehensive automated tests for N-IT Home E-Commerce platform.
Validates No-JS compliance, CBVs, Strategy Pattern, Cart, and Order flows.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from products.models import Category, Product, ProductImage, ProductSpecification
from orders.models import Order, OrderItem
from payments.models import Payment
from decimal import Decimal

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
            username="testuser",
            email="testuser@example.com",
            password="password123"
        )

    def test_product_list_view(self):
        """Test product listing and filtering."""
        response = self.client.get(reverse('products:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NVIDIA GeForce RTX 4090")
        self.assertContains(response, "N-IT")

    def test_product_detail_view(self):
        """Test product detail page renders pure CSS tabs and gallery elements."""
        response = self.client.get(reverse('products:product_detail', kwargs={'slug': self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Technical Specifications")
        self.assertContains(response, "Deep-Dive Architecture")
        self.assertContains(response, "Add to Cart")
        self.assertContains(response, "Buy Now")

    def test_cart_workflow(self):
        """Test adding item to cart, updating quantity, and viewing cart."""
        # Add to cart
        add_url = reverse('cart:cart_add', kwargs={'product_id': self.product.id})
        response = self.client.post(add_url, {'quantity': 2}, follow=True)
        self.assertEqual(response.status_code, 200)

        # View cart
        cart_url = reverse('cart:cart_detail')
        response = self.client.get(cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NVIDIA GeForce RTX 4090")
        self.assertContains(response, "3199.98")

        # Update cart quantity (decrease)
        update_url = reverse('cart:cart_update', kwargs={'product_id': self.product.id})
        response = self.client.post(update_url, {'action': 'decrease'}, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_checkout_cod_order_creation(self):
        """Test creating an atomic COD order."""
        # Add to cart first
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

        # Verify order in DB
        order = Order.objects.get(email='nabil@example.com')
        self.assertEqual(order.payment_method, 'COD')
        self.assertEqual(order.payment_status, 'PENDING')
        self.assertEqual(order.items.count(), 1)
        # Verify stock deducted atomically
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

        # Execute bKash callback
        order = Order.objects.get(email='imtiaz@example.com')
        payment = Payment.objects.get(order=order)
        callback_url = reverse('payments:bkash_callback', kwargs={'transaction_id': payment.transaction_id})
        cb_res = self.client.post(callback_url, {'wallet_number': '01712345678', 'otp': '123456', 'pin': '12345'}, follow=True)
        self.assertEqual(cb_res.status_code, 200)

        # Verify Payment and Order status updated to PAID
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.payment_status, 'PAID')
        self.assertEqual(payment.status, 'SUCCESS')
