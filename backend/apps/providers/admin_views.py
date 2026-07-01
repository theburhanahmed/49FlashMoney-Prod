"""
Provider admin views for 49FlashMoney.

All endpoints require IsAdminUser.

Endpoints:
  GET  /api/providers/admin/configs/                   List provider configs
  POST /api/providers/admin/configs/<slug>/credentials/ Update credentials
  POST /api/providers/admin/catalog/sync/              Sync game catalogue
  GET  /api/providers/admin/rounds/                    All rounds (filterable)
  GET  /api/providers/admin/rounds/<round_id>/         Round detail
  POST /api/providers/admin/rounds/<round_id>/settle/  Manual settle
  POST /api/providers/admin/rounds/<round_id>/refund/  Manual refund
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminUser

from .exceptions import ProviderAuthError, ProviderError, ProviderRefundError, ProviderSettlementError
from .models import ProviderConfig, ProviderRound
from .registry import registry
from .serializers import (
    ProviderConfigSerializer,
    ProviderRoundSerializer,
    RefundRoundRequestSerializer,
    SettleRoundRequestSerializer,
)
from .services import ProviderService

logger = logging.getLogger(__name__)


class AdminProviderConfigListView(APIView):
    """GET /api/providers/admin/configs/"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        configs = ProviderConfig.objects.all().order_by('slug')
        # Augment with registry status
        data = []
        for cfg in configs:
            row = ProviderConfigSerializer(cfg).data
            row['adapter_registered'] = registry.is_registered(cfg.slug)
            data.append(row)
        return Response(data)


class AdminProviderCredentialsView(APIView):
    """POST /api/providers/admin/configs/<slug>/credentials/"""
    permission_classes = [IsAdminUser]

    def post(self, request, slug: str):
        credentials = request.data.get('credentials')
        if not isinstance(credentials, dict):
            return Response(
                {'error': "'credentials' must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        settings_data = request.data.get('settings', None)
        try:
            cfg = ProviderService.update_credentials(
                slug=slug,
                credentials=credentials,
                settings=settings_data,
            )
        except KeyError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ProviderAuthError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProviderConfigSerializer(cfg).data)


class AdminCatalogSyncView(APIView):
    """POST /api/providers/admin/catalog/sync/"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        slug = request.data.get('slug')
        if not slug:
            return Response({'error': "'slug' is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            count = ProviderService.sync_catalog(slug)
        except KeyError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ProviderError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'synced': count, 'provider': slug})


class AdminRoundListView(APIView):
    """GET /api/providers/admin/rounds/"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = ProviderRound.objects.select_related('user', 'provider', 'game').order_by('-created_at')
        slug = request.query_params.get('slug')
        status_filter = request.query_params.get('status')
        user_id = request.query_params.get('user_id')
        if slug:
            qs = qs.filter(provider__slug=slug)
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if user_id:
            qs = qs.filter(user_id=user_id)
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 200)
        start = (page - 1) * page_size
        total = qs.count()
        rounds = qs[start: start + page_size]
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': ProviderRoundSerializer(rounds, many=True).data,
        })


class AdminRoundDetailView(APIView):
    """GET /api/providers/admin/rounds/<round_id>/"""
    permission_classes = [IsAdminUser]

    def get(self, request, round_id: str):
        try:
            prov_round = ProviderRound.objects.select_related(
                'user', 'provider', 'game', 'session',
            ).get(round_id=round_id)
        except ProviderRound.DoesNotExist:
            return Response({'error': 'Round not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = ProviderRoundSerializer(prov_round).data
        data['raw_bet_response'] = prov_round.raw_bet_response
        data['raw_settle_response'] = prov_round.raw_settle_response
        data['error_message'] = prov_round.error_message
        data['bet_ledger_entry_id'] = prov_round.bet_ledger_entry_id
        data['payout_ledger_entry_id'] = prov_round.payout_ledger_entry_id
        return Response(data)


class AdminRoundSettleView(APIView):
    """POST /api/providers/admin/rounds/<round_id>/settle/"""
    permission_classes = [IsAdminUser]

    def post(self, request, round_id: str):
        serializer = SettleRoundRequestSerializer(data={**request.data, 'round_id': round_id})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            prov_round = ProviderService.settle_round(
                round_id=round_id,
                payout=serializer.validated_data['payout'],
            )
        except ProviderSettlementError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ProviderError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(ProviderRoundSerializer(prov_round).data)


class AdminRoundRefundView(APIView):
    """POST /api/providers/admin/rounds/<round_id>/refund/"""
    permission_classes = [IsAdminUser]

    def post(self, request, round_id: str):
        serializer = RefundRoundRequestSerializer(data={**request.data, 'round_id': round_id})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            prov_round = ProviderService.refund_round(
                round_id=round_id,
                reason=serializer.validated_data.get('reason', ''),
            )
        except ProviderRefundError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ProviderError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(ProviderRoundSerializer(prov_round).data)
