"""
Provider player-facing views for 49FlashMoney.

Endpoints:
  GET  /api/providers/                     List registered providers
  GET  /api/providers/<slug>/games/        Browse catalogue for a provider
  GET  /api/providers/<slug>/games/<id>/   Game detail
  POST /api/providers/sessions/            Launch a game session
  POST /api/providers/bets/               Place a bet
  GET  /api/providers/rounds/             Player's round history
  GET  /api/providers/health/             Health check all providers
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.wallet.services import InsufficientBalanceError

from .exceptions import (
    ProviderBetError,
    ProviderError,
    ProviderGameNotFoundError,
    ProviderSessionError,
)
from .models import ProviderGameCatalog, ProviderGameSession, ProviderRound
from .registry import registry
from .serializers import (
    LaunchGameRequestSerializer,
    PlaceBetRequestSerializer,
    ProviderGameCatalogSerializer,
    ProviderGameSessionSerializer,
    ProviderRoundSerializer,
)
from .services import ProviderService

logger = logging.getLogger(__name__)


class ProviderListView(APIView):
    """GET /api/providers/  — list all registered providers."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        adapters = registry.all()
        data = [
            {
                'slug': a.provider_slug,
                'display_name': a.display_name,
                'supports_demo': a.supports_demo_mode(),
                'currencies': a.supported_currencies(),
            }
            for a in adapters
        ]
        return Response(data)


class ProviderGameListView(APIView):
    """GET /api/providers/<slug>/games/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, slug: str):
        if not registry.is_registered(slug):
            return Response(
                {'error': f"Provider '{slug}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        category = request.query_params.get('category', '')
        qs = ProviderGameCatalog.objects.filter(
            provider__slug=slug, is_active=True,
        ).order_by('name')
        if category:
            qs = qs.filter(category=category)

        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        start = (page - 1) * page_size
        games = qs[start: start + page_size]
        serializer = ProviderGameCatalogSerializer(games, many=True)
        return Response({
            'count': qs.count(),
            'page': page,
            'page_size': page_size,
            'results': serializer.data,
        })


class ProviderGameDetailView(APIView):
    """GET /api/providers/<slug>/games/<game_id>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, slug: str, game_id: str):
        if not registry.is_registered(slug):
            return Response(
                {'error': f"Provider '{slug}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            game = ProviderGameCatalog.objects.get(
                provider__slug=slug,
                provider_game_id=game_id,
                is_active=True,
            )
        except ProviderGameCatalog.DoesNotExist:
            return Response(
                {'error': f"Game '{game_id}' not found for provider '{slug}'."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ProviderGameCatalogSerializer(game).data)


class LaunchGameView(APIView):
    """POST /api/providers/sessions/  — create a game session."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LaunchGameRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            db_session = ProviderService.launch_game(
                user=request.user,
                slug=data['slug'],
                provider_game_id=data['provider_game_id'],
                currency=data['currency'],
                language=data['language'],
                mode=data['mode'],
                return_url=data.get('return_url', ''),
            )
        except KeyError as exc:
            return Response(
                {'error': f"Provider not registered: {exc}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ProviderGameNotFoundError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ProviderSessionError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except ProviderError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            ProviderGameSessionSerializer(db_session).data,
            status=status.HTTP_201_CREATED,
        )


class PlaceBetView(APIView):
    """POST /api/providers/bets/  — place a bet."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PlaceBetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            prov_round = ProviderService.place_bet(
                user=request.user,
                session_id=str(data['session_id']),
                bet_amount=data['bet_amount'],
            )
        except InsufficientBalanceError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        except ProviderBetError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except ProviderError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error in PlaceBetView")
            return Response(
                {'error': 'An unexpected error occurred.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(ProviderRoundSerializer(prov_round).data, status=status.HTTP_201_CREATED)


class RoundHistoryView(APIView):
    """GET /api/providers/rounds/  — player's round history."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        slug = request.query_params.get('slug', '')
        limit = min(int(request.query_params.get('limit', 50)), 200)
        rounds = ProviderService.get_round_history(
            user=request.user,
            slug=slug or None,
            limit=limit,
        )
        return Response(ProviderRoundSerializer(rounds, many=True).data)


class ProviderHealthView(APIView):
    """GET /api/providers/health/  — health check for all providers."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        results = ProviderService.health_check_all()
        return Response(results)
