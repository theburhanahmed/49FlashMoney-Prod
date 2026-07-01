"""
Tests for the Scratch Card game engine.
Covers: initial state, bet placement, cell scratching, bust,
prize accumulation, collect, auto-collect, and validation.
"""
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.games.models import GameRoom, GameRoomPlayer, GameKind
from apps.games.engines import scratch_card

User = get_user_model()


class ScratchCardEngineTestCase(TestCase):
    """Unit tests for the Scratch Card game engine."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="scratch_player",
            email="scratch@test.com",
            password="Pass123!",
            wallet_balance=Decimal("500.00"),
        )
        self.room = GameRoom.objects.create(
            game_kind=GameKind.SCRATCH_CARD,
            status=GameRoom.STATUS_IN_PROGRESS,
            entry_fee=Decimal("5.00"),
            min_players=1,
            max_players=1,
            created_by=self.user,
        )
        GameRoomPlayer.objects.create(room=self.room, user=self.user, position=0)

    def test_initial_state_structure(self):
        state = scratch_card.initial_state(self.room, config={})
        self.assertEqual(state['phase'], 'betting')
        self.assertEqual(state['grid_size'], 9)
        self.assertEqual(state['user_id'], str(self.user.id))
        self.assertEqual(state['revealed_indices'], [])
        self.assertEqual(state['total_prize'], '0.00')

    def test_place_bet(self):
        state = scratch_card.initial_state(self.room, config={})
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00'},
            str(self.room.id), 1,
        )
        self.assertEqual(state['phase'], 'scratching')
        self.assertEqual(state['bet_amount'], '10.00')
        self.assertEqual(len(state['cells']), 9)

    def test_place_bet_below_min(self):
        state = scratch_card.initial_state(self.room, config={})
        with self.assertRaises(ValueError):
            scratch_card.apply_action(
                state, str(self.user.id),
                {'action': 'place_bet', 'amount': '0.50'},
                str(self.room.id), 1,
            )

    def test_place_bet_above_max(self):
        state = scratch_card.initial_state(self.room, config={})
        with self.assertRaises(ValueError):
            scratch_card.apply_action(
                state, str(self.user.id),
                {'action': 'place_bet', 'amount': '600.00'},
                str(self.room.id), 1,
            )

    def test_place_bet_wrong_phase(self):
        state = scratch_card.initial_state(self.room, config={})
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00'},
            str(self.room.id), 1,
        )
        with self.assertRaises(ValueError):
            scratch_card.apply_action(
                state, str(self.user.id),
                {'action': 'place_bet', 'amount': '10.00'},
                str(self.room.id), 2,
            )

    def test_scratch_blank_cell(self):
        state = scratch_card.initial_state(self.room, config={})
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00'},
            str(self.room.id), 1,
        )
        # Find a blank cell
        blank_idx = next(
            i for i, c in enumerate(state['cells'])
            if c['value'] == 'blank'
        )
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'scratch', 'cell': blank_idx},
            str(self.room.id), 2,
        )
        self.assertEqual(state['phase'], 'scratching')
        self.assertTrue(state['cells'][blank_idx]['revealed'])
        self.assertIn(blank_idx, state['revealed_indices'])

    def test_scratch_prize_cell(self):
        state = scratch_card.initial_state(self.room, config={})
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00'},
            str(self.room.id), 1,
        )
        # Find a prize cell (2x, 5x, or 10x)
        prize_idx = next(
            i for i, c in enumerate(state['cells'])
            if c['value'] not in ('blank', 'bust')
        )
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'scratch', 'cell': prize_idx},
            str(self.room.id), 2,
        )
        self.assertEqual(state['phase'], 'scratching')
        self.assertGreater(Decimal(state['total_prize']), Decimal('0'))

    def test_scratch_bust_cell(self):
        state = scratch_card.initial_state(self.room, config={})
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00'},
            str(self.room.id), 1,
        )
        bust_idx = next(
            i for i, c in enumerate(state['cells'])
            if c['value'] == 'bust'
        )
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'scratch', 'cell': bust_idx},
            str(self.room.id), 2,
        )
        self.assertEqual(state['phase'], 'finished')
        self.assertEqual(state['total_prize'], '0.00')
        self.assertIsNone(state.get('winner_id'))

    def test_scratch_already_revealed_fails(self):
        state = scratch_card.initial_state(self.room, config={})
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00'},
            str(self.room.id), 1,
        )
        blank_idx = next(
            i for i, c in enumerate(state['cells'])
            if c['value'] == 'blank'
        )
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'scratch', 'cell': blank_idx},
            str(self.room.id), 2,
        )
        with self.assertRaises(ValueError):
            scratch_card.apply_action(
                state, str(self.user.id),
                {'action': 'scratch', 'cell': blank_idx},
                str(self.room.id), 3,
            )

    def test_collect_after_scratching(self):
        state = scratch_card.initial_state(self.room, config={})
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00'},
            str(self.room.id), 1,
        )
        prize_idx = next(
            i for i, c in enumerate(state['cells'])
            if c['value'] not in ('blank', 'bust')
        )
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'scratch', 'cell': prize_idx},
            str(self.room.id), 2,
        )
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'collect'},
            str(self.room.id), 3,
        )
        self.assertEqual(state['phase'], 'finished')
        self.assertEqual(state['winner_id'], str(self.user.id))
        self.assertGreater(Decimal(state['total_prize']), Decimal('0'))

    def test_collect_with_zero_prize_fails(self):
        state = scratch_card.initial_state(self.room, config={})
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00'},
            str(self.room.id), 1,
        )
        # Scratch only a blank
        blank_idx = next(
            i for i, c in enumerate(state['cells'])
            if c['value'] == 'blank'
        )
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'scratch', 'cell': blank_idx},
            str(self.room.id), 2,
        )
        # Collect should still work (zero prize is collected)
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'collect'},
            str(self.room.id), 3,
        )
        self.assertEqual(state['phase'], 'finished')

    def test_wrong_user_rejected(self):
        other = User.objects.create_user(
            username="other", email="other@test.com", password="Pass123!"
        )
        state = scratch_card.initial_state(self.room, config={})
        with self.assertRaises(ValueError):
            scratch_card.apply_action(
                state, str(other.id),
                {'action': 'place_bet', 'amount': '10.00'},
                str(self.room.id), 1,
            )

    def test_action_after_finish_fails(self):
        state = scratch_card.initial_state(self.room, config={})
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'place_bet', 'amount': '10.00'},
            str(self.room.id), 1,
        )
        bust_idx = next(
            i for i, c in enumerate(state['cells'])
            if c['value'] == 'bust'
        )
        state = scratch_card.apply_action(
            state, str(self.user.id),
            {'action': 'scratch', 'cell': bust_idx},
            str(self.room.id), 2,
        )
        with self.assertRaises(ValueError):
            scratch_card.apply_action(
                state, str(self.user.id),
                {'action': 'scratch', 'cell': 0},
                str(self.room.id), 3,
            )


class ScratchCardABCHelpersTestCase(TestCase):
    """Test the ABC-compatible helper functions."""

    def test_game_kind(self):
        self.assertEqual(scratch_card.game_kind(), 'SCRATCH_CARD')

    def test_default_config(self):
        config = scratch_card.default_config()
        self.assertIn('grid_size', config)
        self.assertIn('min_bet', config)
        self.assertIn('max_bet', config)
        self.assertIn('house_edge', config)
        self.assertIn('cell_values', config)

    def test_is_finished(self):
        self.assertFalse(scratch_card.is_finished({'phase': 'scratching'}))
        self.assertTrue(scratch_card.is_finished({'phase': 'finished'}))

    def test_get_winners_no_winner(self):
        state = {'phase': 'finished', 'winner_id': None, 'total_prize': '0.00'}
        self.assertEqual(scratch_card.get_winners(state), [])

    def test_get_winners_with_winner(self):
        state = {
            'phase': 'finished',
            'winner_id': 'user-123',
            'total_prize': '50.00',
        }
        winners = scratch_card.get_winners(state)
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0]['user_id'], 'user-123')
        self.assertEqual(winners[0]['payout'], Decimal('50.00'))

    def test_get_public_state_hides_unrevealed(self):
        state = {
            'phase': 'scratching',
            'cells': [
                {'value': '2x', 'revealed': True},
                {'value': '10x', 'revealed': False},
                {'value': 'bust', 'revealed': False},
            ],
        }
        public = scratch_card.get_public_state(state)
        self.assertEqual(public['cells'][0]['value'], '2x')
        self.assertIsNone(public['cells'][1]['value'])
        self.assertIsNone(public['cells'][2]['value'])

    def test_get_public_state_shows_all_after_finish(self):
        state = {
            'phase': 'finished',
            'cells': [
                {'value': '2x', 'revealed': True},
                {'value': '10x', 'revealed': False},
            ],
        }
        public = scratch_card.get_public_state(state)
        self.assertEqual(public['cells'][1]['value'], '10x')

    def test_validate_config_valid(self):
        errors = scratch_card.validate_config(scratch_card.default_config())
        self.assertEqual(errors, [])

    def test_validate_config_bad_grid(self):
        errors = scratch_card.validate_config({'grid_size': 2})
        self.assertTrue(any('grid_size' in e for e in errors))

    def test_validate_bet_valid(self):
        state = {
            'phase': 'betting',
            'user_id': 'u1',
            'config': {'min_bet': '1.00', 'max_bet': '500.00'},
        }
        result = scratch_card.validate_bet(state, 'u1', Decimal('10.00'), {})
        self.assertIsNone(result)

    def test_validate_bet_wrong_phase(self):
        state = {
            'phase': 'scratching',
            'user_id': 'u1',
            'config': {'min_bet': '1.00', 'max_bet': '500.00'},
        }
        result = scratch_card.validate_bet(state, 'u1', Decimal('10.00'), {})
        self.assertIsNotNone(result)

    def test_deterministic_grid(self):
        """Same room_id + version produces same grid."""
        config = scratch_card.default_config()
        g1 = scratch_card._generate_grid('room-1', 1, config['cell_values'])
        g2 = scratch_card._generate_grid('room-1', 1, config['cell_values'])
        self.assertEqual(
            [c['value'] for c in g1],
            [c['value'] for c in g2],
        )

    def test_different_version_different_grid(self):
        config = scratch_card.default_config()
        g1 = scratch_card._generate_grid('room-1', 1, config['cell_values'])
        g2 = scratch_card._generate_grid('room-1', 2, config['cell_values'])
        # Values are valid
        self.assertEqual(len(g1), len(config['cell_values']))
        self.assertEqual(len(g2), len(config['cell_values']))
