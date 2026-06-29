"""
Tests for Slots app: games list, spin (success, insufficient balance, inactive game, limits), permissions.
"""
from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.slots.models import SlotsGame, SlotsSpin
from apps.transactions.models import Transaction

User = get_user_model()

DEFAULT_PAYTABLE = {
    "seven": 100, "bar": 50, "bell": 25, "plum": 10,
    "orange": 5, "lemon": 3, "cherry": 2,
}
DEFAULT_REELS = [
    ["cherry", "lemon", "orange", "plum", "bell", "bar", "seven", "seven"],
    ["cherry", "lemon", "orange", "plum", "bell", "bar", "seven", "seven"],
    ["cherry", "lemon", "orange", "plum", "bell", "bar", "seven", "seven"],
]


def make_game(name="Test Slots", is_active=True, min_bet=Decimal("0.10"), max_bet=Decimal("100.00"), created_by=None):
    return SlotsGame.objects.create(
        name=name,
        description="Test game",
        is_active=is_active,
        paytable=DEFAULT_PAYTABLE,
        reels=DEFAULT_REELS,
        rtp_percent=Decimal("96.00"),
        min_bet=min_bet,
        max_bet=max_bet,
        created_by=created_by,
    )


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'slots-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    }
)
class SlotsGameListTestCase(TestCase):
    """Test listing slots games: anonymous and regular users see only active; admin sees all."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="AdminPass123",
            is_admin=True,
            role="admin",
        )
        self.user = User.objects.create_user(
            username="user",
            email="user@test.com",
            password="UserPass123",
            wallet_balance=Decimal("100"),
        )
        self.active_game = make_game(name="Active Game", is_active=True, created_by=self.admin)
        self.inactive_game = make_game(name="Inactive Game", is_active=False, created_by=self.admin)

    def test_list_games_anonymous_sees_only_active(self):
        response = self.client.get("/api/slots/games/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get("results", [])
        ids = [g["id"] for g in results]
        self.assertIn(str(self.active_game.id), ids)
        self.assertNotIn(str(self.inactive_game.id), ids)

    def test_list_games_authenticated_user_sees_only_active(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/slots/games/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get("results", [])
        ids = [g["id"] for g in results]
        self.assertIn(str(self.active_game.id), ids)
        self.assertNotIn(str(self.inactive_game.id), ids)

    def test_list_games_admin_sees_all(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/slots/games/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get("results", [])
        ids = [g["id"] for g in results]
        self.assertIn(str(self.active_game.id), ids)
        self.assertIn(str(self.inactive_game.id), ids)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'slots-spin-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    }
)
class SlotsSpinTestCase(TestCase):
    """Test spin endpoint: success, insufficient balance, inactive game, bet limits, unauthorized."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="AdminPass123",
            is_admin=True,
            role="admin",
        )
        self.user = User.objects.create_user(
            username="player",
            email="player@test.com",
            password="PlayerPass123",
            wallet_balance=Decimal("50.00"),
        )
        self.game = make_game(name="Lucky Test", is_active=True, created_by=self.admin)

    def test_spin_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"/api/slots/games/{self.game.id}/spin/",
            {"bet_amount": "1.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("symbols", response.data)
        self.assertEqual(len(response.data["symbols"]), 3)
        self.assertEqual(Decimal(str(response.data["bet_amount"])), Decimal("1.00"))
        self.assertIn("payout", response.data)
        self.assertIn("random_seed", response.data)
        self.user.refresh_from_db()
        self.assertEqual(SlotsSpin.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Transaction.objects.filter(user=self.user, type="SLOTS_BET").count(), 1)

    def test_spin_insufficient_balance(self):
        self.user.wallet_balance = Decimal("0.50")
        self.user.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"/api/slots/games/{self.game.id}/spin/",
            {"bet_amount": "1.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("balance", response.data["error"].lower() or "")
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal("0.50"))
        self.assertEqual(SlotsSpin.objects.filter(user=self.user).count(), 0)

    def test_spin_inactive_game(self):
        self.game.is_active = False
        self.game.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"/api/slots/games/{self.game.id}/spin/",
            {"bet_amount": "1.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(SlotsSpin.objects.filter(user=self.user).count(), 0)

    def test_spin_bet_below_minimum(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"/api/slots/games/{self.game.id}/spin/",
            {"bet_amount": "0.05"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_spin_bet_above_maximum(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"/api/slots/games/{self.game.id}/spin/",
            {"bet_amount": "200.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_spin_unauthorized(self):
        response = self.client.post(
            f"/api/slots/games/{self.game.id}/spin/",
            {"bet_amount": "1.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(SlotsSpin.objects.count(), 0)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'slots-history-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    }
)
class SlotsSpinHistoryTestCase(TestCase):
    """Test spin history (list) requires authentication."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="user",
            email="user@test.com",
            password="UserPass123",
            wallet_balance=Decimal("100"),
        )
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="AdminPass123",
            is_admin=True,
            role="admin",
        )
        self.game = make_game(created_by=self.admin)

    def test_spins_list_requires_auth(self):
        response = self.client.get("/api/slots/spins/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_spins_list_returns_user_spins_only(self):
        self.client.force_authenticate(user=self.user)
        # One spin
        self.client.post(
            f"/api/slots/games/{self.game.id}/spin/",
            {"bet_amount": "1.00"},
            format="json",
        )
        response = self.client.get("/api/slots/spins/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get("results", [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["bet_amount"], "1.00")
