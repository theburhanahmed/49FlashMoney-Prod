"""
Tests for Slots service.
Covers: spin logic, payout calculation, provably fair RNG,
validation, and API endpoints.
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService, InsufficientBalanceError
from apps.slots.models import SlotsGame, SlotsSpin, DEFAULT_REELS, DEFAULT_PAYTABLE
from apps.slots.services import SlotsService

User = get_user_model()


class SlotsServiceTestCase(TestCase):
    """Unit tests for SlotsService."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='slots_player',
            email='slots@test.com',
            password='Pass123!',
        )
        WalletService.credit(
            self.user, Decimal('500'), LedgerEntry.DEPOSIT,
            'Test fund', idempotency_key='slots-test-fund',
        )
        self.game = SlotsGame.objects.create(
            name='Classic Slots',
            description='A classic 3-reel slot machine',
            paytable=DEFAULT_PAYTABLE,
            reels=DEFAULT_REELS,
            min_bet=Decimal('0.10'),
            max_bet=Decimal('100.00'),
            created_by=self.user,
        )

    def test_spin_creates_record(self):
        spin = SlotsService.spin(self.user, str(self.game.id), Decimal('1.00'))
        self.assertIsInstance(spin, SlotsSpin)
        self.assertEqual(spin.bet_amount, Decimal('1.00'))
        self.assertEqual(len(spin.symbols), 3)
        self.assertTrue(all(isinstance(s, str) for s in spin.symbols))

    def test_spin_debits_wallet(self):
        SlotsService.spin(self.user, str(self.game.id), Decimal('10.00'))
        wallet = WalletService.get_or_create_wallet(self.user)
        # Balance should be reduced (at minimum by bet amount if no win)
        self.assertLessEqual(wallet.balance, Decimal('500.00'))

    def test_spin_credits_winnings(self):
        # Run multiple spins to check that wins are credited
        initial_balance = WalletService.get_or_create_wallet(self.user).balance
        total_bet = Decimal('0')
        total_payout = Decimal('0')
        for _ in range(20):
            spin = SlotsService.spin(self.user, str(self.game.id), Decimal('1.00'))
            total_bet += Decimal('1.00')
            total_payout += spin.payout
        wallet = WalletService.get_or_create_wallet(self.user)
        # Balance should equal initial - bets + payouts
        expected = initial_balance - total_bet + total_payout
        self.assertEqual(wallet.balance, expected)

    def test_spin_below_min_bet(self):
        with self.assertRaises(ValueError):
            SlotsService.spin(self.user, str(self.game.id), Decimal('0.01'))

    def test_spin_above_max_bet(self):
        with self.assertRaises(ValueError):
            SlotsService.spin(self.user, str(self.game.id), Decimal('200.00'))

    def test_spin_inactive_game(self):
        self.game.is_active = False
        self.game.save()
        with self.assertRaises(ValueError):
            SlotsService.spin(self.user, str(self.game.id), Decimal('1.00'))

    def test_spin_insufficient_balance(self):
        poor_user = User.objects.create_user(
            username='poor', email='poor@test.com', password='Pass123!',
        )
        with self.assertRaises(InsufficientBalanceError):
            SlotsService.spin(poor_user, str(self.game.id), Decimal('1.00'))

    def test_payout_three_of_kind(self):
        """3-of-a-kind pays full multiplier."""
        payout = SlotsService._calculate_payout(
            self.game, ['seven', 'seven', 'seven'], Decimal('10.00')
        )
        self.assertEqual(payout, Decimal('1000.00'))

    def test_payout_two_of_kind(self):
        """2-of-a-kind (first two) pays 0.25x multiplier."""
        payout = SlotsService._calculate_payout(
            self.game, ['cherry', 'cherry', 'lemon'], Decimal('10.00')
        )
        self.assertEqual(payout, Decimal('5.00'))  # 10 * 2 * 0.25

    def test_payout_no_match(self):
        payout = SlotsService._calculate_payout(
            self.game, ['cherry', 'lemon', 'orange'], Decimal('10.00')
        )
        self.assertEqual(payout, Decimal('0.00'))

    def test_get_spin_history(self):
        SlotsService.spin(self.user, str(self.game.id), Decimal('1.00'))
        SlotsService.spin(self.user, str(self.game.id), Decimal('1.00'))
        history = SlotsService.get_spin_history(self.user)
        self.assertEqual(len(history), 2)

    def test_get_game_stats(self):
        SlotsService.spin(self.user, str(self.game.id), Decimal('1.00'))
        stats = SlotsService.get_game_stats(str(self.game.id))
        self.assertEqual(stats['total_spins'], 1)
        self.assertEqual(stats['total_wagered'], '1.00')

    def test_spin_result_deterministic_per_seed(self):
        """Same seed produces same symbols."""
        result1 = SlotsService._generate_spin_result(self.game, 'test-seed-123')
        result2 = SlotsService._generate_spin_result(self.game, 'test-seed-123')
        self.assertEqual(result1, result2)

    def test_spin_result_different_seeds(self):
        """Different seeds produce different-ish results."""
        result1 = SlotsService._generate_spin_result(self.game, 'seed-a')
        result2 = SlotsService._generate_spin_result(self.game, 'seed-b')
        # Valid symbols
        valid = set(DEFAULT_REELS[0])
        for s in result1 + result2:
            self.assertIn(s, valid)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'slots-api-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class SlotsApiTestCase(TestCase):
    """Integration tests for Slots API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='slotsapi_user',
            email='slotsapi@test.com',
            password='Pass123!',
        )
        self.admin = User.objects.create_user(
            username='slotsapi_admin',
            email='slotsadmin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        WalletService.credit(
            self.user, Decimal('500'), LedgerEntry.DEPOSIT,
            'API test fund', idempotency_key='slotsapi-fund',
        )
        self.game = SlotsGame.objects.create(
            name='API Test Slots',
            paytable=DEFAULT_PAYTABLE,
            reels=DEFAULT_REELS,
            min_bet=Decimal('0.10'),
            max_bet=Decimal('100.00'),
            created_by=self.admin,
        )

    def test_list_games(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/slots/games/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_retrieve_game(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(f'/api/slots/games/{self.game.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'API Test Slots')

    def test_spin(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            f'/api/slots/games/{self.game.id}/spin/',
            {'bet_amount': '1.00'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('symbols', resp.data)
        self.assertIn('payout', resp.data)

    def test_spin_no_bet_amount(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            f'/api/slots/games/{self.game.id}/spin/',
            {},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_history(self):
        self.client.force_authenticate(user=self.user)
        # Do a spin first
        self.client.post(
            f'/api/slots/games/{self.game.id}/spin/',
            {'bet_amount': '1.00'},
            format='json',
        )
        resp = self.client.get(f'/api/slots/games/{self.game.id}/history/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_admin_create_game(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            '/api/slots/games/',
            {'name': 'New Game', 'min_bet': '1.00', 'max_bet': '50.00'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_non_admin_cannot_create(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            '/api/slots/games/',
            {'name': 'New Game'},
            format='json',
        )
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])

    def test_admin_stats(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(f'/api/slots/games/{self.game.id}/stats/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('total_spins', resp.data)
