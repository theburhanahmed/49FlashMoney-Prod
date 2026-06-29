import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken

from django.contrib.auth import get_user_model
from .models import GameRoom, GameRoomPlayer, GameState, GameKind
from .engines import get_engine_for_game_kind
from .services import end_game

logger = logging.getLogger(__name__)
User = get_user_model()


def _get_user_from_token(token: str):
    """Validate JWT and return User or None."""
    if not token:
        return None
    try:
        access = AccessToken(token)
        user_id = access.get('user_id') or access.get('token_id')
        if not user_id:
            return None
        return User.objects.get(id=user_id)
    except (InvalidToken, User.DoesNotExist, Exception):
        return None


def _user_in_room(user_id, room_id: str) -> bool:
    return GameRoomPlayer.objects.filter(room_id=room_id, user_id=user_id).exists()


class GameRoomConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for game rooms. Validates JWT, joins room channel, handles game actions."""

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'room_{self.room_id}'

        # Token from query string: ?token=xxx
        qs = parse_qs(self.scope.get('query_string', b'').decode())
        token = (qs.get('token') or [None])[0]

        user = await sync_to_async(_get_user_from_token)(token)
        if not user:
            await self.close(code=4401)
            return

        in_room = await sync_to_async(_user_in_room)(user.id, self.room_id)
        if not in_room:
            await self.close(code=4403)
            return

        self.scope['user'] = user
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get('type', '')
            payload = data.get('payload', {})
            if msg_type == 'action':
                await self.handle_action(payload)
            else:
                await self.send(text_data=json.dumps({'type': 'error', 'payload': {'message': 'Unknown message type'}}))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'payload': {'message': 'Invalid JSON'}}))

    async def handle_action(self, payload):
        user = self.scope.get('user')
        if not user:
            await self.send(text_data=json.dumps({'type': 'error', 'payload': {'message': 'Not authenticated'}}))
            return

        result = await sync_to_async(self._apply_action_sync)(user, payload)
        if result.get('error'):
            await self.send(text_data=json.dumps({'type': 'error', 'payload': {'message': result['error']}}))
            return

        state_payload = result['state']
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'game_state_broadcast', 'payload': state_payload},
        )

        if result.get('game_ended'):
            await sync_to_async(end_game)(self.room_id)

    def _apply_action_sync(self, user, payload):
        """Run game engine and persist state. Returns dict with state or error."""
        try:
            room = GameRoom.objects.select_related('game_state').get(id=self.room_id)
        except GameRoom.DoesNotExist:
            return {'error': 'Room not found'}
        if room.status != GameRoom.STATUS_IN_PROGRESS:
            return {'error': 'Game is not in progress'}
        try:
            gs = room.game_state
        except GameState.DoesNotExist:
            return {'error': 'No game state'}

        state = gs.state
        version = gs.version

        engine = None
        try:
            engine = get_engine_for_game_kind(room.game_kind)
        except ValueError as e:
            return {'error': str(e)}

        try:
            new_state = engine.apply_action(
                state, str(user.id), payload, self.room_id, version
            )
        except ValueError as e:
            return {'error': str(e)}

        gs.state = new_state
        gs.version = version + 1
        gs.save()

        game_ended = bool(new_state.get('winner_id'))
        return {'state': new_state, 'game_ended': game_ended}

    async def game_state_broadcast(self, event):
        await self.send(text_data=json.dumps({'type': 'game_state', 'payload': event['payload']}))
