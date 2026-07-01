"""
Slots views - thin REST endpoints delegating to SlotsService.
"""
import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.permissions import IsAdminUser
from .models import SlotsGame, SlotsSpin
from .services import SlotsService

logger = logging.getLogger(__name__)


class SlotsGameViewSet(viewsets.ModelViewSet):
    """
    ViewSet for slots games.
    List/retrieve: all authenticated users.
    Create/update/delete: admin only.
    """
    queryset = SlotsGame.objects.all()
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        qs = SlotsGame.objects.all()
        if not (self.request.user.is_admin or self.request.user.role == 'admin'):
            qs = qs.filter(is_active=True)
        return qs.order_by('-created_at')

    def list(self, request):
        games = self.get_queryset()
        data = []
        for g in games:
            data.append({
                'id': str(g.id),
                'name': g.name,
                'description': g.description,
                'is_active': g.is_active,
                'min_bet': str(g.min_bet),
                'max_bet': str(g.max_bet),
                'rtp_percent': str(g.rtp_percent),
            })
        return Response(data)

    def retrieve(self, request, pk=None):
        try:
            game = SlotsGame.objects.get(id=pk)
        except SlotsGame.DoesNotExist:
            return Response({'error': 'Game not found'}, status=status.HTTP_404_NOT_FOUND)
        data = {
            'id': str(game.id),
            'name': game.name,
            'description': game.description,
            'is_active': game.is_active,
            'min_bet': str(game.min_bet),
            'max_bet': str(game.max_bet),
            'rtp_percent': str(game.rtp_percent),
            'paytable': game.paytable,
        }
        return Response(data)

    def create(self, request):
        from .models import DEFAULT_REELS, DEFAULT_PAYTABLE
        data = request.data
        game = SlotsGame.objects.create(
            name=data.get('name', 'New Slots Game'),
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
            paytable=data.get('paytable', DEFAULT_PAYTABLE),
            reels=data.get('reels', DEFAULT_REELS),
            rtp_percent=data.get('rtp_percent', 96.00),
            min_bet=data.get('min_bet', 0.10),
            max_bet=data.get('max_bet', 100.00),
            created_by=request.user,
        )
        return Response({
            'id': str(game.id),
            'name': game.name,
            'message': 'Slots game created',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def spin(self, request, pk=None):
        """POST /api/slots/games/<game_id>/spin/"""
        from decimal import Decimal, InvalidOperation

        raw_amount = request.data.get('bet_amount')
        if not raw_amount:
            return Response(
                {'error': 'bet_amount is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bet_amount = Decimal(str(raw_amount))
            if bet_amount <= 0:
                return Response(
                    {'error': 'bet_amount must be greater than 0'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (InvalidOperation, ValueError, TypeError):
            return Response(
                {'error': 'bet_amount must be a valid number'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            spin_result = SlotsService.spin(
                user=request.user,
                game_id=pk,
                bet_amount=bet_amount,
            )
            return Response({
                'spin_id': str(spin_result.id),
                'symbols': spin_result.symbols,
                'payout': str(spin_result.payout),
                'bet_amount': str(spin_result.bet_amount),
                'won': spin_result.payout > 0,
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Spin error")
            return Response(
                {'error': 'An error occurred during spin'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """GET /api/slots/games/<game_id>/history/"""
        spins = SlotsService.get_spin_history(request.user, game_id=pk)
        data = [{
            'id': str(s.id),
            'symbols': s.symbols,
            'bet_amount': str(s.bet_amount),
            'payout': str(s.payout),
            'created_at': s.created_at.isoformat(),
        } for s in spins]
        return Response(data)

    @action(detail=True, methods=['get'], permission_classes=[IsAdminUser])
    def stats(self, request, pk=None):
        """GET /api/slots/games/<game_id>/stats/ (admin only)"""
        stats = SlotsService.get_game_stats(pk)
        return Response(stats)
