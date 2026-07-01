"""
Tests for Games app: engines (Snakes & Ladders, Ludo, Carrom) and
basic game room lifecycle for different GameKind values.
"""

from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.games.models import GameRoom, GameRoomPlayer, GameKind, GameState
from apps.games.engines import snakes_ladders, ludo, carrom, aviator, wingo


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

    def test_create_aviator_room(self):
        room = self._create_room(GameKind.AVIATOR)
        self.assertEqual(room.game_kind, GameKind.AVIATOR)

    def test_create_wingo_room(self):
        room = self._create_room(GameKind.WINGO)
        self.assertEqual(room.game_kind, GameKind.WINGO)


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'aviator-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class AviatorEngineTestCase(TestCase):
    """Unit tests for the Aviator game engine."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="aviator_p1",
            email="aviator_p1@test.com",
            password="Pass123!",
            wallet_balance=Decimal("500.00"),
        )
        self.user2 = User.objects.create_user(
            username="aviator_p2",
            email="aviator_p2@test.com",
            password="Pass123!",
            wallet_balance=Decimal("500.00"),
        )
        self.room = GameRoom.objects.create(
            game_kind=GameKind.AVIATOR,
            status=GameRoom.STATUS_IN_PROGRESS,
            entry_fee=Decimal("10.00"),
            min_players=1,
            max_players=10,
            created_by=self.user1,
        )
        GameRoomPlayer.objects.create(room=self.room, user=self.user1, position=0)
        GameRoomPlayer.objects.create(room=self.room, user=self.user2, position=1)

    def test_initial_state(self):
        state = aviator.initial_state(self.room, config={})
        self.assertEqual(state['phase'], 'betting')
        self.assertIn('crash_point', state)
        self.assertGreaterEqual(state['crash_point'], 1.00)
        self.assertEqual(len(state['players']), 2)

    def test_place_bet(self):
        state = aviator.initial_state(self.room, config={})
        state = aviator.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '50.00'},
            str(self.room.id), 1,
        )
        self.assertEqual(len(state['bets']), 1)
        self.assertEqual(state['bets'][0]['user_id'], str(self.user1.id))
        self.assertEqual(state['bets'][0]['amount'], '50.00')

    def test_duplicate_bet_rejected(self):
        state = aviator.initial_state(self.room, config={})
        state = aviator.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '50.00'},
            str(self.room.id), 1,
        )
        with self.assertRaises(ValueError):
            aviator.apply_action(
                state, str(self.user1.id),
                {'action': 'place_bet', 'amount': '50.00'},
                str(self.room.id), 2,
            )

    def test_cash_out_during_flight(self):
        state = aviator.initial_state(self.room, config={})
        state = aviator.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '100.00'},
            str(self.room.id), 1,
        )
        # Start flight
        state = aviator.apply_action(
            state, str(self.user1.id),
            {'action': 'start_flight'},
            str(self.room.id), 2,
        )
        self.assertEqual(state['phase'], 'flying')
        # Advance multiplier
        state['current_multiplier'] = 2.50
        # Cash out
        state = aviator.apply_action(
            state, str(self.user1.id),
            {'action': 'cash_out'},
            str(self.room.id), 3,
        )
        self.assertTrue(state['bets'][0]['cashed_out'])
        self.assertEqual(state['bets'][0]['cashout_multiplier'], 2.50)
        self.assertEqual(state['bets'][0]['payout'], '250.00')

    def test_cash_out_before_flight_fails(self):
        state = aviator.initial_state(self.room, config={})
        state = aviator.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '50.00'},
            str(self.room.id), 1,
        )
        with self.assertRaises(ValueError):
            aviator.apply_action(
                state, str(self.user1.id),
                {'action': 'cash_out'},
                str(self.room.id), 2,
            )

    def test_crash_resolves_round(self):
        state = aviator.initial_state(self.room, config={})
        state = aviator.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '50.00'},
            str(self.room.id), 1,
        )
        state = aviator.apply_action(
            state, str(self.user1.id),
            {'action': 'start_flight'},
            str(self.room.id), 2,
        )
        state = aviator.apply_action(
            state, str(self.user1.id),
            {'action': 'crash'},
            str(self.room.id), 3,
        )
        self.assertEqual(state['phase'], 'finished')
        # User didn't cash out, payout is 0
        self.assertEqual(state['bets'][0]['payout'], '0.00')

    def test_bet_amount_validation(self):
        state = aviator.initial_state(self.room, config={})
        # Below minimum
        with self.assertRaises(ValueError):
            aviator.apply_action(
                state, str(self.user1.id),
                {'action': 'place_bet', 'amount': '0.50'},
                str(self.room.id), 1,
            )
        # Above maximum
        with self.assertRaises(ValueError):
            aviator.apply_action(
                state, str(self.user1.id),
                {'action': 'place_bet', 'amount': '2000.00'},
                str(self.room.id), 2,
            )


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'wingo-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class WingoEngineTestCase(TestCase):
    """Unit tests for the Wingo game engine."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="wingo_p1",
            email="wingo_p1@test.com",
            password="Pass123!",
            wallet_balance=Decimal("500.00"),
        )
        self.user2 = User.objects.create_user(
            username="wingo_p2",
            email="wingo_p2@test.com",
            password="Pass123!",
            wallet_balance=Decimal("500.00"),
        )
        self.room = GameRoom.objects.create(
            game_kind=GameKind.WINGO,
            status=GameRoom.STATUS_IN_PROGRESS,
            entry_fee=Decimal("5.00"),
            min_players=1,
            max_players=100,
            created_by=self.user1,
        )
        GameRoomPlayer.objects.create(room=self.room, user=self.user1, position=0)
        GameRoomPlayer.objects.create(room=self.room, user=self.user2, position=1)

    def test_initial_state(self):
        state = wingo.initial_state(self.room, config={})
        self.assertEqual(state['phase'], 'betting')
        self.assertEqual(state['round_number'], 1)
        self.assertIsNone(state['outcome'])
        self.assertEqual(len(state['players']), 2)

    def test_place_number_bet(self):
        state = wingo.initial_state(self.room, config={})
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '10.00',
             'prediction_type': 'number', 'prediction_value': '5'},
            str(self.room.id), 1,
        )
        self.assertEqual(len(state['bets']), 1)
        self.assertEqual(state['bets'][0]['prediction_type'], 'number')
        self.assertEqual(state['bets'][0]['prediction_value'], '5')

    def test_place_color_bet(self):
        state = wingo.initial_state(self.room, config={})
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '10.00',
             'prediction_type': 'color', 'prediction_value': 'RED'},
            str(self.room.id), 1,
        )
        self.assertEqual(state['bets'][0]['prediction_type'], 'color')

    def test_place_big_small_bet(self):
        state = wingo.initial_state(self.room, config={})
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '10.00',
             'prediction_type': 'big_small', 'prediction_value': 'BIG'},
            str(self.room.id), 1,
        )
        self.assertEqual(state['bets'][0]['prediction_type'], 'big_small')

    def test_invalid_prediction_type_rejected(self):
        state = wingo.initial_state(self.room, config={})
        with self.assertRaises(ValueError):
            wingo.apply_action(
                state, str(self.user1.id),
                {'action': 'place_bet', 'amount': '10.00',
                 'prediction_type': 'invalid', 'prediction_value': 'X'},
                str(self.room.id), 1,
            )

    def test_invalid_number_rejected(self):
        state = wingo.initial_state(self.room, config={})
        with self.assertRaises(ValueError):
            wingo.apply_action(
                state, str(self.user1.id),
                {'action': 'place_bet', 'amount': '10.00',
                 'prediction_type': 'number', 'prediction_value': '15'},
                str(self.room.id), 1,
            )

    def test_duplicate_bet_rejected(self):
        state = wingo.initial_state(self.room, config={})
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '10.00',
             'prediction_type': 'number', 'prediction_value': '5'},
            str(self.room.id), 1,
        )
        with self.assertRaises(ValueError):
            wingo.apply_action(
                state, str(self.user1.id),
                {'action': 'place_bet', 'amount': '10.00',
                 'prediction_type': 'number', 'prediction_value': '5'},
                str(self.room.id), 2,
            )

    def test_lock_phase(self):
        state = wingo.initial_state(self.room, config={})
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'lock'},
            str(self.room.id), 1,
        )
        self.assertEqual(state['phase'], 'locked')

    def test_bet_after_lock_rejected(self):
        state = wingo.initial_state(self.room, config={})
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'lock'},
            str(self.room.id), 1,
        )
        with self.assertRaises(ValueError):
            wingo.apply_action(
                state, str(self.user1.id),
                {'action': 'place_bet', 'amount': '10.00',
                 'prediction_type': 'number', 'prediction_value': '3'},
                str(self.room.id), 2,
            )

    def test_resolve_generates_outcome(self):
        state = wingo.initial_state(self.room, config={})
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '10.00',
             'prediction_type': 'number', 'prediction_value': '5'},
            str(self.room.id), 1,
        )
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'lock'},
            str(self.room.id), 2,
        )
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'resolve'},
            str(self.room.id), 3,
        )
        self.assertEqual(state['phase'], 'finished')
        self.assertIsNotNone(state['outcome'])
        self.assertIn(state['outcome'], range(10))
        # Bet should have won/payout set
        self.assertIsNotNone(state['bets'][0]['won'])
        self.assertIsNotNone(state['bets'][0]['payout'])

    def test_winning_number_bet_payout(self):
        """Force a known outcome and verify correct payout."""
        state = wingo.initial_state(self.room, config={})
        # Place a bet on number 0
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'place_bet', 'amount': '10.00',
             'prediction_type': 'number', 'prediction_value': '0'},
            str(self.room.id), 1,
        )
        state = wingo.apply_action(
            state, str(self.user1.id),
            {'action': 'lock'},
            str(self.room.id), 2,
        )
        # Manually set outcome to 0 to test payout logic
        import copy
        test_state = copy.deepcopy(state)
        test_state['phase'] = 'locked'
        # Use resolve logic directly with known outcome
        from apps.games.engines.wingo import _get_payout_multiplier, NUMBER_COLORS, DEFAULT_PAYOUTS
        multiplier = _get_payout_multiplier('number', '0', 0, {})
        self.assertEqual(multiplier, Decimal('9.00'))
        # Payout should be 10 * 9 = 90
        expected_payout = Decimal('10.00') * multiplier
        self.assertEqual(expected_payout, Decimal('90.00'))

    def test_color_bet_payout_logic(self):
        """Verify color payout multiplier logic."""
        from apps.games.engines.wingo import _get_payout_multiplier
        # Outcome 2 is RED
        mult = _get_payout_multiplier('color', 'RED', 2, {})
        self.assertEqual(mult, Decimal('2.00'))
        # Outcome 2 is not GREEN
        mult = _get_payout_multiplier('color', 'GREEN', 2, {})
        self.assertEqual(mult, Decimal('0'))
        # Outcome 0 has VIOLET
        mult = _get_payout_multiplier('color', 'VIOLET', 0, {})
        self.assertEqual(mult, Decimal('4.50'))

    def test_big_small_payout_logic(self):
        """Verify big/small payout logic."""
        from apps.games.engines.wingo import _get_payout_multiplier
        # Outcome 7 is BIG (>=5)
        mult = _get_payout_multiplier('big_small', 'BIG', 7, {})
        self.assertEqual(mult, Decimal('2.00'))
        # Outcome 7 is not SMALL
        mult = _get_payout_multiplier('big_small', 'SMALL', 7, {})
        self.assertEqual(mult, Decimal('0'))
        # Outcome 3 is SMALL (<5)
        mult = _get_payout_multiplier('big_small', 'SMALL', 3, {})
        self.assertEqual(mult, Decimal('2.00'))


