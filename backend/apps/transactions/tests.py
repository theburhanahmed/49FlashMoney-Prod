from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.transactions.models import Transaction, PaymentMethod, WithdrawalRequest
from apps.transactions.services import WithdrawalService
from decimal import Decimal
import uuid

User = get_user_model()


class TransactionModelTestCase(TestCase):
    """Test Transaction model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    def test_create_transaction(self):
        """Test creating a transaction"""
        transaction = Transaction.objects.create(
            user=self.user,
            type='DEPOSIT',
            amount=Decimal('100.00'),
            status='COMPLETED',
            description='Test deposit'
        )

        self.assertEqual(transaction.type, 'DEPOSIT')
        self.assertEqual(transaction.amount, Decimal('100.00'))
        self.assertEqual(transaction.status, 'COMPLETED')

    def test_mark_completed(self):
        """Test marking transaction as completed"""
        transaction = Transaction.objects.create(
            user=self.user,
            type='DEPOSIT',
            amount=Decimal('100.00'),
            status='PENDING'
        )

        result = transaction.mark_completed()

        self.assertTrue(result)
        self.assertEqual(transaction.status, 'COMPLETED')
        self.assertIsNotNone(transaction.completed_at)


class WithdrawalServiceTestCase(TestCase):
    """Test WithdrawalService"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123',
            wallet_balance=Decimal('100.00')
        )

    def test_validate_withdrawal_request_success(self):
        """Test successful withdrawal validation"""
        is_valid, error_message = WithdrawalService.validate_withdrawal_request(
            self.user,
            Decimal('50.00')
        )

        self.assertTrue(is_valid)
        self.assertIsNone(error_message)

    def test_validate_withdrawal_request_insufficient_balance(self):
        """Test withdrawal validation with insufficient balance"""
        is_valid, error_message = WithdrawalService.validate_withdrawal_request(
            self.user,
            Decimal('150.00')
        )

        self.assertFalse(is_valid)
        self.assertIn('balance', error_message.lower())

    def test_validate_withdrawal_request_below_minimum(self):
        """Test withdrawal validation below minimum threshold"""
        is_valid, error_message = WithdrawalService.validate_withdrawal_request(
            self.user,
            Decimal('5.00')
        )

        self.assertFalse(is_valid)
        self.assertIn('minimum', error_message.lower())


class WithdrawalRequestViewSetTestCase(TestCase):
    """Test WithdrawalRequestViewSet"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123',
            wallet_balance=Decimal('100.00')
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123',
            role='admin'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_withdrawal_request(self):
        """Test creating a withdrawal request"""
        response = self.client.post('/api/withdrawals/', {
            'amount': '50.00',
            'bank_details': {
                'account_number': '123456789',
                'routing_number': '987654321'
            }
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'REQUESTED')

    def test_approve_withdrawal(self):
        """Test approving a withdrawal (admin only)"""
        withdrawal = WithdrawalRequest.objects.create(
            user=self.user,
            amount=Decimal('50.00'),
            status='REQUESTED'
        )

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/withdrawals/{withdrawal.id}/approve/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'APPROVED')

    def test_reject_withdrawal(self):
        """Test rejecting a withdrawal (admin only)"""
        withdrawal = WithdrawalRequest.objects.create(
            user=self.user,
            amount=Decimal('50.00'),
            status='REQUESTED'
        )

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/withdrawals/{withdrawal.id}/reject/', {
            'rejection_reason': 'Insufficient documentation'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'REJECTED')


class PaymentMethodViewSetTestCase(TestCase):
    """Test PaymentMethodViewSet"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )
        self.client.force_authenticate(user=self.user)

    def test_list_payment_methods(self):
        """Test listing payment methods"""
        PaymentMethod.objects.create(
            user=self.user,
            method_type='CREDIT_CARD',
            payment_details={'last4': '4242'}
        )

        response = self.client.get('/api/payment-methods/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_set_primary_payment_method(self):
        """Test setting primary payment method"""
        pm1 = PaymentMethod.objects.create(
            user=self.user,
            method_type='CREDIT_CARD',
            is_primary=True
        )
        pm2 = PaymentMethod.objects.create(
            user=self.user,
            method_type='DEBIT_CARD',
            is_primary=False
        )

        response = self.client.post(f'/api/payment-methods/{pm2.id}/set_primary/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pm1.refresh_from_db()
        pm2.refresh_from_db()
        self.assertFalse(pm1.is_primary)
        self.assertTrue(pm2.is_primary)

