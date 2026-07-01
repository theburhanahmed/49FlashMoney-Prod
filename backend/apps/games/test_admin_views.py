"""
Tests for admin API views: game config, engine registry,
round history, maintenance mode, audit logs, and withdrawal management.
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.games.models import GameRoom, GameRoomPlayer, GameState, GameKind
from apps.users.models import AuditLog
from apps.wallet.services import WalletService
from apps.wallet.models import LedgerEntry

User = get_user_model()


def _fund_user(user, amount, key_suffix=''):
    """Fund user wallet via WalletService."""
    WalletService.credit(
        user=user, amount=amount,
        entry_type=LedgerEntry.DEPOSIT,
        idempotency_key=f'test_admin_{user.id}_{key_suffix}',
    )


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'admin-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class AdminAuthTestCase(TestCase):
    """Test admin-only access control on all admin endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='Pass123!',
            role='user',
        )

    def test_engines_requires_admin(self):
        self.client.force_authenticate(user=self.regular_user)
        resp = self.client.get('/api/games/admin/engines/')
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])

    def test_config_requires_admin(self):
        self.client.force_authenticate(user=self.regular_user)
        resp = self.client.get('/api/games/admin/config/AVIATOR/')
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])

    def test_rounds_requires_admin(self):
        self.client.force_authenticate(user=self.regular_user)
        resp = self.client.get('/api/games/admin/rounds/')
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])

    def test_audit_logs_requires_admin(self):
        self.client.force_authenticate(user=self.regular_user)
        resp = self.client.get('/api/games/admin/audit-logs/')
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'admin-api-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class EngineRegistryViewTestCase(TestCase):
    """Test engine registry endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        self.client.force_authenticate(user=self.admin)

    def test_list_engines(self):
        resp = self.client.get('/api/games/admin/engines/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        engines = resp.data['engines']
        game_kinds = [e['game_kind'] for e in engines]
        self.assertIn('AVIATOR', game_kinds)
        self.assertIn('WINGO', game_kinds)
        self.assertIn('MINES', game_kinds)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'admin-config-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class GameConfigViewTestCase(TestCase):
    """Test game configuration endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='config_admin',
            email='config_admin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        self.client.force_authenticate(user=self.admin)

    def test_get_game_config(self):
        resp = self.client.get('/api/games/admin/config/AVIATOR/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['game_kind'], 'AVIATOR')
        self.assertIn('default_config', resp.data)

    def test_get_config_unknown_game(self):
        resp = self.client.get('/api/games/admin/config/UNKNOWN/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_game_config(self):
        resp = self.client.put(
            '/api/games/admin/config/AVIATOR/',
            {'config': {'min_bet': '5.00', 'max_bet': '500.00', 'house_edge': 0.05}},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Should create audit log
        log = AuditLog.objects.filter(resource_id='AVIATOR').first()
        self.assertIsNotNone(log)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'admin-rounds-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class GameRoundHistoryViewTestCase(TestCase):
    """Test round history and detail endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='rounds_admin',
            email='rounds_admin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        self.player = User.objects.create_user(
            username='player',
            email='player@test.com',
            password='PlayerPass123!',
        )
        _fund_user(self.player, Decimal('100.00'), 'round_hist')
        self.client.force_authenticate(user=self.admin)
        # Create some rooms
        self.room = GameRoom.objects.create(
            game_kind=GameKind.AVIATOR,
            status=GameRoom.STATUS_COMPLETED,
            entry_fee=Decimal('10.00'),
            min_players=1,
            max_players=10,
            created_by=self.player,
        )
        GameRoomPlayer.objects.create(
            room=self.room, user=self.player, position=0,
            result='WON', payout=Decimal('50.00'),
        )

    def test_list_rounds(self):
        resp = self.client.get('/api/games/admin/rounds/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['game_kind'], 'AVIATOR')

    def test_filter_rounds_by_game_kind(self):
        resp = self.client.get('/api/games/admin/rounds/', {'game_kind': 'WINGO'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 0)

    def test_round_detail(self):
        resp = self.client.get(f'/api/games/admin/rounds/{self.room.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['game_kind'], 'AVIATOR')
        self.assertEqual(len(resp.data['players']), 1)

    def test_round_detail_not_found(self):
        import uuid
        resp = self.client.get(f'/api/games/admin/rounds/{uuid.uuid4()}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'admin-maintenance-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class GameMaintenanceViewTestCase(TestCase):
    """Test maintenance mode toggle."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='maint_admin',
            email='maint_admin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        self.player = User.objects.create_user(
            username='maint_player',
            email='maint_player@test.com',
            password='Pass123!',
        )
        _fund_user(self.player, Decimal('100.00'), 'maint')
        self.client.force_authenticate(user=self.admin)

    def test_disable_game(self):
        # Create waiting rooms
        GameRoom.objects.create(
            game_kind=GameKind.WINGO,
            status=GameRoom.STATUS_WAITING,
            entry_fee=Decimal('5.00'),
            min_players=2,
            max_players=4,
            created_by=self.player,
        )
        resp = self.client.post(
            '/api/games/admin/maintenance/WINGO/',
            {'enabled': False, 'reason': 'Scheduled maintenance'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['enabled'])
        # Waiting rooms should be cancelled
        self.assertEqual(
            GameRoom.objects.filter(
                game_kind=GameKind.WINGO, status=GameRoom.STATUS_CANCELLED
            ).count(),
            1,
        )

    def test_enable_game(self):
        resp = self.client.post(
            '/api/games/admin/maintenance/WINGO/',
            {'enabled': True},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['enabled'])


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'admin-audit-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class AuditLogViewTestCase(TestCase):
    """Test audit log listing and filtering."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='audit_admin',
            email='audit_admin@test.com',
            password='AdminPass123!',
            role='admin',
            is_admin=True,
            is_staff=True,
        )
        self.client.force_authenticate(user=self.admin)

        AuditLog.objects.create(
            user=self.admin,
            action='DEPOSIT',
            description='Test deposit log',
            resource_type='PAYMENT',
            resource_id='pay-001',
        )
        AuditLog.objects.create(
            user=self.admin,
            action='WITHDRAWAL',
            description='Test withdrawal log',
            resource_type='WITHDRAWAL',
            resource_id='wd-001',
        )

    def test_list_audit_logs(self):
        resp = self.client.get('/api/games/admin/audit-logs/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 2)

    def test_filter_by_action(self):
        resp = self.client.get('/api/games/admin/audit-logs/', {'action': 'DEPOSIT'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['action'], 'DEPOSIT')

    def test_filter_by_resource_type(self):
        resp = self.client.get(
            '/api/games/admin/audit-logs/', {'resource_type': 'WITHDRAWAL'}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 1)
