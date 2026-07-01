"""
WebSocket consumer for real-time user notifications.

Connects each authenticated user to a personal channel group
``user_{user_id}`` so the platform can push events in real time:
- Game results, bet acceptance, round starts
- Payment confirmations, withdrawal status
- Promotions and system messages

Client connects to: ws://.../ws/notifications/?token=<JWT>
"""
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_user_from_token(token: str):
    """Validate JWT and return user, or None."""
    from rest_framework_simplejwt.tokens import AccessToken
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        validated = AccessToken(token)
        user_id = validated['user_id']
        return User.objects.get(id=user_id)
    except Exception:
        return None


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Personal notification channel for each authenticated user.

    Receives messages from the platform (via channel_layer.group_send)
    and forwards them to the connected WebSocket client.
    """

    async def connect(self):
        """Authenticate via JWT query param and join user group."""
        query_string = self.scope.get('query_string', b'').decode()
        params = dict(
            p.split('=', 1) for p in query_string.split('&') if '=' in p
        )
        token = params.get('token', '')

        user = await database_sync_to_async(_get_user_from_token)(token)
        if not user:
            await self.close(code=4001)
            return

        self.user = user
        self.group_name = f'user_{user.id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'user_id': str(user.id),
        }))

        logger.info(f"Notification WS connected: user={user.id}")

    async def disconnect(self, close_code):
        """Leave user group on disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )
            logger.info(
                f"Notification WS disconnected: user={self.user.id} "
                f"code={close_code}"
            )

    async def receive(self, text_data=None, bytes_data=None):
        """
        Client can send:
        - {"action": "mark_read", "notification_id": "..."}
        - {"action": "ping"}
        """
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get('action')
        if action == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
        elif action == 'mark_read':
            nid = data.get('notification_id')
            if nid:
                await self._mark_notification_read(nid)
                await self.send(text_data=json.dumps({
                    'type': 'notification_marked_read',
                    'notification_id': nid,
                }))

    # ── Event handlers (called by channel_layer.group_send) ───────────

    async def notification_event(self, event):
        """
        Handle a notification event pushed from the backend.
        Payload structure:
        {
            "type": "notification_event",
            "event_type": "deposit_confirmed" | "game_win" | ...,
            "payload": { ... }
        }
        """
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'event_type': event.get('event_type', 'unknown'),
            'payload': event.get('payload', {}),
        }))

    async def game_event(self, event):
        """Handle game-specific events (round started, bet accepted, etc.)."""
        await self.send(text_data=json.dumps({
            'type': 'game_event',
            'event_type': event.get('event_type', 'unknown'),
            'payload': event.get('payload', {}),
        }))

    async def payment_event(self, event):
        """Handle payment-specific events (deposit confirmed, etc.)."""
        await self.send(text_data=json.dumps({
            'type': 'payment_event',
            'event_type': event.get('event_type', 'unknown'),
            'payload': event.get('payload', {}),
        }))

    async def system_event(self, event):
        """Handle system-wide events (maintenance, announcements)."""
        await self.send(text_data=json.dumps({
            'type': 'system_event',
            'event_type': event.get('event_type', 'unknown'),
            'payload': event.get('payload', {}),
        }))

    # ── Helpers ───────────────────────────────────────────────────────

    @database_sync_to_async
    def _mark_notification_read(self, notification_id: str):
        """Mark a notification as read in the database."""
        from .models import Notification
        try:
            notif = Notification.objects.get(
                id=notification_id, user=self.user
            )
            notif.mark_as_read()
        except Notification.DoesNotExist:
            pass
