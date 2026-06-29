"""
Game room services: create, join, start, end.
Wallet, transactions, responsible gaming, and broadcast via Channels.
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.users.models import User, UserProfile, AuditLog
from apps.users.responsible_gaming import ResponsibleGamingService
from apps.transactions.models import Transaction
from .models import GameRoom, GameRoomPlayer, GameState, GameKind
from .engines import get_engine_for_game_kind

logger = logging.getLogger(__name__)

# Per-game entry fee limits (min, max)
GAME_ENTRY_LIMITS = {
    GameKind.SNAKES_LADDERS: (Decimal('0.10'), Decimal('100.00')),
    GameKind.LUDO: (Decimal('0.10'), Decimal('100.00')),
    GameKind.CARROM: (Decimal('0.10'), Decimal('100.00')),
}


def _get_entry_limits(game_kind: str):
    return GAME_ENTRY_LIMITS.get(game_kind, (Decimal('0.10'), Decimal('100.00')))


def _broadcast_game_state(room_id: str, payload: dict):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    group_name = f'room_{room_id}'
    async_to_sync(channel_layer.group_send)(
        group_name,
        {'type': 'game_state_broadcast', 'payload': payload},
    )


@transaction.atomic
def create_room(user, game_kind: str, entry_fee: Decimal, config: dict = None):
    """
    Create a new game room (WAITING). Creator is first player. No wallet deduction yet.
    """
    if game_kind not in dict(GameKind.CHOICES):
        raise ValueError(f'Unknown game kind: {game_kind}')
    min_fee, max_fee = _get_entry_limits(game_kind)
    entry_fee = Decimal(str(entry_fee))
    if entry_fee < min_fee or entry_fee > max_fee:
        raise ValueError(f'Entry fee must be between {min_fee} and {max_fee}')

    # Default player counts; can be customized per game kind if needed.
    min_players = 2
    max_players = 4

    room = GameRoom.objects.create(
        game_kind=game_kind,
        status=GameRoom.STATUS_WAITING,
        entry_fee=entry_fee,
        min_players=min_players,
        max_players=max_players,
        created_by=user,
        config=config or {},
    )
    GameRoomPlayer.objects.create(room=room, user=user, position=0)
    logger.info(f'Game room created: {room.id} by {user.id}')
    return room


@transaction.atomic
def join_room(user, room_id: str):
    """Add user to room if WAITING and not full.

    Making this operation idempotent for a given user+room:
    if the user is already in the room, we simply return the room
    instead of raising an error. This plays nicer with the frontend
    join flow where the creator may click "Join" on their own room.
    No auto-start.
    """
    room = GameRoom.objects.get(id=room_id)
    if room.status != GameRoom.STATUS_WAITING:
        raise ValueError('Room is not waiting for players')
    if room.players.filter(user=user).exists():
        # User already in room - treat as success
        logger.info(f'User {user.id} re-joined room {room_id} (already a player)')
        return room
    current_count = room.players.count()
    if current_count >= room.max_players:
        raise ValueError('Room is full')

    position = current_count
    GameRoomPlayer.objects.create(room=room, user=user, position=position)
    logger.info(f'User {user.id} joined room {room_id}')
    return room


@transaction.atomic
def start_game(room_id: str, started_by_user=None):
    """
    Transition WAITING -> IN_PROGRESS: deduct entry fee from each player,
    create GameState, broadcast state. Any player can start if min_players reached.
    """
    room = GameRoom.objects.select_for_update().get(id=room_id)
    if room.status != GameRoom.STATUS_WAITING:
        raise ValueError('Room is not in waiting state')
    players = list(room.players.order_by('position').select_related('user'))
    if len(players) < room.min_players:
        raise ValueError(f'Need at least {room.min_players} players to start')

    entry_fee = room.entry_fee
    for rp in players:
        u = rp.user
        is_excluded, exclusion_reason = ResponsibleGamingService.check_self_exclusion(u)
        if is_excluded:
            raise ValueError(f'Player {u.username} is excluded: {exclusion_reason}')
        is_valid, error_msg, _ = ResponsibleGamingService.check_session_time(u)
        if not is_valid:
            raise ValueError(error_msg or 'Session limit exceeded')
        is_valid, error_msg = ResponsibleGamingService.check_loss_limit(u, entry_fee)
        if not is_valid:
            raise ValueError(error_msg or 'Daily loss limit exceeded')
        if u.wallet_balance < entry_fee:
            raise ValueError(f'Insufficient balance for player {u.username}')

    # Deduct and create transactions
    for rp in players:
        u = rp.user
        u.deduct_balance(entry_fee)
        rp.balance_snapshot = u.wallet_balance
        rp.save()
        Transaction.objects.create(
            user=u,
            type='GAME_ENTRY',
            amount=entry_fee,
            status='COMPLETED',
            description=f'Game entry: {room.get_game_kind_display()}',
            reference_id=str(room.id),
            game_room=room,
        )
        profile, _ = UserProfile.objects.get_or_create(user=u)
        profile.total_spent += entry_fee
        profile.save()

    room.status = GameRoom.STATUS_IN_PROGRESS
    room.started_at = timezone.now()
    room.save()

    # Create initial game state using the appropriate engine
    engine = get_engine_for_game_kind(room.game_kind)
    state_dict = engine.initial_state(room, room.config)

    GameState.objects.create(room=room, state=state_dict, version=0)

    # Broadcast so connected WebSocket clients get state
    _broadcast_game_state(str(room_id), state_dict)

    logger.info(f'Game started: room {room_id}')
    return room


@transaction.atomic
def end_game(room_id: str, results: list = None):
    """
    Set room COMPLETED, set each player result/payout, credit winners, create transactions.
    results: optional list of dicts { user_id, result, payout }. If None, derived from GameState winner_id.
    """
    room = GameRoom.objects.select_for_update().get(id=room_id)
    if room.status != GameRoom.STATUS_IN_PROGRESS and room.status != GameRoom.STATUS_WAITING:
        raise ValueError('Room is not in progress')

    room.status = GameRoom.STATUS_COMPLETED
    room.ended_at = timezone.now()
    room.save()

    players = list(room.players.select_related('user').order_by('position'))
    pool = room.entry_fee * len(players)
    state = getattr(room, 'game_state', None)
    state_data = state.state if state else {}

    if results:
        result_map = {r['user_id']: r for r in results}
    else:
        winner_id = state_data.get('winner_id')
        result_map = {}
        for rp in players:
            uid = str(rp.user_id)
            if uid == winner_id:
                result_map[uid] = {'user_id': uid, 'result': GameRoomPlayer.RESULT_WON, 'payout': pool}
            else:
                result_map[uid] = {'user_id': uid, 'result': GameRoomPlayer.RESULT_LOST, 'payout': Decimal('0')}

    for rp in players:
        uid = str(rp.user_id)
        r = result_map.get(uid, {'result': GameRoomPlayer.RESULT_LOST, 'payout': Decimal('0')})
        result = r.get('result', GameRoomPlayer.RESULT_LOST)
        payout = Decimal(str(r.get('payout', 0)))
        rp.result = result
        rp.payout = payout
        rp.save()

        u = rp.user
        if payout > 0:
            u.add_balance(payout)
            Transaction.objects.create(
                user=u,
                type='GAME_WIN',
                amount=payout,
                status='COMPLETED',
                description=f'Game win: {room.get_game_kind_display()}',
                reference_id=str(room.id),
                game_room=room,
            )
            profile, _ = UserProfile.objects.get_or_create(user=u)
            profile.total_won += payout
            profile.total_wins += 1
            profile.save()

    # Broadcast final state
    payload = {**state_data, 'phase': 'finished', 'room_status': 'COMPLETED'}
    _broadcast_game_state(str(room_id), payload)

    logger.info(f'Game ended: room {room_id}')
    return room
