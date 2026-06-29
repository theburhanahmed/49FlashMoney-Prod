from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.analytics.services import AnalyticsService
from apps.lotteries.models import Lottery
from apps.transactions.models import Transaction
from apps.users.models import User
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class AnalyticsServiceTestCase(TestCase):
    """Test AnalyticsService"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )
        self.start_date = timezone.now() - timedelta(days=30)
        self.end_date = timezone.now()

    def test_get_financial_metrics(self):
        """Test getting financial metrics"""
        # Create test transactions
        Transaction.objects.create(
            user=self.user,
            type='DEPOSIT',
            amount=Decimal('100.00'),
            status='COMPLETED'
        )
        Transaction.objects.create(
            user=self.user,
            type='TICKET_PURCHASE',
            amount=Decimal('10.00'),
            status='COMPLETED'
        )

        metrics = AnalyticsService.get_financial_metrics(self.start_date, self.end_date)

        self.assertIn('total_revenue', metrics)
        self.assertIn('total_deposits', metrics)
        self.assertIn('total_withdrawals', metrics)
        self.assertIn('total_prizes_paid', metrics)

    def test_get_user_metrics(self):
        """Test getting user metrics"""
        # Create additional users
        User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='Password123'
        )

        metrics = AnalyticsService.get_user_metrics(self.start_date, self.end_date)

        self.assertIn('total_users', metrics)
        self.assertIn('active_users', metrics)
        self.assertIn('new_registrations', metrics)

    def test_get_lottery_metrics(self):
        """Test getting lottery metrics"""
        Lottery.objects.create(
            name='Test Lottery',
            description='Test',
            ticket_price=Decimal('10.00'),
            total_tickets=100,
            available_tickets=100,
            prize_amount=Decimal('500.00'),
            status='ACTIVE'
        )

        metrics = AnalyticsService.get_lottery_metrics(self.start_date, self.end_date)

        self.assertIn('active_lotteries', metrics)
        self.assertIn('completed_lotteries', metrics)
        self.assertIn('total_tickets_sold', metrics)


class AnalyticsViewSetTestCase(TestCase):
    """Test AnalyticsViewSet endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123',
            role='admin'
        )
        self.admin_user.is_admin = True
        self.admin_user.save()
        self.client.force_authenticate(user=self.admin_user)

    def test_dashboard_endpoint(self):
        """Test dashboard analytics endpoint"""
        response = self.client.get('/api/analytics/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('financial', response.data)
        self.assertIn('users', response.data)
        self.assertIn('lotteries', response.data)

    def test_financial_endpoint(self):
        """Test financial metrics endpoint"""
        response = self.client.get('/api/analytics/financial/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_revenue', response.data)

    def test_users_endpoint(self):
        """Test user metrics endpoint"""
        response = self.client.get('/api/analytics/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_users', response.data)

    def test_lotteries_endpoint(self):
        """Test lottery metrics endpoint"""
        response = self.client.get('/api/analytics/lotteries/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('active_lotteries', response.data)

