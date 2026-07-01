"""
Provider URL configuration for 49FlashMoney.

Mount at /api/providers/ in lottery/urls.py:
    path('api/providers/', include('apps.providers.urls')),
"""
from django.urls import path

from .admin_views import (
    AdminCatalogSyncView,
    AdminProviderConfigListView,
    AdminProviderCredentialsView,
    AdminRoundDetailView,
    AdminRoundListView,
    AdminRoundRefundView,
    AdminRoundSettleView,
)
from .views import (
    LaunchGameView,
    PlaceBetView,
    ProviderGameDetailView,
    ProviderGameListView,
    ProviderHealthView,
    ProviderListView,
    RoundHistoryView,
)

urlpatterns = [
    # Player-facing
    path('', ProviderListView.as_view(), name='provider-list'),
    path('<str:slug>/games/', ProviderGameListView.as_view(), name='provider-game-list'),
    path('<str:slug>/games/<str:game_id>/', ProviderGameDetailView.as_view(), name='provider-game-detail'),
    path('sessions/', LaunchGameView.as_view(), name='provider-launch-session'),
    path('bets/', PlaceBetView.as_view(), name='provider-place-bet'),
    path('rounds/', RoundHistoryView.as_view(), name='provider-round-history'),
    path('health/', ProviderHealthView.as_view(), name='provider-health'),

    # Admin
    path('admin/configs/', AdminProviderConfigListView.as_view(), name='admin-provider-configs'),
    path(
        'admin/configs/<str:slug>/credentials/',
        AdminProviderCredentialsView.as_view(),
        name='admin-provider-credentials',
    ),
    path('admin/catalog/sync/', AdminCatalogSyncView.as_view(), name='admin-catalog-sync'),
    path('admin/rounds/', AdminRoundListView.as_view(), name='admin-round-list'),
    path('admin/rounds/<str:round_id>/', AdminRoundDetailView.as_view(), name='admin-round-detail'),
    path(
        'admin/rounds/<str:round_id>/settle/',
        AdminRoundSettleView.as_view(),
        name='admin-round-settle',
    ),
    path(
        'admin/rounds/<str:round_id>/refund/',
        AdminRoundRefundView.as_view(),
        name='admin-round-refund',
    ),
]
