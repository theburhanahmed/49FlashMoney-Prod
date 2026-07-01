"""
Promotions views for 49FlashMoney.

Views are intentionally thin – all business logic lives in PromotionService.
"""
import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import IsAdminUser, IsUserOrAdmin

from .models import Promotion, PromotionClaim
from .serializers import (
    ClaimPromotionSerializer,
    PromotionClaimSerializer,
    PromotionListSerializer,
    PromotionSerializer,
)
from .services import (
    PromotionAlreadyClaimedError,
    PromotionExpiredError,
    PromotionIneligibleError,
    PromotionMaxClaimsReachedError,
    PromotionNotActiveError,
    PromotionNotFoundError,
    PromotionService,
)

logger = logging.getLogger(__name__)


class PromotionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Promotion resources.

    Endpoints
    ---------
    GET    /promotions/            list       – all users (active promotions)
    GET    /promotions/<id>/       retrieve   – all users
    POST   /promotions/            create     – admin only
    PUT    /promotions/<id>/       update     – admin only
    PATCH  /promotions/<id>/       partial_update – admin only
    DELETE /promotions/<id>/       destroy    – admin only
    POST   /promotions/<id>/claim/ claim      – authenticated users
    GET    /promotions/my-claims/  my_claims  – authenticated users
    """

    queryset = Promotion.objects.all()

    # ── Permission dispatch ───────────────────────────────────────────────────

    def get_permissions(self):
        """
        - list / retrieve        → any authenticated user
        - create / update / destroy → admin only
        - claim / my_claims      → authenticated users (IsUserOrAdmin)
        """
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            permission_classes = [IsAdminUser]
        elif self.action in ('claim', 'my_claims'):
            permission_classes = [IsAuthenticated, IsUserOrAdmin]
        else:
            # list, retrieve
            permission_classes = [IsAuthenticated]
        return [perm() for perm in permission_classes]

    # ── Serializer dispatch ───────────────────────────────────────────────────

    def get_serializer_class(self):
        if self.action == 'list':
            return PromotionListSerializer
        if self.action == 'claim':
            return ClaimPromotionSerializer
        if self.action == 'my_claims':
            return PromotionClaimSerializer
        return PromotionSerializer

    # ── Standard CRUD (list & retrieve are read-only for all users) ───────────

    def list(self, request, *args, **kwargs):
        """
        Return active promotions the requesting user has not yet claimed.
        Regular users see only claimable promotions; admins see all.
        """
        if request.user.is_admin or request.user.role == 'admin':
            queryset = Promotion.objects.all().order_by('-created_at')
        else:
            queryset = PromotionService.get_available_promotions(request.user)

        serializer = PromotionListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Admin creates a new promotion."""
        serializer = PromotionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        promotion = PromotionService.create_promotion(
            admin_user=request.user,
            data=serializer.validated_data,
        )

        return Response(
            PromotionSerializer(promotion).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """Admin updates an existing promotion (full or partial)."""
        partial = kwargs.pop('partial', False)
        serializer = PromotionSerializer(
            self.get_object(),
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        try:
            promotion = PromotionService.update_promotion(
                admin_user=request.user,
                promotion_id=str(kwargs.get('pk') or self.kwargs.get('pk')),
                data=serializer.validated_data,
            )
        except PromotionNotFoundError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(PromotionSerializer(promotion).data)

    def destroy(self, request, *args, **kwargs):
        """Admin cancels a promotion (soft-delete to CANCELLED status)."""
        promotion_id = str(kwargs.get('pk') or self.kwargs.get('pk'))

        try:
            PromotionService.cancel_promotion(
                admin_user=request.user,
                promotion_id=promotion_id,
            )
        except PromotionNotFoundError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except PromotionNotActiveError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Custom actions ────────────────────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='claim')
    def claim(self, request, pk=None):
        """
        POST /promotions/<id>/claim/

        Authenticated users claim a promotion. For DEPOSIT_BONUS / CASHBACK
        promotions, pass ``deposit_amount`` in the request body.

        Returns the created PromotionClaim on success.
        """
        serializer = ClaimPromotionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        deposit_amount = serializer.validated_data.get('deposit_amount')

        try:
            claim = PromotionService.claim_promotion(
                user=request.user,
                promotion_id=str(pk),
                deposit_amount=deposit_amount,
            )
        except PromotionNotFoundError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except (PromotionNotActiveError, PromotionExpiredError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except PromotionMaxClaimsReachedError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except PromotionAlreadyClaimedError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        except PromotionIneligibleError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as exc:
            logger.exception(f"Unexpected error during promotion claim: {exc}")
            return Response(
                {'detail': 'An unexpected error occurred. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            PromotionClaimSerializer(claim).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'], url_path='my-claims')
    def my_claims(self, request):
        """
        GET /promotions/my-claims/

        Returns the authenticated user's promotion claim history.
        """
        claims = PromotionService.get_user_claims(request.user)
        serializer = PromotionClaimSerializer(claims, many=True)
        return Response(serializer.data)
