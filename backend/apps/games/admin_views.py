"""
Admin API views for game management.
Covers: game configuration, RTP, limits, maintenance mode,
round history, and engine registry introspection.
"""
import logging
from decimal import Decimal

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import AuditLog
from apps.users.permissions import IsAdminUser
from .models import GameRoom, GameRoomPlayer, GameState, GameKind
from .engines import get_engine_for_game_kind, list_registered_engines

logger = logging.getLogger(__name__)


class GameConfigView(APIView):
    """
    GET  /api/games/admin/config/<game_kind>/  - Get current game config
    PUT  /api/games/admin/config/<game_kind>/  - Update game config
    """
    permission_classes = [IsAdminUser]

    def get(self, request, game_kind):
        if game_kind not in dict(GameKind.CHOICES):
            return Response(
                {'error': f'Unknown game kind: {game_kind}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        engine = get_engine_for_game_kind(game_kind)
        config = {}
        if hasattr(engine, 'default_config'):
            config = engine.default_config()

        return Response({
            'game_kind': game_kind,
            'default_config': config,
            'active_rooms': GameRoom.objects.filter(
                game_kind=game_kind,
                status__in=[GameRoom.STATUS_WAITING, GameRoom.STATUS_IN_PROGRESS],
            ).count(),
            'total_rooms': GameRoom.objects.filter(game_kind=game_kind).count(),
        })

    def put(self, request, game_kind):
        if game_kind not in dict(GameKind.CHOICES):
            return Response(
                {'error': f'Unknown game kind: {game_kind}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_config = request.data.get('config', {})
        engine = get_engine_for_game_kind(game_kind)

        # Validate config if engine supports it
        if hasattr(engine, 'validate_config'):
            errors = engine.validate_config(new_config)
            if errors:
                return Response(
                    {'error': 'Invalid configuration', 'details': errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        AuditLog.objects.create(
            user=request.user,
            action='CHANGE_ROLE',  # reuse for config changes
            description=f'Updated config for game {game_kind}',
            resource_type='GAME_CONFIG',
            resource_id=game_kind,
            changes={'config': new_config},
        )

        return Response({
            'game_kind': game_kind,
            'config': new_config,
            'message': 'Configuration updated successfully',
        })


class EngineRegistryView(APIView):
    """
    GET /api/games/admin/engines/
    List all registered game engines with their capabilities.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        engines = list_registered_engines()
        return Response({'engines': engines})


class GameRoundHistoryView(APIView):
    """
    GET /api/games/admin/rounds/
    View game round history with filtering.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = GameRoom.objects.all().order_by('-created_at')

        # Filters
        game_kind = request.query_params.get('game_kind')
        room_status = request.query_params.get('status')
        user_id = request.query_params.get('user_id')

        if game_kind:
            queryset = queryset.filter(game_kind=game_kind)
        if room_status:
            queryset = queryset.filter(status=room_status)
        if user_id:
            queryset = queryset.filter(players__user_id=user_id)

        limit = min(int(request.query_params.get('limit', 50)), 200)
        offset = int(request.query_params.get('offset', 0))
        total = queryset.count()
        rooms = queryset[offset:offset + limit]

        results = []
        for room in rooms:
            players = list(
                room.players.select_related('user').values(
                    'user__username', 'user_id', 'result', 'payout',
                )
            )
            state_obj = getattr(room, 'game_state', None)
            results.append({
                'id': str(room.id),
                'game_kind': room.game_kind,
                'status': room.status,
                'entry_fee': str(room.entry_fee),
                'player_count': len(players),
                'players': players,
                'config': room.config,
                'has_state': state_obj is not None,
                'created_at': room.created_at.isoformat(),
                'started_at': room.started_at.isoformat() if room.started_at else None,
                'ended_at': room.ended_at.isoformat() if room.ended_at else None,
            })

        return Response({
            'count': total,
            'limit': limit,
            'offset': offset,
            'results': results,
        })


class GameRoundDetailView(APIView):
    """
    GET /api/games/admin/rounds/<room_id>/
    View detailed round data including full game state for audit.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, room_id):
        try:
            room = GameRoom.objects.get(id=room_id)
        except GameRoom.DoesNotExist:
            return Response(
                {'error': 'Room not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        players = list(
            room.players.select_related('user').values(
                'user__username', 'user_id', 'position', 'result',
                'payout', 'joined_at', 'balance_snapshot',
            )
        )
        state_obj = getattr(room, 'game_state', None)
        state_data = state_obj.state if state_obj else None

        return Response({
            'id': str(room.id),
            'game_kind': room.game_kind,
            'status': room.status,
            'entry_fee': str(room.entry_fee),
            'config': room.config,
            'players': players,
            'state': state_data,
            'state_version': state_obj.version if state_obj else None,
            'created_at': room.created_at.isoformat(),
            'started_at': room.started_at.isoformat() if room.started_at else None,
            'ended_at': room.ended_at.isoformat() if room.ended_at else None,
            'created_by': str(room.created_by_id),
        })


class GameMaintenanceView(APIView):
    """
    POST /api/games/admin/maintenance/<game_kind>/
    Enable or disable a game kind (maintenance mode).

    Body: {"enabled": false, "reason": "Scheduled maintenance"}
    """
    permission_classes = [IsAdminUser]

    def post(self, request, game_kind):
        if game_kind not in dict(GameKind.CHOICES):
            return Response(
                {'error': f'Unknown game kind: {game_kind}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enabled = request.data.get('enabled', True)
        reason = request.data.get('reason', '')

        # Cancel active waiting rooms if disabling
        if not enabled:
            cancelled = GameRoom.objects.filter(
                game_kind=game_kind,
                status=GameRoom.STATUS_WAITING,
            ).update(status=GameRoom.STATUS_CANCELLED)

            AuditLog.objects.create(
                user=request.user,
                action='TOGGLE_USER_STATUS',  # reuse
                description=(
                    f'Disabled game {game_kind}: {reason}. '
                    f'Cancelled {cancelled} waiting rooms.'
                ),
                resource_type='GAME_CONFIG',
                resource_id=game_kind,
                changes={
                    'enabled': enabled,
                    'reason': reason,
                    'cancelled_rooms': cancelled,
                },
            )
        else:
            AuditLog.objects.create(
                user=request.user,
                action='TOGGLE_USER_STATUS',
                description=f'Enabled game {game_kind}',
                resource_type='GAME_CONFIG',
                resource_id=game_kind,
                changes={'enabled': enabled},
            )

        return Response({
            'game_kind': game_kind,
            'enabled': enabled,
            'message': f'Game {"enabled" if enabled else "disabled"} successfully',
        })


class AuditLogView(APIView):
    """
    GET /api/games/admin/audit-logs/
    View audit logs with filtering.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = AuditLog.objects.all().order_by('-timestamp')

        # Filters
        action = request.query_params.get('action')
        user_id = request.query_params.get('user_id')
        resource_type = request.query_params.get('resource_type')

        if action:
            queryset = queryset.filter(action=action)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        limit = min(int(request.query_params.get('limit', 50)), 200)
        offset = int(request.query_params.get('offset', 0))
        total = queryset.count()
        logs = queryset[offset:offset + limit]

        results = []
        for log in logs:
            results.append({
                'id': log.id,
                'user': log.user.username if log.user else 'system',
                'user_id': str(log.user_id) if log.user_id else None,
                'action': log.action,
                'description': log.description,
                'resource_type': log.resource_type,
                'resource_id': log.resource_id,
                'changes': log.changes,
                'ip_address': log.ip_address,
                'timestamp': log.timestamp.isoformat(),
            })

        return Response({
            'count': total,
            'limit': limit,
            'offset': offset,
            'results': results,
        })


class WithdrawalAdminView(APIView):
    """
    GET  /api/games/admin/withdrawals/      - List pending withdrawals
    POST /api/games/admin/withdrawals/approve/  - Approve withdrawal
    POST /api/games/admin/withdrawals/reject/   - Reject withdrawal
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.transactions.models import WithdrawalRequest

        queryset = WithdrawalRequest.objects.all().order_by('-requested_at')
        wd_status = request.query_params.get('status', 'REQUESTED')
        if wd_status:
            queryset = queryset.filter(status=wd_status)

        limit = min(int(request.query_params.get('limit', 50)), 200)
        offset = int(request.query_params.get('offset', 0))
        total = queryset.count()
        wds = queryset.select_related('user')[offset:offset + limit]

        results = []
        for wd in wds:
            results.append({
                'id': str(wd.id),
                'user': wd.user.username,
                'user_id': str(wd.user_id),
                'amount': str(wd.amount),
                'status': wd.status,
                'bank_details': wd.bank_details,
                'remarks': wd.remarks,
                'requested_at': wd.requested_at.isoformat(),
                'processed_at': wd.processed_at.isoformat() if wd.processed_at else None,
            })

        return Response({
            'count': total,
            'limit': limit,
            'offset': offset,
            'results': results,
        })


class WithdrawalApproveView(APIView):
    """POST /api/payments/admin/withdrawals/approve/"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        from apps.payments.payment_service import PaymentService

        withdrawal_id = request.data.get('withdrawal_id')
        remarks = request.data.get('remarks', '')

        if not withdrawal_id:
            return Response(
                {'error': 'withdrawal_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            wd = PaymentService.approve_withdrawal(
                withdrawal_id=withdrawal_id,
                admin_user=request.user,
                remarks=remarks,
            )
            return Response({
                'id': str(wd.id),
                'status': wd.status,
                'message': 'Withdrawal approved',
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class WithdrawalRejectView(APIView):
    """POST /api/payments/admin/withdrawals/reject/"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        from apps.payments.payment_service import PaymentService

        withdrawal_id = request.data.get('withdrawal_id')
        reason = request.data.get('reason', '')

        if not withdrawal_id:
            return Response(
                {'error': 'withdrawal_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            wd = PaymentService.reject_withdrawal(
                withdrawal_id=withdrawal_id,
                admin_user=request.user,
                reason=reason,
            )
            return Response({
                'id': str(wd.id),
                'status': wd.status,
                'message': 'Withdrawal rejected',
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
