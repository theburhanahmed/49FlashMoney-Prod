"""
Tests for AnalyticsService – game metrics (GGR, NGR, RTP).
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.transactions.models import Transaction
from apps.analytics.services import AnalyticsService

User = get_user_model()


class GameMetricsTestCase(TestCase):
    """Test AnalyticsService.get_game_metrics()."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='analytics_user',
            email='analytics@test.com',
            password='Pass123!',
        )

    def test_empty_metrics(self):
        metrics = AnalyticsService.get_game_metrics()
        self.assertEqual(metrics['total_bets'], '0')
        self.assertEqual(metrics['total_payouts'], '0')
        self.assertEqual(metrics['ggr'], '0')
        self.assertEqual(metrics['ngr'], '0')

    def test_ggr_calculation(self):
        Transaction.objects.create(
            user=self.user, type='BET', amount=Decimal('100'),
            status='COMPLETED', description='Test bet',
        )
        Transaction.objects.create(
            user=self.user, type='WINNING', amount=Decimal('40'),
            status='COMPLETED', description='Test win',
        )
        metrics = AnalyticsService.get_game_metrics()
        self.assertEqual(Decimal(metrics['ggr']), Decimal('60'))

    def test_ngr_subtracts_bonuses(self):
        Transaction.objects.create(
            user=self.user, type='BET', amount=Decimal('200'),
            status='COMPLETED', description='Bet',
        )
        Transaction.objects.create(
            user=self.user, type='WINNING', amount=Decimal('80'),
            status='COMPLETED', description='Win',
        )
        Transaction.objects.create(
            user=self.user, type='CASHBACK', amount=Decimal('10'),
            status='COMPLETED', description='Cashback',
        )
        metrics = AnalyticsService.get_game_metrics()
        ggr = Decimal(metrics['ggr'])
        ngr = Decimal(metrics['ngr'])
        self.assertEqual(ggr, Decimal('120'))
        self.assertEqual(ngr, Decimal('110'))

    def test_rtp_calculation(self):
        Transaction.objects.create(
            user=self.user, type='BET', amount=Decimal('100'),
            status='COMPLETED', description='Bet',
        )
        Transaction.objects.create(
            user=self.user, type='WINNING', amount=Decimal('96'),
            status='COMPLETED', description='Win',
        )
        metrics = AnalyticsService.get_game_metrics()
        self.assertEqual(metrics['rtp'], '96.00')

    def test_slots_metrics(self):
        Transaction.objects.create(
            user=self.user, type='SLOTS_BET', amount=Decimal('50'),
            status='COMPLETED', description='Slots bet',
        )
        Transaction.objects.create(
            user=self.user, type='SLOTS_WIN', amount=Decimal('45'),
            status='COMPLETED', description='Slots win',
        )
        metrics = AnalyticsService.get_game_metrics()
        self.assertEqual(Decimal(metrics['total_bets']), Decimal('50'))
        self.assertEqual(Decimal(metrics['total_payouts']), Decimal('45'))


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'analytics-api-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class AnalyticsApiTestCase(TestCase):
    """Integration tests for analytics API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='analytics_admin',
            email='analyticadmin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username='analytics_regular',
            email='analyticuser@test.com',
            password='Pass123!',
        )

    def test_games_endpoint(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/analytics/admin/analytics/games/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('ggr', resp.data)
        self.assertIn('ngr', resp.data)
        self.assertIn('rtp', resp.data)

    def test_games_endpoint_requires_admin(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/analytics/admin/analytics/games/')
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])

    def test_dashboard_endpoint(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/analytics/admin/analytics/dashboard/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('financial', resp.data)
        self.assertIn('users', resp.data)

    def test_financial_endpoint(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/analytics/admin/analytics/financial/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('revenue', resp.data)
        self.assertIn('deposits', resp.data)
