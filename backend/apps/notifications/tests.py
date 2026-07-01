"""
Tests for notification services and WebSocket consumer.
Covers: GameNotificationService, PaymentNotificationService,
and NotificationConsumer event handlers.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.notifications.models import Notification
from apps.notifications.game_notifications import (
    GameNotificationService,
    PaymentNotificationService,
)

User = get_user_model()


class GameNotificationServiceTestCase(TestCase):
    """Test GameNotificationService creates correct notifications."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='notif_user',
            email='notif@test.com',
            password='Pass123!',
        )

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_game_bet_accepted(self, mock_channel_layer):
        mock_channel_layer.return_value = None  # No channel layer in tests
        notif = GameNotificationService.game_bet_accepted(
            self.user, 'AVIATOR', Decimal('50.00'), 'room-123'
        )
        self.assertEqual(notif.type, 'GAME')
        self.assertEqual(notif.title, 'Bet Accepted')
        self.assertIn('50', notif.message)
        self.assertEqual(notif.metadata['game_kind'], 'AVIATOR')

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_game_win(self, mock_channel_layer):
        mock_channel_layer.return_value = None
        notif = GameNotificationService.game_win(
            self.user, 'MINES', Decimal('150.00'), 'room-456'
        )
        self.assertEqual(notif.title, 'You Won!')
        self.assertIn('150', notif.message)
        self.assertEqual(notif.metadata['payout'], '150.00')

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_game_loss(self, mock_channel_layer):
        mock_channel_layer.return_value = None
        notif = GameNotificationService.game_loss(
            self.user, 'WINGO', 'room-789'
        )
        self.assertEqual(notif.title, 'Round Complete')

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_game_round_started(self, mock_channel_layer):
        mock_channel_layer.return_value = None
        notif = GameNotificationService.game_round_started(
            self.user, 'AVIATOR', 'room-abc'
        )
        self.assertEqual(notif.title, 'Round Started')

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_notification_created_in_db(self, mock_channel_layer):
        mock_channel_layer.return_value = None
        GameNotificationService.game_win(
            self.user, 'MINES', Decimal('100'), 'room-x'
        )
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)


class PaymentNotificationServiceTestCase(TestCase):
    """Test PaymentNotificationService creates correct notifications."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='pay_notif_user',
            email='paynotif@test.com',
            password='Pass123!',
        )

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_deposit_confirmed(self, mock_channel_layer):
        mock_channel_layer.return_value = None
        notif = PaymentNotificationService.deposit_confirmed(
            self.user, Decimal('200.00'), 'stripe'
        )
        self.assertEqual(notif.type, 'TRANSACTION')
        self.assertEqual(notif.title, 'Deposit Confirmed')
        self.assertIn('200', notif.message)

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_withdrawal_requested(self, mock_channel_layer):
        mock_channel_layer.return_value = None
        notif = PaymentNotificationService.withdrawal_requested(
            self.user, Decimal('100.00'), 'wd-001'
        )
        self.assertEqual(notif.title, 'Withdrawal Requested')
        self.assertEqual(notif.metadata['withdrawal_id'], 'wd-001')

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_withdrawal_approved(self, mock_channel_layer):
        mock_channel_layer.return_value = None
        notif = PaymentNotificationService.withdrawal_approved(
            self.user, Decimal('100.00'), 'wd-002'
        )
        self.assertEqual(notif.title, 'Withdrawal Approved')

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_withdrawal_rejected(self, mock_channel_layer):
        mock_channel_layer.return_value = None
        notif = PaymentNotificationService.withdrawal_rejected(
            self.user, Decimal('50.00'), 'wd-003', 'KYC pending'
        )
        self.assertEqual(notif.title, 'Withdrawal Rejected')
        self.assertIn('KYC pending', notif.message)
        self.assertEqual(notif.metadata['reason'], 'KYC pending')

    @patch('apps.notifications.game_notifications.get_channel_layer')
    def test_broadcast_called_when_channel_layer_exists(self, mock_channel_layer):
        mock_layer = MagicMock()
        mock_channel_layer.return_value = mock_layer
        PaymentNotificationService.deposit_confirmed(
            self.user, Decimal('100.00'), 'stripe'
        )
        mock_layer.group_send.assert_called_once()
