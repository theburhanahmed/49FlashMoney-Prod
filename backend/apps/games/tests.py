"""
Tests for Games app: engines (Snakes & Ladders, Ludo, Carrom) and
basic game room lifecycle for different GameKind values.
"""

from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.games.models import GameRoom, GameKind, GameState
from apps.games.engines import snakes_ladders, ludo, carrom


User = get_user_model()


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'games-engine-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class GameEnginesTestCase(TestCase):
    """Unit tests for individual game engines."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="player",
            email="player@test.com",
            password="PlayerPass123",
            wallet_balance=Decimal("100.00"),
        )
        self.room_sl = GameRoom.objects.create(
            game_kind=GameKind.SNAKES_LADDERS,
            status=GameRoom.STATUS_WAITING,
            entry_fee=Decimal("1.00"),
            min_players=2,
            max_players=4,
            created_by=self.user,
        )
        self.room_ludo = GameRoom.objects.create(
            game_kind=GameKind.LUDO,
            status=GameRoom.STATUS_WAITING,
            entry_fee=Decimal("1.00"),
            min_players=2,
            max_players=4,
            created_by=self.user,
        )
        self.room_carrom = GameRoom.objects.create(
            game_kind=GameKind.CARROM,
            status=GameRoom.STATUS_WAITING,
            entry_fee=Decimal("1.00"),
            min_players=2,
            max_players=4,
            created_by=self.user,
        )

    def test_snakes_ladders_initial_state(self):
        state = snakes_ladders.initial_state(self.room_sl, config={})
        self.assertIn("players", state)
        self.assertEqual(state["current_turn_index"], 0)

    def test_ludo_initial_state(self):
        state = ludo.initial_state(self.room_ludo, config={})
        self.assertIn("players", state)
        self.assertEqual(state["current_turn_index"], 0)

    def test_carrom_initial_state(self):
        state = carrom.initial_state(self.room_carrom, config={})
        self.assertIn("players", state)
        self.assertEqual(state["current_turn_index"], 0)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'games-room-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class GameRoomApiTestCase(TestCase):
    """Integration-style tests for creating and starting rooms for each GameKind."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="player",
            email="player@test.com",
            password="PlayerPass123",
            wallet_balance=Decimal("100.00"),
        )
        self.client.force_authenticate(user=self.user)

    def _create_room(self, game_kind: str) -> GameRoom:
        resp = self.client.post(
            "/api/games/rooms/",
            {
                "game_kind": game_kind,
                "entry_fee": "1.00",
                "config": {},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        room_id = resp.data["id"]
        return GameRoom.objects.get(id=room_id)

    def _start_room(self, room: GameRoom):
        url = f"/api/games/rooms/{room.id}/start/"
        resp = self.client.post(url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertEqual(room.status, GameRoom.STATUS_IN_PROGRESS)
        # A GameState record should exist
        self.assertTrue(GameState.objects.filter(room=room).exists())

    def test_create_and_start_snakes_ladders_room(self):
        room = self._create_room(GameKind.SNAKES_LADDERS)
        self._start_room(room)

    def test_create_and_start_ludo_room(self):
        room = self._create_room(GameKind.LUDO)
        self._start_room(room)

    def test_create_and_start_carrom_room(self):
        room = self._create_room(GameKind.CARROM)
        self._start_room(room)

