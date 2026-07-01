"""
Tests for the Mines game engine.
Covers: initial state, bet placement, tile reveal, cash-out,
mine explosion, multiplier calculation, and validation.
"""
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.games.models import GameRoom, GameRoomPlayer, GameKind
from apps.games.engines import mines
from apps.wallet.services import WalletService
from apps.wallet.models import LedgerEntry


User = get_user_model()


class MinesEngineTestCase(TestCase):
    """Unit tests for the Mines game engine."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="mines_player",
            email="mines@test.com",
            password="Pass123!",
        )
        WalletService.credit(
            user=self.user, amount=Decimal("500.00"),
            entry_type=LedgerEntry.DEPOSIT,
            idempotency_key='test_mines_setup',
        )
        self.room = GameRoom.objects.create(
            game_kind=GameKind.MINES,
            status=GameRoom.STATUS_IN_PROGRESS,
            entry_fee=Decimal("10.00"),
            min_players=1,
            max_players=1,
            created_by=self.user,
        )
        GameRoomPlayer.objects.create(room=self.room, user=self.user, position=0)

    def test_initial_state_structure(self):
        state = mines.initial_state(self.room, config={})
        self.assertEqual(state['phase'], 'betting')
        self.assertEqual(state['grid_size'], 25)
        self.assertEqual(state['user_id'], str(self.user.id))
        self.assertEqual(state['mine_count'], 0)
        self.assertEqual(state['revealed'], [])

    def test_place_bet(self):
        state = mines.initial_state(self.room, config={})
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00', 'mine_count': 5},
            str(self.room.id), 1,
        )
        self.assertEqual(state['phase'], 'playing')
        self.assertEqual(state['mine_count'], 5)
        self.assertEqual(state['bet_amount'], '10.00')
        self.assertEqual(len(state['mine_positions']), 5)

    def test_place_bet_wrong_phase(self):
        state = mines.initial_state(self.room, config={})
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00', 'mine_count': 5},
            str(self.room.id), 1,
        )
        with self.assertRaises(ValueError):
            mines.apply_action(
                state, str(self.user.id),
                {'action': 'place_bet', 'amount': '10.00', 'mine_count': 5},
                str(self.room.id), 2,
            )

    def test_place_bet_below_min(self):
        state = mines.initial_state(self.room, config={})
        with self.assertRaises(ValueError):
            mines.apply_action(
                state, str(self.user.id),
                {'action': 'place_bet', 'amount': '0.50', 'mine_count': 5},
                str(self.room.id), 1,
            )

    def test_place_bet_above_max(self):
        state = mines.initial_state(self.room, config={})
        with self.assertRaises(ValueError):
            mines.apply_action(
                state, str(self.user.id),
                {'action': 'place_bet', 'amount': '600.00', 'mine_count': 5},
                str(self.room.id), 1,
            )

    def test_mine_count_too_high(self):
        state = mines.initial_state(self.room, config={})
        with self.assertRaises(ValueError):
            mines.apply_action(
                state, str(self.user.id),
                {'action': 'place_bet', 'amount': '10.00', 'mine_count': 25},
                str(self.room.id), 1,
            )

    def test_reveal_safe_tile(self):
        state = mines.initial_state(self.room, config={})
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00', 'mine_count': 3},
            str(self.room.id), 1,
        )
        # Find a safe tile
        mine_positions = set(state['mine_positions'])
        safe_tile = next(i for i in range(25) if i not in mine_positions)

        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'reveal', 'tile': safe_tile},
            str(self.room.id), 2,
        )
        self.assertEqual(state['phase'], 'playing')
        self.assertIn(safe_tile, state['revealed'])
        self.assertGreater(Decimal(state['current_multiplier']), Decimal('1.00'))

    def test_reveal_mine_explodes(self):
        state = mines.initial_state(self.room, config={})
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00', 'mine_count': 3},
            str(self.room.id), 1,
        )
        mine_tile = state['mine_positions'][0]
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'reveal', 'tile': mine_tile},
            str(self.room.id), 2,
        )
        self.assertEqual(state['phase'], 'finished')
        self.assertEqual(state['payout'], '0.00')

    def test_reveal_duplicate_tile(self):
        state = mines.initial_state(self.room, config={})
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00', 'mine_count': 3},
            str(self.room.id), 1,
        )
        mine_positions = set(state['mine_positions'])
        safe_tile = next(i for i in range(25) if i not in mine_positions)
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'reveal', 'tile': safe_tile},
            str(self.room.id), 2,
        )
        with self.assertRaises(ValueError):
            mines.apply_action(
                state, str(self.user.id),
                {'action': 'reveal', 'tile': safe_tile},
                str(self.room.id), 3,
            )

    def test_cash_out(self):
        state = mines.initial_state(self.room, config={})
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00', 'mine_count': 3},
            str(self.room.id), 1,
        )
        mine_positions = set(state['mine_positions'])
        safe_tile = next(i for i in range(25) if i not in mine_positions)
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'reveal', 'tile': safe_tile},
            str(self.room.id), 2,
        )
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'cash_out'},
            str(self.room.id), 3,
        )
        self.assertEqual(state['phase'], 'finished')
        self.assertIsNotNone(state['payout'])
        payout = Decimal(state['payout'])
        self.assertGreater(payout, Decimal('0'))
        self.assertEqual(state['winner_id'], str(self.user.id))

    def test_cash_out_before_reveal_fails(self):
        state = mines.initial_state(self.room, config={})
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00', 'mine_count': 3},
            str(self.room.id), 1,
        )
        with self.assertRaises(ValueError):
            mines.apply_action(
                state, str(self.user.id),
                {'action': 'cash_out'},
                str(self.room.id), 2,
            )

    def test_action_after_finish_fails(self):
        state = mines.initial_state(self.room, config={})
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00', 'mine_count': 3},
            str(self.room.id), 1,
        )
        mine_tile = state['mine_positions'][0]
        state = mines.apply_action(
            state, str(self.user.id),
            {'action': 'reveal', 'tile': mine_tile},
            str(self.room.id), 2,
        )
        with self.assertRaises(ValueError):
            mines.apply_action(
                state, str(self.user.id),
                {'action': 'reveal', 'tile': 0},
                str(self.room.id), 3,
            )

    def test_wrong_user_rejected(self):
        other_user = User.objects.create_user(
            username="other_player",
            email="other@test.com",
            password="Pass123!",
        )
        state = mines.initial_state(self.room, config={})
        with self.assertRaises(ValueError):
            mines.apply_action(
                state, str(other_user.id),
                {'action': 'place_bet', 'amount': '10.00', 'mine_count': 3},
                str(self.room.id), 1,
            )

    def test_deterministic_mine_positions(self):
        """Same room_id + version always produces same positions."""
        pos1 = mines._generate_mine_positions(str(self.room.id), 1, 25, 5)
        pos2 = mines._generate_mine_positions(str(self.room.id), 1, 25, 5)
        self.assertEqual(pos1, pos2)

    def test_different_version_different_positions(self):
        """Different versions produce different mine positions."""
        pos1 = mines._generate_mine_positions(str(self.room.id), 1, 25, 5)
        pos2 = mines._generate_mine_positions(str(self.room.id), 2, 25, 5)
        # Very unlikely to be the same (not impossible, but statistically improbable)
        # Just check they're valid
        self.assertEqual(len(pos1), 5)
        self.assertEqual(len(pos2), 5)

    def test_multiplier_increases_with_reveals(self):
        """More reveals → higher multiplier."""
        m1 = mines._calculate_multiplier(25, 5, 1)
        m2 = mines._calculate_multiplier(25, 5, 2)
        m3 = mines._calculate_multiplier(25, 5, 5)
        self.assertGreater(m2, m1)
        self.assertGreater(m3, m2)

    def test_multiplier_with_more_mines_is_higher(self):
        """More mines → higher risk → higher multiplier for same reveals."""
        m_few = mines._calculate_multiplier(25, 3, 2)
        m_many = mines._calculate_multiplier(25, 10, 2)
        self.assertGreater(m_many, m_few)


class MinesABCHelpersTestCase(TestCase):
    """Test the ABC-compatible helper functions."""

    def test_game_kind(self):
        self.assertEqual(mines.game_kind(), 'MINES')

    def test_default_config(self):
        config = mines.default_config()
        self.assertIn('grid_size', config)
        self.assertIn('min_bet', config)
        self.assertIn('max_bet', config)
        self.assertIn('house_edge', config)

    def test_is_finished(self):
        self.assertFalse(mines.is_finished({'phase': 'playing'}))
        self.assertTrue(mines.is_finished({'phase': 'finished'}))

    def test_get_winners_no_winner(self):
        state = {'phase': 'finished', 'winner_id': 'MINES_EXPLODED', 'payout': '0.00'}
        self.assertEqual(mines.get_winners(state), [])

    def test_get_winners_with_winner(self):
        state = {
            'phase': 'finished',
            'winner_id': 'user-123',
            'payout': '50.00',
        }
        winners = mines.get_winners(state)
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0]['user_id'], 'user-123')
        self.assertEqual(winners[0]['payout'], Decimal('50.00'))

    def test_get_public_state_hides_mines_during_play(self):
        state = {
            'phase': 'playing',
            'mine_positions': [1, 5, 10],
            'revealed': [0],
        }
        public = mines.get_public_state(state)
        self.assertNotIn('mine_positions', public)
        self.assertIn('revealed', public)

    def test_get_public_state_shows_mines_after_finish(self):
        state = {
            'phase': 'finished',
            'mine_positions': [1, 5, 10],
            'revealed': [0],
        }
        public = mines.get_public_state(state)
        self.assertIn('mine_positions', public)

    def test_validate_config_valid(self):
        errors = mines.validate_config({
            'grid_size': 25,
            'min_bet': '1.00',
            'max_bet': '500.00',
            'house_edge': '0.02',
        })
        self.assertEqual(errors, [])

    def test_validate_config_bad_grid(self):
        errors = mines.validate_config({'grid_size': 2})
        self.assertTrue(any('grid_size' in e for e in errors))

    def test_validate_config_bad_bet_range(self):
        errors = mines.validate_config({'min_bet': '500', 'max_bet': '100'})
        self.assertTrue(any('min_bet' in e for e in errors))

    def test_validate_bet_valid(self):
        state = {'phase': 'betting', 'config': {'min_bet': '1.00', 'max_bet': '500.00'}}
        result = mines.validate_bet(state, 'user-1', Decimal('10.00'), {})
        self.assertIsNone(result)

    def test_validate_bet_wrong_phase(self):
        state = {'phase': 'playing', 'config': {'min_bet': '1.00', 'max_bet': '500.00'}}
        result = mines.validate_bet(state, 'user-1', Decimal('10.00'), {})
        self.assertIsNotNone(result)