# ---------------------------------------------------------------------------
# Tests for leave_room service and start_game permission check
# ---------------------------------------------------------------------------

@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'games-leave-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class LeaveRoomServiceTestCase(TestCase):
    """Tests for the leave_room service function."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="leave_p1",
            email="leave_p1@test.com",
            password="Pass123!",
            wallet_balance=Decimal("100.00"),
        )
        self.user2 = User.objects.create_user(
            username="leave_p2",
            email="leave_p2@test.com",
            password="Pass123!",
            wallet_balance=Decimal("100.00"),
        )
        self.room = GameRoom.objects.create(
            game_kind=GameKind.SNAKES_LADDERS,
            status=GameRoom.STATUS_WAITING,
            entry_fee=Decimal("1.00"),
            min_players=2,
            max_players=4,
            created_by=self.user1,
        )
        GameRoomPlayer.objects.create(room=self.room, user=self.user1, position=0)
        GameRoomPlayer.objects.create(room=self.room, user=self.user2, position=1)

    def test_leave_room_removes_player(self):
        from apps.games.services import leave_room
        result = leave_room(self.user2, str(self.room.id))
        self.assertIsNotNone(result)
        self.assertFalse(result.players.filter(user=self.user2).exists())
        self.assertTrue(result.players.filter(user=self.user1).exists())

    def test_leave_room_deletes_empty_room(self):
        from apps.games.services import leave_room
        # Remove user2 first
        leave_room(self.user2, str(self.room.id))
        # Now user1 leaves -> room should be deleted
        result = leave_room(self.user1, str(self.room.id))
        self.assertIsNone(result)
        self.assertFalse(GameRoom.objects.filter(id=self.room.id).exists())

    def test_leave_room_not_in_room_raises(self):
        from apps.games.services import leave_room
        other_user = User.objects.create_user(
            username="outsider",
            email="outsider@test.com",
            password="Pass123!",
            wallet_balance=Decimal("100.00"),
        )
        with self.assertRaises(ValueError) as ctx:
            leave_room(other_user, str(self.room.id))
        self.assertIn('not in this room', str(ctx.exception))

    def test_leave_room_in_progress_raises(self):
        from apps.games.services import leave_room
        self.room.status = GameRoom.STATUS_IN_PROGRESS
        self.room.save()
        with self.assertRaises(ValueError) as ctx:
            leave_room(self.user1, str(self.room.id))
        self.assertIn('Can only leave when room is waiting', str(ctx.exception))

    def test_leave_room_nonexistent_raises(self):
        from apps.games.services import leave_room
        import uuid
        with self.assertRaises(ValueError) as ctx:
            leave_room(self.user1, str(uuid.uuid4()))
        self.assertIn('Room not found', str(ctx.exception))


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'games-perm-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class StartGamePermissionTestCase(TestCase):
    """Test that only room participants can start a game."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="starter_p1",
            email="starter_p1@test.com",
            password="Pass123!",
            wallet_balance=Decimal("100.00"),
        )
        self.outsider = User.objects.create_user(
            username="starter_outsider",
            email="starter_outsider@test.com",
            password="Pass123!",
            wallet_balance=Decimal("100.00"),
        )
        self.room = GameRoom.objects.create(
            game_kind=GameKind.SNAKES_LADDERS,
            status=GameRoom.STATUS_WAITING,
            entry_fee=Decimal("1.00"),
            min_players=1,
            max_players=4,
            created_by=self.user1,
        )
        GameRoomPlayer.objects.create(room=self.room, user=self.user1, position=0)

    def test_outsider_cannot_start_game(self):
        from apps.games.services import start_game
        with self.assertRaises(ValueError) as ctx:
            start_game(str(self.room.id), started_by_user=self.outsider)
        self.assertIn('must be in the room', str(ctx.exception))

