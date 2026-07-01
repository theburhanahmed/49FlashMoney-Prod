"""
Tests for Promotions service and views.
Covers: promotion creation, claiming, duplicate claim prevention,
expired promotions, max claims, and admin management.
"""
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService
from apps.promotions.models import Promotion, PromotionClaim
from apps.promotions.services import (
    PromotionService,
    PromotionNotActiveError,
    PromotionExpiredError,
    PromotionMaxClaimsReachedError,
    PromotionAlreadyClaimedError,
)

User = get_user_model()


class PromotionServiceTestCase(TestCase):
    """Test PromotionService operations."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='promo_user',
            email='promo@test.com',
            password='Pass123!',
        )
        self.admin = User.objects.create_user(
            username='promo_admin',
            email='promoadmin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
        )
        self.promo = Promotion.objects.create(
            name='Welcome Bonus',
            description='50% deposit bonus up to 100',
            promotion_type='DEPOSIT_BONUS',
            status='ACTIVE',
            bonus_percentage=Decimal('50'),
            max_bonus_amount=Decimal('100'),
            min_deposit=Decimal('10'),
            wagering_requirement=Decimal('5'),
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            max_claims=100,
        )

    def test_claim_deposit_bonus(self):
        claim = PromotionService.claim_promotion(
            self.user, str(self.promo.id), deposit_amount=Decimal('200')
        )
        self.assertEqual(claim.status, 'CREDITED')
        # 50% of 200 = 100, capped at max_bonus_amount=100
        self.assertEqual(claim.bonus_amount, Decimal('100.00'))
        # Wallet should be credited
        wallet = WalletService.get_or_create_wallet(self.user)
        self.assertEqual(wallet.balance, Decimal('100.00'))

    def test_claim_deposit_bonus_partial(self):
        claim = PromotionService.claim_promotion(
            self.user, str(self.promo.id), deposit_amount=Decimal('50')
        )
        # 50% of 50 = 25, below cap
        self.assertEqual(claim.bonus_amount, Decimal('25.00'))

    def test_claim_increments_total_claims(self):
        PromotionService.claim_promotion(
            self.user, str(self.promo.id), deposit_amount=Decimal('100')
        )
        self.promo.refresh_from_db()
        self.assertEqual(self.promo.total_claims, 1)

    def test_duplicate_claim_rejected(self):
        PromotionService.claim_promotion(
            self.user, str(self.promo.id), deposit_amount=Decimal('100')
        )
        with self.assertRaises(PromotionAlreadyClaimedError):
            PromotionService.claim_promotion(
                self.user, str(self.promo.id), deposit_amount=Decimal('100')
            )

    def test_inactive_promotion_rejected(self):
        self.promo.status = 'DRAFT'
        self.promo.save()
        with self.assertRaises(PromotionNotActiveError):
            PromotionService.claim_promotion(
                self.user, str(self.promo.id), deposit_amount=Decimal('100')
            )

    def test_expired_promotion_rejected(self):
        self.promo.end_date = timezone.now() - timedelta(hours=1)
        self.promo.save()
        with self.assertRaises(PromotionExpiredError):
            PromotionService.claim_promotion(
                self.user, str(self.promo.id), deposit_amount=Decimal('100')
            )

    def test_max_claims_reached(self):
        self.promo.max_claims = 1
        self.promo.total_claims = 1
        self.promo.save()
        with self.assertRaises(PromotionMaxClaimsReachedError):
            PromotionService.claim_promotion(
                self.user, str(self.promo.id), deposit_amount=Decimal('100')
            )

    def test_get_available_promotions(self):
        available = PromotionService.get_available_promotions(self.user)
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0].id, self.promo.id)

    def test_available_excludes_claimed(self):
        PromotionService.claim_promotion(
            self.user, str(self.promo.id), deposit_amount=Decimal('100')
        )
        available = PromotionService.get_available_promotions(self.user)
        self.assertEqual(len(available), 0)

    def test_get_user_claims(self):
        PromotionService.claim_promotion(
            self.user, str(self.promo.id), deposit_amount=Decimal('100')
        )
        claims = PromotionService.get_user_claims(self.user)
        self.assertEqual(len(claims), 1)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'promo-api-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class PromotionApiTestCase(TestCase):
    """Integration tests for Promotion API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='promoapi_user',
            email='promoapi@test.com',
            password='Pass123!',
        )
        self.admin = User.objects.create_user(
            username='promoapi_admin',
            email='promoapiadmin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        self.promo = Promotion.objects.create(
            name='API Bonus',
            promotion_type='DEPOSIT_BONUS',
            status='ACTIVE',
            bonus_percentage=Decimal('25'),
            max_bonus_amount=Decimal('50'),
            min_deposit=Decimal('10'),
            wagering_requirement=Decimal('3'),
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            max_claims=0,
        )

    def test_list_promotions(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/promotions/promotions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_claim_promotion(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            f'/api/promotions/promotions/{self.promo.id}/claim/',
            {'deposit_amount': 100},
            format='json',
        )
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_my_claims(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/promotions/promotions/my-claims/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_create(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            '/api/promotions/promotions/',
            {
                'name': 'New Promo',
                'promotion_type': 'CASHBACK',
                'bonus_percentage': '10',
                'max_bonus_amount': '200',
                'min_deposit': '0',
                'wagering_requirement': '1',
                'start_date': (timezone.now() - timedelta(days=1)).isoformat(),
                'end_date': (timezone.now() + timedelta(days=30)).isoformat(),
            },
            format='json',
        )
        self.assertIn(resp.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])

    def test_non_admin_cannot_create(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            '/api/promotions/promotions/',
            {'name': 'X', 'promotion_type': 'CASHBACK'},
            format='json',
        )
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])
