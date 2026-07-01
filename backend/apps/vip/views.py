"""
VIP views – thin REST endpoints delegating to VIPService.
"""
import logging

from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsAdminUser
from .models import VIPTier, UserVIPStatus
from .services import VIPService

User = get_user_model()
logger = logging.getLogger(__name__)


class VIPViewSet(viewsets.ViewSet):
    """Player-facing VIP endpoints."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='status')
    def my_status(self, request):
        """GET /api/vip/status/ – current user's VIP status."""
        info = VIPService.get_tier_benefits(request.user)
        return Response(info)

    @action(detail=False, methods=['get'])
    def tiers(self, request):
        """GET /api/vip/tiers/ – list all VIP tiers."""
        tiers = VIPTier.objects.all().order_by('level')
        data = [{
            'id': str(t.id),
            'name': t.name,
            'level': t.level,
            'min_wagered': str(t.min_wagered),
            'cashback_percentage': str(t.cashback_percentage),
            'withdrawal_limit_multiplier': str(t.withdrawal_limit_multiplier),
            'benefits': t.benefits,
        } for t in tiers]
        return Response(data)

    @action(detail=False, methods=['post'])
    def cashback(self, request):
        """POST /api/vip/cashback/ – claim weekly cashback."""
        try:
            amount = VIPService.calculate_cashback(request.user)
            if amount > 0:
                return Response({
                    'message': f'Cashback of {amount} credited',
                    'amount': str(amount),
                })
            return Response({
                'message': 'No cashback available. You need net losses to earn cashback.',
                'amount': '0.00',
            })
        except Exception as e:
            logger.exception("Cashback error")
            return Response(
                {'error': 'Failed to process cashback'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VIPAdminViewSet(viewsets.ViewSet):
    """Admin VIP management endpoints."""
    permission_classes = [IsAdminUser]

    def list(self, request):
        """GET /api/vip/admin/tiers/ – list all tiers."""
        tiers = VIPTier.objects.all().order_by('level')
        data = [{
            'id': str(t.id),
            'name': t.name,
            'level': t.level,
            'min_wagered': str(t.min_wagered),
            'cashback_percentage': str(t.cashback_percentage),
            'withdrawal_limit_multiplier': str(t.withdrawal_limit_multiplier),
            'benefits': t.benefits,
            'member_count': t.members.count(),
        } for t in tiers]
        return Response(data)

    def create(self, request):
        """POST /api/vip/admin/tiers/ – create a tier."""
        data = request.data
        if not data.get('name') or 'level' not in data:
            return Response(
                {'error': 'name and level are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tier = VIPService.admin_create_tier(request.user, data)
            return Response({
                'id': str(tier.id),
                'name': tier.name,
                'level': tier.level,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """PUT /api/vip/admin/tiers/<id>/ – update a tier."""
        try:
            tier = VIPService.admin_update_tier(request.user, pk, request.data)
            return Response({
                'id': str(tier.id),
                'name': tier.name,
                'message': 'Tier updated',
            })
        except VIPTier.DoesNotExist:
            return Response({'error': 'Tier not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def members(self, request):
        """GET /api/vip/admin/tiers/members/?tier_id=... – list VIP members."""
        tier_id = request.query_params.get('tier_id')
        qs = UserVIPStatus.objects.select_related('user', 'tier').order_by('-total_wagered')
        if tier_id:
            qs = qs.filter(tier_id=tier_id)
        data = [{
            'user_id': str(s.user.id),
            'username': s.user.username,
            'tier': s.tier.name,
            'total_wagered': str(s.total_wagered),
            'promoted_at': s.promoted_at.isoformat() if s.promoted_at else None,
        } for s in qs[:100]]
        return Response(data)

    @action(detail=False, methods=['post'], url_path='set-tier')
    def set_tier(self, request):
        """POST /api/vip/admin/tiers/set-tier/ – manually set user's tier."""
        user_id = request.data.get('user_id')
        tier_id = request.data.get('tier_id')
        if not user_id or not tier_id:
            return Response(
                {'error': 'user_id and tier_id are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            target = User.objects.get(id=user_id)
            VIPService.admin_set_tier(request.user, target, tier_id)
            return Response({'message': 'Tier updated successfully'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except VIPTier.DoesNotExist:
            return Response({'error': 'Tier not found'}, status=status.HTTP_404_NOT_FOUND)
