"""
Tests for VIP service.
Covers: tier creation, auto-promotion, cashback calculation,
admin tier management, and status retrieval.
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService
from apps.transactions.models import Transaction
from apps.vip.models import VIPTier, UserVIPStatus
from apps.vip.services import VIPService

User = get_user_model()


class VIPServiceTestCase(TestCase):
    """Test VIP service operations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='vip_user',
            email='vip@test.com',
            password='Pass123!',
        )
        self.admin = User.objects.create_user(
            username='vip_admin',
            email='vipadmin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
        )
        # Create tiers
        self.bronze = VIPTier.objects.create(
            name='Bronze', level=0, min_wagered=Decimal('0'),
            cashback_percentage=Decimal('0'),
        )
        self.silver = VIPTier.objects.create(
            name='Silver', level=1, min_wagered=Decimal('1000'),
            cashback_percentage=Decimal('2'),
        )
        self.gold = VIPTier.objects.create(
            name='Gold', level=2, min_wagered=Decimal('5000'),
            cashback_percentage=Decimal('5'),
        )

    def test_get_or_create_status(self):
        vip_status = VIPService.get_or_create_status(self.user)
        self.assertEqual(vip_status.tier, self.bronze)
        self.assertEqual(vip_status.total_wagered, Decimal('0'))

    def test_get_or_create_status_idempotent(self):
        s1 = VIPService.get_or_create_status(self.user)
        s2 = VIPService.get_or_create_status(self.user)
        self.assertEqual(s1.id, s2.id)

    def test_update_wagered(self):
        VIPService.update_wagered(self.user, Decimal('500'))
        vip = UserVIPStatus.objects.get(user=self.user)
        self.assertEqual(vip.total_wagered, Decimal('500'))

    def test_auto_promote_to_silver(self):
        VIPService.update_wagered(self.user, Decimal('1200'))
        vip = UserVIPStatus.objects.get(user=self.user)
        self.assertEqual(vip.tier, self.silver)

    def test_auto_promote_to_gold(self):
        VIPService.update_wagered(self.user, Decimal('6000'))
        vip = UserVIPStatus.objects.get(user=self.user)
        self.assertEqual(vip.tier, self.gold)

    def test_no_downgrade(self):
        VIPService.update_wagered(self.user, Decimal('6000'))
        # Total is still 6000, which qualifies for gold
        vip = UserVIPStatus.objects.get(user=self.user)
        self.assertEqual(vip.tier, self.gold)

    def test_cashback_no_losses(self):
        VIPService.get_or_create_status(self.user)
        # Give the user Silver tier
        UserVIPStatus.objects.filter(user=self.user).update(tier=self.silver)
        amount = VIPService.calculate_cashback(self.user, period_days=7)
        self.assertEqual(amount, Decimal('0'))

    def test_cashback_with_losses(self):
        VIPService.get_or_create_status(self.user)
        UserVIPStatus.objects.filter(user=self.user).update(tier=self.silver)
        # Fund wallet
        WalletService.credit(
            self.user, Decimal('1000'), LedgerEntry.DEPOSIT,
            'Test fund', idempotency_key='vip-test-fund',
        )
        # Simulate bets
        Transaction.objects.create(
            user=self.user, type='BET', amount=Decimal('500'),
            status='COMPLETED', description='Test bet',
        )
        # Simulate winnings (less than bets = net loss)
        Transaction.objects.create(
            user=self.user, type='WINNING', amount=Decimal('200'),
            status='COMPLETED', description='Test win',
        )
        # Net loss = 300, Silver cashback = 2%, expected = 6.00
        amount = VIPService.calculate_cashback(self.user, period_days=7)
        self.assertEqual(amount, Decimal('6.00'))

    def test_cashback_idempotent(self):
        VIPService.get_or_create_status(self.user)
        UserVIPStatus.objects.filter(user=self.user).update(tier=self.silver)
        WalletService.credit(
            self.user, Decimal('1000'), LedgerEntry.DEPOSIT,
            'Fund', idempotency_key='vip-idem-fund',
        )
        Transaction.objects.create(
            user=self.user, type='BET', amount=Decimal('500'),
            status='COMPLETED', description='Bet',
        )
        first = VIPService.calculate_cashback(self.user, period_days=7)
        second = VIPService.calculate_cashback(self.user, period_days=7)
        self.assertGreater(first, Decimal('0'))
        self.assertEqual(second, Decimal('0'))  # Already claimed

    def test_get_tier_benefits(self):
        VIPService.get_or_create_status(self.user)
        info = VIPService.get_tier_benefits(self.user)
        self.assertEqual(info['tier']['name'], 'Bronze')
        self.assertIsNotNone(info['next_tier'])
        self.assertEqual(info['next_tier']['name'], 'Silver')

    def test_admin_set_tier(self):
        VIPService.get_or_create_status(self.user)
        VIPService.admin_set_tier(self.admin, self.user, str(self.gold.id))
        vip = UserVIPStatus.objects.get(user=self.user)
        self.assertEqual(vip.tier, self.gold)

    def test_admin_create_tier(self):
        tier = VIPService.admin_create_tier(self.admin, {
            'name': 'Platinum',
            'level': 3,
            'min_wagered': '20000',
            'cashback_percentage': '10',
        })
        self.assertEqual(tier.name, 'Platinum')
        self.assertEqual(tier.level, 3)

    def test_admin_update_tier(self):
        tier = VIPService.admin_update_tier(
            self.admin, str(self.silver.id),
            {'cashback_percentage': '3'},
        )
        self.assertEqual(tier.cashback_percentage, Decimal('3'))


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'vip-api-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class VIPApiTestCase(TestCase):
    """Integration tests for VIP API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='vipapi_user',
            email='vipapi@test.com',
            password='Pass123!',
        )
        self.admin = User.objects.create_user(
            username='vipapi_admin',
            email='vipadmin2@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        VIPTier.objects.create(
            name='Bronze', level=0, min_wagered=Decimal('0'),
            cashback_percentage=Decimal('0'),
        )

    def test_get_status(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/vip/status/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['tier']['name'], 'Bronze')

    def test_get_tiers(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/vip/tiers/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_cashback_endpoint(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/vip/cashback/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_create_tier(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            '/api/vip/admin/tiers/',
            {'name': 'Diamond', 'level': 5, 'min_wagered': '50000'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_admin_set_tier(self):
        self.client.force_authenticate(user=self.admin)
        tier = VIPTier.objects.first()
        resp = self.client.post(
            '/api/vip/admin/tiers/set-tier/',
            {'user_id': str(self.user.id), 'tier_id': str(tier.id)},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_only(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            '/api/vip/admin/tiers/',
            {'name': 'X', 'level': 99},
            format='json',
        )
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])
