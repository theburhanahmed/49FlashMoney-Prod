"""
Wallet API views for 49FlashMoney.
Views are thin - all business logic lives in WalletService.
"""
import logging

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User
from apps.users.permissions import IsAdminUser
from .models import Wallet, LedgerEntry
from .serializers import (
    WalletSerializer,
    LedgerEntrySerializer,
    AdminAdjustmentSerializer,
    ReconciliationSerializer,
)
from .services import (
    WalletService,
    InsufficientBalanceError,
    WalletFrozenError,
    DuplicateTransactionError,
)

logger = logging.getLogger(__name__)


class WalletDetailView(APIView):
    """
    GET /api/wallet/
    Returns the authenticated user's wallet balance and status.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        wallet = WalletService.get_or_create_wallet(request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


class LedgerHistoryView(APIView):
    """
    GET /api/wallet/ledger/
    Returns paginated ledger entries for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        limit = min(int(request.query_params.get('limit', 50)), 100)
        offset = int(request.query_params.get('offset', 0))
        entry_type = request.query_params.get('type')

        wallet = WalletService.get_or_create_wallet(request.user)
        entries = wallet.ledger_entries.all()

        if entry_type:
            entries = entries.filter(entry_type=entry_type)

        total = entries.count()
        entries = entries[offset:offset + limit]
        serializer = LedgerEntrySerializer(entries, many=True)

        return Response({
            'count': total,
            'limit': limit,
            'offset': offset,
            'results': serializer.data,
        })


class ReconcileView(APIView):
    """
    GET /api/wallet/reconcile/
    Reconcile cached balance against ledger-derived balance.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        result = WalletService.reconcile(request.user)
        return Response(result)


class AdminAdjustmentView(APIView):
    """
    POST /api/wallet/admin/adjust/
    Admin-only endpoint to credit or debit a user's wallet.
    Requires reason and idempotency key.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = AdminAdjustmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            user = User.objects.get(id=data['user_id'])
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            entry = WalletService.admin_adjustment(
                user=user,
                amount=data['amount'],
                direction=data['direction'],
                reason=data['reason'],
                admin_user=request.user,
                idempotency_key=data['idempotency_key'],
            )
            return Response(
                LedgerEntrySerializer(entry).data,
                status=status.HTTP_201_CREATED,
            )
        except DuplicateTransactionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_409_CONFLICT,
            )
        except InsufficientBalanceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except WalletFrozenError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )


class AdminWalletLookupView(APIView):
    """
    GET /api/wallet/admin/lookup/<user_id>/
    Admin-only endpoint to view any user's wallet and ledger.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        wallet = WalletService.get_or_create_wallet(user)
        wallet_data = WalletSerializer(wallet).data

        limit = min(int(request.query_params.get('limit', 50)), 100)
        offset = int(request.query_params.get('offset', 0))
        entries = wallet.ledger_entries.all()[offset:offset + limit]
        entries_data = LedgerEntrySerializer(entries, many=True).data

        return Response({
            'wallet': wallet_data,
            'ledger_entries': entries_data,
        })


class AdminReconcileView(APIView):
    """
    GET /api/wallet/admin/reconcile/<user_id>/
    Admin-only reconciliation for any user.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = WalletService.reconcile(user)
        return Response(result)
