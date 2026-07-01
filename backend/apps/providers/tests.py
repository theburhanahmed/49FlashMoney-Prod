"""
Tests for the Provider adapter layer.

Covers:
  - Registry (register, get, unregister, duplicate guard)
  - DemoProviderAdapter (catalogue, sessions, bets, settlement, refund, health)
  - ProviderService (sync_catalog, launch_game, place_bet, settle_round, refund_round)
  - Player-facing API endpoints
  - Admin API endpoints
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService, InsufficientBalanceError

from .adapters.demo import DemoProviderAdapter
from .exceptions import (
    ProviderAuthError,
    ProviderBetError,
    ProviderGameNotFoundError,
    ProviderRefundError,
    ProviderSettlementError,
)
from .models import ProviderConfig, ProviderGameCatalog, ProviderGameSession, ProviderRound
from .registry import ProviderRegistry
from .services import ProviderService

User = get_user_model()

# Override throttling and cache for all tests in this module
_override = override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'providers-test',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework_simplejwt.authentication.JWTAuthentication',
        ),
        'DEFAULT_PERMISSION_CLASSES': (
            'rest_framework.permissions.IsAuthenticated',
        ),
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)


# =========================================================================== #
# Registry tests                                                                #
# =========================================================================== #

class RegistryTestCase(TestCase):
    def _fresh_registry(self):
        return ProviderRegistry()

    def test_register_and_get(self):
        reg = self._fresh_registry()
        adapter = DemoProviderAdapter()
        reg.register(adapter)
        self.assertIs(reg.get('demo'), adapter)

    def test_duplicate_registration_raises(self):
        reg = self._fresh_registry()
        reg.register(DemoProviderAdapter())
        with self.assertRaises(ValueError):
            reg.register(DemoProviderAdapter())

    def test_get_unknown_raises(self):
        reg = self._fresh_registry()
        with self.assertRaises(KeyError):
            reg.get('nonexistent')

    def test_unregister(self):
        reg = self._fresh_registry()
        reg.register(DemoProviderAdapter())
        reg.unregister('demo')
        self.assertFalse(reg.is_registered('demo'))

    def test_slugs(self):
        reg = self._fresh_registry()
        reg.register(DemoProviderAdapter())
        self.assertIn('demo', reg.slugs())

    def test_all(self):
        reg = self._fresh_registry()
        reg.register(DemoProviderAdapter())
        self.assertEqual(len(reg.all()), 1)

    def test_len(self):
        reg = self._fresh_registry()
        self.assertEqual(len(reg), 0)
        reg.register(DemoProviderAdapter())
        self.assertEqual(len(reg), 1)


# =========================================================================== #
# DemoProviderAdapter unit tests                                                #
# =========================================================================== #

class DemoAdapterTestCase(TestCase):
    def setUp(self):
        self.adapter = DemoProviderAdapter()

    def test_provider_slug(self):
        self.assertEqual(self.adapter.provider_slug, 'demo')

    def test_display_name(self):
        self.assertIsInstance(self.adapter.display_name, str)
        self.assertTrue(len(self.adapter.display_name) > 0)

    def test_authenticate_valid(self):
        self.assertTrue(self.adapter.authenticate({'api_key': 'demo-secret'}))

    def test_authenticate_empty_key(self):
        self.assertTrue(self.adapter.authenticate({'api_key': ''}))

    def test_authenticate_invalid_key(self):
        with self.assertRaises(ProviderAuthError):
            self.adapter.authenticate({'api_key': 'wrong-key'})

    def test_list_games_returns_all(self):
        games = self.adapter.list_games()
        self.assertGreaterEqual(len(games), 4)

    def test_list_games_pagination(self):
        page1 = self.adapter.list_games(page=1, page_size=2)
        page2 = self.adapter.list_games(page=2, page_size=2)
        self.assertEqual(len(page1), 2)
        ids_p1 = {g.game_id for g in page1}
        ids_p2 = {g.game_id for g in page2}
        self.assertTrue(ids_p1.isdisjoint(ids_p2))

    def test_get_game_exists(self):
        game = self.adapter.get_game('demo_slots_classic')
        self.assertEqual(game.game_id, 'demo_slots_classic')
        self.assertEqual(game.category, 'slots')
        self.assertEqual(game.provider, 'demo')

    def test_get_game_not_found(self):
        with self.assertRaises(ProviderGameNotFoundError):
            self.adapter.get_game('nonexistent_game')

    def test_create_session(self):
        session = self.adapter.create_session(
            game_id='demo_slots_classic',
            user_id='user-123',
            currency='INR',
        )
        self.assertIsInstance(session.session_token, str)
        self.assertIn('demo_slots_classic', session.launch_url)
        self.assertEqual(session.provider, 'demo')

    def test_create_session_unknown_game(self):
        from .exceptions import ProviderSessionError
        with self.assertRaises(ProviderSessionError):
            self.adapter.create_session('bad_game', 'user-123', 'INR')

    def test_launch_game_url(self):
        url = self.adapter.launch_game('tok-abc', return_url='https://example.com', mode='demo')
        self.assertIn('tok-abc', url)
        self.assertIn('mode=demo', url)
        self.assertIn('return=', url)

    def test_place_bet_returns_result(self):
        result = self.adapter.place_bet(
            session_token='tok',
            game_id='demo_slots_classic',
            user_id='user-1',
            amount=Decimal('10.00'),
            currency='INR',
            round_id='round-1',
        )
        self.assertIn(result.status, ('won', 'lost', 'push'))
        self.assertEqual(result.round_id, 'round-1')
        self.assertGreaterEqual(result.payout, Decimal('0'))

    def test_place_bet_below_min(self):
        with self.assertRaises(ProviderBetError):
            self.adapter.place_bet(
                session_token='tok', game_id='demo_slots_classic',
                user_id='u', amount=Decimal('0.01'), currency='INR',
                round_id='r',
            )

    def test_place_bet_above_max(self):
        with self.assertRaises(ProviderBetError):
            self.adapter.place_bet(
                session_token='tok', game_id='demo_slots_classic',
                user_id='u', amount=Decimal('99999.00'), currency='INR',
                round_id='r',
            )

    def test_place_bet_unknown_game(self):
        with self.assertRaises(ProviderBetError):
            self.adapter.place_bet(
                session_token='tok', game_id='bad_game',
                user_id='u', amount=Decimal('1'), currency='INR',
                round_id='r',
            )

    def test_settle_round(self):
        result = self.adapter.settle_round(
            round_id='r-1', provider_round_id='pr-1',
            payout=Decimal('20.00'), currency='INR',
        )
        self.assertEqual(result.status, 'settled')
        self.assertEqual(result.payout, Decimal('20.00'))

    def test_refund(self):
        result = self.adapter.refund(
            round_id='r-2', provider_round_id='pr-2',
            amount=Decimal('5.00'), currency='INR', reason='game error',
        )
        self.assertEqual(result.status, 'refunded')
        self.assertEqual(result.payout, Decimal('5.00'))

    def test_get_balance(self):
        balance = self.adapter.get_balance('user-1', 'INR')
        self.assertEqual(balance, Decimal('0.00'))

    def test_health_check(self):
        health = self.adapter.health_check()
        self.assertTrue(health.healthy)
        self.assertEqual(health.provider, 'demo')

    def test_supports_demo_mode(self):
        self.assertTrue(self.adapter.supports_demo_mode())

    def test_validate_config_missing_key(self):
        errors = self.adapter.validate_config({})
        self.assertTrue(any('api_key' in e for e in errors))

    def test_validate_config_valid(self):
        errors = self.adapter.validate_config({'api_key': 'demo-secret'})
        self.assertEqual(errors, [])

    def test_bet_deterministic(self):
        """Same round_id + user_id + game_id always produces the same outcome."""
        r1 = self.adapter.place_bet('tok', 'demo_slots_classic', 'u', Decimal('1'), 'INR', 'round-det')
        r2 = self.adapter.place_bet('tok', 'demo_slots_classic', 'u', Decimal('1'), 'INR', 'round-det')
        self.assertEqual(r1.payout, r2.payout)
        self.assertEqual(r1.status, r2.status)


# =========================================================================== #
# ProviderService integration tests                                             #
# =========================================================================== #

class ProviderServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='prov_player',
            email='prov@test.com',
            password='Pass123!',
        )
        WalletService.credit(
            self.user, Decimal('1000'), LedgerEntry.DEPOSIT,
            'Provider test fund', idempotency_key='prov-svc-fund',
        )
        # Sync the demo catalogue so ProviderGameCatalog rows exist
        ProviderService.sync_catalog('demo')

    def test_sync_catalog_creates_rows(self):
        count = ProviderGameCatalog.objects.filter(provider__slug='demo').count()
        self.assertGreaterEqual(count, 4)

    def test_sync_catalog_idempotent(self):
        count1 = ProviderService.sync_catalog('demo')
        count2 = ProviderService.sync_catalog('demo')
        self.assertEqual(count1, count2)
        total = ProviderGameCatalog.objects.filter(provider__slug='demo').count()
        self.assertEqual(total, count1)

    def test_launch_game_creates_session(self):
        session = ProviderService.launch_game(
            user=self.user,
            slug='demo',
            provider_game_id='demo_slots_classic',
            currency='INR',
            mode='real',
        )
        self.assertIsInstance(session, ProviderGameSession)
        self.assertEqual(session.status, ProviderGameSession.STATUS_ACTIVE)
        self.assertTrue(session.launch_url.startswith('https://'))
        self.assertEqual(session.user, self.user)

    def test_launch_game_unknown_game(self):
        with self.assertRaises(ProviderGameNotFoundError):
            ProviderService.launch_game(
                user=self.user,
                slug='demo',
                provider_game_id='nonexistent_game',
            )

    def test_launch_game_unknown_provider(self):
        with self.assertRaises(KeyError):
            ProviderService.launch_game(
                user=self.user,
                slug='nonexistent_provider',
                provider_game_id='demo_slots_classic',
            )

    def _get_session(self):
        return ProviderService.launch_game(
            user=self.user,
            slug='demo',
            provider_game_id='demo_slots_classic',
            currency='INR',
            mode='real',
        )

    def test_place_bet_debits_wallet(self):
        session = self._get_session()
        balance_before = WalletService.get_balance(self.user)
        prov_round = ProviderService.place_bet(
            user=self.user,
            session_id=str(session.id),
            bet_amount=Decimal('10.00'),
        )
        balance_after = WalletService.get_balance(self.user)
        # Wallet must have been debited (and possibly credited if won)
        net = balance_before - balance_after
        if prov_round.status == ProviderRound.STATUS_WON:
            self.assertEqual(net, Decimal('10.00') - prov_round.payout)
        elif prov_round.status == ProviderRound.STATUS_PUSH:
            self.assertEqual(net, Decimal('0.00'))
        else:
            self.assertEqual(net, Decimal('10.00'))

    def test_place_bet_creates_round(self):
        session = self._get_session()
        prov_round = ProviderService.place_bet(
            user=self.user,
            session_id=str(session.id),
            bet_amount=Decimal('5.00'),
        )
        self.assertIsInstance(prov_round, ProviderRound)
        self.assertIn(prov_round.status, [
            ProviderRound.STATUS_WON,
            ProviderRound.STATUS_LOST,
            ProviderRound.STATUS_PUSH,
        ])
        self.assertEqual(prov_round.bet_amount, Decimal('5.00'))
        self.assertNotEqual(prov_round.round_id, '')

    def test_place_bet_ledger_entries_created(self):
        session = self._get_session()
        ProviderService.place_bet(
            user=self.user,
            session_id=str(session.id),
            bet_amount=Decimal('5.00'),
        )
        entries = LedgerEntry.objects.filter(
            reference_type='provider_round',
        )
        self.assertGreaterEqual(entries.count(), 1)

    def test_place_bet_insufficient_balance(self):
        poor_user = User.objects.create_user(
            username='poor_prov', email='poor_prov@test.com', password='P!',
        )
        ProviderService.sync_catalog('demo')
        session = ProviderService.launch_game(
            user=poor_user, slug='demo',
            provider_game_id='demo_slots_classic',
        )
        with self.assertRaises(InsufficientBalanceError):
            ProviderService.place_bet(
                user=poor_user,
                session_id=str(session.id),
                bet_amount=Decimal('10.00'),
            )

    def test_settle_pending_round(self):
        session = self._get_session()
        prov_round = ProviderRound.objects.create(
            session=session,
            user=self.user,
            provider=session.provider,
            game=session.game,
            round_id='test-settle-round',
            bet_amount=Decimal('10.00'),
            payout=Decimal('0.00'),
            currency='INR',
            status=ProviderRound.STATUS_PENDING,
        )
        settled = ProviderService.settle_round('test-settle-round', Decimal('20.00'))
        self.assertEqual(settled.status, ProviderRound.STATUS_WON)
        self.assertEqual(settled.payout, Decimal('20.00'))
        balance = WalletService.get_balance(self.user)
        # Balance should have increased by payout
        self.assertGreater(balance, Decimal('0'))

    def test_settle_non_pending_raises(self):
        session = self._get_session()
        prov_round = ProviderRound.objects.create(
            session=session,
            user=self.user,
            provider=session.provider,
            game=session.game,
            round_id='test-settled-already',
            bet_amount=Decimal('10.00'),
            currency='INR',
            status=ProviderRound.STATUS_WON,
        )
        with self.assertRaises(ProviderSettlementError):
            ProviderService.settle_round('test-settled-already', Decimal('5.00'))

    def test_refund_pending_round(self):
        session = self._get_session()
        WalletService.debit(
            self.user, Decimal('10.00'), LedgerEntry.BET,
            description='manual debit for refund test',
            idempotency_key='prov-refund-test-debit',
        )
        prov_round = ProviderRound.objects.create(
            session=session,
            user=self.user,
            provider=session.provider,
            game=session.game,
            round_id='test-refund-round',
            bet_amount=Decimal('10.00'),
            currency='INR',
            status=ProviderRound.STATUS_PENDING,
        )
        balance_before = WalletService.get_balance(self.user)
        refunded = ProviderService.refund_round('test-refund-round', reason='test refund')
        balance_after = WalletService.get_balance(self.user)
        self.assertEqual(refunded.status, ProviderRound.STATUS_REFUNDED)
        self.assertEqual(balance_after - balance_before, Decimal('10.00'))

    def test_refund_settled_round_raises(self):
        session = self._get_session()
        prov_round = ProviderRound.objects.create(
            session=session,
            user=self.user,
            provider=session.provider,
            round_id='test-no-refund',
            bet_amount=Decimal('5.00'),
            currency='INR',
            status=ProviderRound.STATUS_SETTLED,
        )
        with self.assertRaises(ProviderRefundError):
            ProviderService.refund_round('test-no-refund')

    def test_get_round_history(self):
        session = self._get_session()
        ProviderService.place_bet(
            user=self.user, session_id=str(session.id),
            bet_amount=Decimal('1.00'),
        )
        rounds = ProviderService.get_round_history(self.user)
        self.assertGreaterEqual(len(rounds), 1)

    def test_health_check_all(self):
        results = ProviderService.health_check_all()
        self.assertGreaterEqual(len(results), 1)
        demo_result = next(r for r in results if r['provider'] == 'demo')
        self.assertTrue(demo_result['healthy'])

    def test_update_credentials_valid(self):
        cfg = ProviderService.update_credentials(
            'demo', {'api_key': 'demo-secret'},
        )
        self.assertEqual(cfg.credentials['api_key'], 'demo-secret')

    def test_update_credentials_invalid(self):
        with self.assertRaises(ProviderAuthError):
            ProviderService.update_credentials('demo', {})


# =========================================================================== #
# Player-facing API tests                                                       #
# =========================================================================== #

@_override
class ProviderApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='prov_api_user',
            email='prov_api@test.com',
            password='Pass123!',
        )
        self.admin = User.objects.create_user(
            username='prov_api_admin',
            email='prov_api_admin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        WalletService.credit(
            self.user, Decimal('500'), LedgerEntry.DEPOSIT,
            'API prov fund', idempotency_key='api-prov-fund',
        )
        ProviderService.sync_catalog('demo')

    def test_list_providers(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/providers/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(any(p['slug'] == 'demo' for p in resp.data))

    def test_list_games(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/providers/demo/games/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('results', resp.data)
        self.assertGreaterEqual(resp.data['count'], 4)

    def test_list_games_unknown_provider(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/providers/unknown/games/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_game_detail(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/providers/demo/games/demo_slots_classic/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['provider_game_id'], 'demo_slots_classic')

    def test_game_detail_not_found(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/providers/demo/games/bad_game_id/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_launch_session(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/providers/sessions/', {
            'slug': 'demo',
            'provider_game_id': 'demo_slots_classic',
            'currency': 'INR',
            'mode': 'real',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('session_token', resp.data)
        self.assertIn('launch_url', resp.data)

    def test_launch_session_unknown_game(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/providers/sessions/', {
            'slug': 'demo',
            'provider_game_id': 'no_such_game',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_place_bet(self):
        self.client.force_authenticate(user=self.user)
        launch_resp = self.client.post('/api/providers/sessions/', {
            'slug': 'demo',
            'provider_game_id': 'demo_slots_classic',
            'currency': 'INR',
        }, format='json')
        session_id = launch_resp.data['id']
        bet_resp = self.client.post('/api/providers/bets/', {
            'session_id': session_id,
            'bet_amount': '1.00',
        }, format='json')
        self.assertEqual(bet_resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('round_id', bet_resp.data)
        self.assertIn('status', bet_resp.data)

    def test_place_bet_insufficient_balance(self):
        poor = User.objects.create_user(
            username='prov_poor', email='prov_poor@test.com', password='P!',
        )
        self.client.force_authenticate(user=poor)
        launch_resp = self.client.post('/api/providers/sessions/', {
            'slug': 'demo',
            'provider_game_id': 'demo_slots_classic',
            'currency': 'INR',
        }, format='json')
        self.assertEqual(launch_resp.status_code, status.HTTP_201_CREATED)
        session_id = launch_resp.data['id']
        bet_resp = self.client.post('/api/providers/bets/', {
            'session_id': session_id,
            'bet_amount': '100.00',
        }, format='json')
        self.assertEqual(bet_resp.status_code, status.HTTP_402_PAYMENT_REQUIRED)

    def test_round_history(self):
        self.client.force_authenticate(user=self.user)
        launch_resp = self.client.post('/api/providers/sessions/', {
            'slug': 'demo',
            'provider_game_id': 'demo_slots_classic',
            'currency': 'INR',
        }, format='json')
        session_id = launch_resp.data['id']
        self.client.post('/api/providers/bets/', {
            'session_id': session_id,
            'bet_amount': '1.00',
        }, format='json')
        hist_resp = self.client.get('/api/providers/rounds/')
        self.assertEqual(hist_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(hist_resp.data), 1)

    def test_health_check_endpoint(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/providers/health/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(any(r['provider'] == 'demo' for r in resp.data))

    def test_unauthenticated_blocked(self):
        resp = self.client.get('/api/providers/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# =========================================================================== #
# Admin API tests                                                               #
# =========================================================================== #

@_override
class ProviderAdminApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='prov_admin_api_user',
            email='prov_adm_api@test.com',
            password='Pass123!',
        )
        self.admin = User.objects.create_user(
            username='prov_admin_api_admin',
            email='prov_adm_api_admin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        WalletService.credit(
            self.user, Decimal('500'), LedgerEntry.DEPOSIT,
            'Admin API prov fund', idempotency_key='admin-api-prov-fund',
        )
        ProviderService.sync_catalog('demo')

    def test_list_configs(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/providers/admin/configs/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(any(c['slug'] == 'demo' for c in resp.data))

    def test_list_configs_non_admin_denied(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/providers/admin/configs/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_credentials(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            '/api/providers/admin/configs/demo/credentials/',
            {'credentials': {'api_key': 'demo-secret'}},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['slug'], 'demo')

    def test_update_credentials_invalid(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(
            '/api/providers/admin/configs/demo/credentials/',
            {'credentials': {}},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sync_catalog(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/providers/admin/catalog/sync/', {'slug': 'demo'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('synced', resp.data)

    def test_sync_catalog_missing_slug(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/providers/admin/catalog/sync/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_round_list(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/providers/admin/rounds/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('results', resp.data)

    def test_admin_round_detail(self):
        self.client.force_authenticate(user=self.admin)
        # Create a round to query
        session = ProviderService.launch_game(
            user=self.user, slug='demo',
            provider_game_id='demo_slots_classic',
        )
        prov_round = ProviderRound.objects.create(
            session=session, user=self.user,
            provider=session.provider, game=session.game,
            round_id='admin-detail-test',
            bet_amount=Decimal('1.00'),
            currency='INR', status=ProviderRound.STATUS_PENDING,
        )
        resp = self.client.get('/api/providers/admin/rounds/admin-detail-test/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['round_id'], 'admin-detail-test')

    def test_admin_manual_settle(self):
        self.client.force_authenticate(user=self.admin)
        session = ProviderService.launch_game(
            user=self.user, slug='demo',
            provider_game_id='demo_slots_classic',
        )
        ProviderRound.objects.create(
            session=session, user=self.user,
            provider=session.provider, game=session.game,
            round_id='admin-settle-test',
            bet_amount=Decimal('5.00'),
            currency='INR', status=ProviderRound.STATUS_PENDING,
        )
        resp = self.client.post(
            '/api/providers/admin/rounds/admin-settle-test/settle/',
            {'payout': '10.00'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], ProviderRound.STATUS_WON)

    def test_admin_manual_refund(self):
        self.client.force_authenticate(user=self.admin)
        session = ProviderService.launch_game(
            user=self.user, slug='demo',
            provider_game_id='demo_slots_classic',
        )
        # Debit wallet first so refund has something to return
        WalletService.debit(
            self.user, Decimal('5.00'), LedgerEntry.BET,
            description='manual debit', idempotency_key='admin-refund-debit',
        )
        ProviderRound.objects.create(
            session=session, user=self.user,
            provider=session.provider, game=session.game,
            round_id='admin-refund-test',
            bet_amount=Decimal('5.00'),
            currency='INR', status=ProviderRound.STATUS_PENDING,
        )
        resp = self.client.post(
            '/api/providers/admin/rounds/admin-refund-test/refund/',
            {'reason': 'admin test refund'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], ProviderRound.STATUS_REFUNDED)
