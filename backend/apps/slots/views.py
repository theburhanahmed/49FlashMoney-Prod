from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.slots.models import SlotsGame, SlotsSpin
from apps.slots.serializers import (
    SlotsGameSerializer,
    SlotsGameListSerializer,
    SlotsSpinSerializer,
    SlotsSpinRequestSerializer,
)
from apps.slots.services import SlotsSpinService


class SlotsGameViewSet(viewsets.ModelViewSet):
    """Manage slots games - list for all, create/update for admin."""
    queryset = SlotsGame.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['is_active']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return SlotsGameListSerializer
        return SlotsGameSerializer

    def get_queryset(self):
        if self.action == 'list' and not self.request.user.is_authenticated:
            return SlotsGame.objects.filter(is_active=True)
        if self.action == 'list' and not getattr(self.request.user, 'is_admin', False):
            return SlotsGame.objects.filter(is_active=True)
        return SlotsGame.objects.all()

    def create(self, request, *args, **kwargs):
        """Create game (admin only)."""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can create slots games'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update game (admin only)."""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can update slots games'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete game (admin only)."""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can delete slots games'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def spin(self, request, pk=None):
        """Place a bet and spin."""
        game = self.get_object()
        req_serializer = SlotsSpinRequestSerializer(data=request.data)
        if not req_serializer.is_valid():
            return Response(req_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        bet_amount = req_serializer.validated_data['bet_amount']

        try:
            result = SlotsSpinService.spin(request.user, str(game.id), bet_amount)
            return Response(result, status=status.HTTP_200_OK)
        except SlotsGame.DoesNotExist:
            return Response({'error': 'Game not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SlotsSpinViewSet(viewsets.ReadOnlyModelViewSet):
    """User's spin history - read only."""
    serializer_class = SlotsSpinSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SlotsSpin.objects.filter(user=self.request.user).select_related('game').order_by('-created_at')

    @action(detail=True, methods=['get'])
    def verify(self, request, pk=None):
        """Provably fair verification - recompute result from seed."""
        spin = self.get_object()
        if spin.user != request.user:
            return Response({'error': 'Not your spin'}, status=status.HTTP_403_FORBIDDEN)

        recomputed = SlotsSpinService._generate_spin_result(spin.game, spin.random_seed)
        return Response({
            'spin_id': str(spin.id),
            'stored_symbols': spin.symbols,
            'recomputed_symbols': recomputed,
            'verified': spin.symbols == recomputed,
            'random_seed': spin.random_seed,
        })
