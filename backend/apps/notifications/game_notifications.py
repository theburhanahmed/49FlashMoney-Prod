"""
GameNotificationService – in-app and broadcast notifications
for game and payment events.

Creates Notification records and optionally broadcasts via
Django Channels for real-time delivery.
"""
import logging
from decimal import Decimal
from typing import Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification

logger = logging.getLogger(__name__)


def _broadcast_to_user(user_id: str, event_type: str, payload: dict):
    """Send a notification event to a user's personal channel."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f'user_{user_id}',
            {
                'type': 'notification_event',
                'event_type': event_type,
                'payload': payload,
            },
        )
    except Exception:
        logger.exception(f"Failed to broadcast notification to user {user_id}")


class GameNotificationService:
    """Creates notifications for game lifecycle events."""

    @classmethod
    def game_bet_accepted(cls, user, game_kind: str, amount: Decimal, room_id: str):
        notif = Notification.objects.create(
            user=user,
            type='GAME',
            title='Bet Accepted',
            message=f'Your bet of {amount} on {game_kind} has been accepted.',
            metadata={
                'event': 'bet_accepted',
                'game_kind': game_kind,
                'amount': str(amount),
                'room_id': str(room_id),
            },
        )
        _broadcast_to_user(str(user.id), 'bet_accepted', {
            'game_kind': game_kind, 'amount': str(amount), 'room_id': str(room_id),
        })
        return notif

    @classmethod
    def game_round_started(cls, user, game_kind: str, room_id: str):
        notif = Notification.objects.create(
            user=user,
            type='GAME',
            title='Round Started',
            message=f'Your {game_kind} round has started.',
            metadata={
                'event': 'round_started',
                'game_kind': game_kind,
                'room_id': str(room_id),
            },
        )
        _broadcast_to_user(str(user.id), 'round_started', {
            'game_kind': game_kind, 'room_id': str(room_id),
        })
        return notif

    @classmethod
    def game_win(cls, user, game_kind: str, payout: Decimal, room_id: str):
        notif = Notification.objects.create(
            user=user,
            type='GAME',
            title='You Won!',
            message=f'Congratulations! You won {payout} on {game_kind}.',
            metadata={
                'event': 'game_win',
                'game_kind': game_kind,
                'payout': str(payout),
                'room_id': str(room_id),
            },
        )
        _broadcast_to_user(str(user.id), 'game_win', {
            'game_kind': game_kind, 'payout': str(payout), 'room_id': str(room_id),
        })
        return notif

    @classmethod
    def game_loss(cls, user, game_kind: str, room_id: str):
        notif = Notification.objects.create(
            user=user,
            type='GAME',
            title='Round Complete',
            message=f'Your {game_kind} round has ended.',
            metadata={
                'event': 'game_loss',
                'game_kind': game_kind,
                'room_id': str(room_id),
            },
        )
        _broadcast_to_user(str(user.id), 'round_complete', {
            'game_kind': game_kind, 'room_id': str(room_id),
        })
        return notif


class PaymentNotificationService:
    """Creates notifications for payment events."""

    @classmethod
    def deposit_confirmed(cls, user, amount: Decimal, provider: str):
        notif = Notification.objects.create(
            user=user,
            type='TRANSACTION',
            title='Deposit Confirmed',
            message=f'Your deposit of {amount} has been confirmed.',
            metadata={
                'event': 'deposit_confirmed',
                'amount': str(amount),
                'provider': provider,
            },
        )
        _broadcast_to_user(str(user.id), 'deposit_confirmed', {
            'amount': str(amount), 'provider': provider,
        })
        return notif

    @classmethod
    def withdrawal_requested(cls, user, amount: Decimal, withdrawal_id: str):
        notif = Notification.objects.create(
            user=user,
            type='TRANSACTION',
            title='Withdrawal Requested',
            message=f'Your withdrawal of {amount} is being reviewed.',
            metadata={
                'event': 'withdrawal_requested',
                'amount': str(amount),
                'withdrawal_id': withdrawal_id,
            },
        )
        _broadcast_to_user(str(user.id), 'withdrawal_requested', {
            'amount': str(amount), 'withdrawal_id': withdrawal_id,
        })
        return notif

    @classmethod
    def withdrawal_approved(cls, user, amount: Decimal, withdrawal_id: str):
        notif = Notification.objects.create(
            user=user,
            type='TRANSACTION',
            title='Withdrawal Approved',
            message=f'Your withdrawal of {amount} has been approved.',
            metadata={
                'event': 'withdrawal_approved',
                'amount': str(amount),
                'withdrawal_id': withdrawal_id,
            },
        )
        _broadcast_to_user(str(user.id), 'withdrawal_approved', {
            'amount': str(amount), 'withdrawal_id': withdrawal_id,
        })
        return notif

    @classmethod
    def withdrawal_rejected(cls, user, amount: Decimal, withdrawal_id: str, reason: str = ''):
        notif = Notification.objects.create(
            user=user,
            type='TRANSACTION',
            title='Withdrawal Rejected',
            message=f'Your withdrawal of {amount} has been rejected. {reason}'.strip(),
            metadata={
                'event': 'withdrawal_rejected',
                'amount': str(amount),
                'withdrawal_id': withdrawal_id,
                'reason': reason,
            },
        )
        _broadcast_to_user(str(user.id), 'withdrawal_rejected', {
            'amount': str(amount), 'withdrawal_id': withdrawal_id, 'reason': reason,
        })
        return notif
