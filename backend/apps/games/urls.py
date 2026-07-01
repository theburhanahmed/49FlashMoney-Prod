from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameRoomViewSet
from .admin_views import (
    GameConfigView,
    EngineRegistryView,
    GameRoundHistoryView,
    GameRoundDetailView,
    GameMaintenanceView,
    AuditLogView,
    WithdrawalAdminView,
    WithdrawalApproveView,
    WithdrawalRejectView,
)

router = DefaultRouter()
router.register(r'rooms', GameRoomViewSet, basename='gameroom')

urlpatterns = [
    path('', include(router.urls)),

    # Admin endpoints
    path('admin/engines/', EngineRegistryView.as_view(), name='admin-engines'),
    path('admin/config/<str:game_kind>/', GameConfigView.as_view(), name='admin-game-config'),
    path('admin/maintenance/<str:game_kind>/', GameMaintenanceView.as_view(), name='admin-game-maintenance'),
    path('admin/rounds/', GameRoundHistoryView.as_view(), name='admin-rounds'),
    path('admin/rounds/<uuid:room_id>/', GameRoundDetailView.as_view(), name='admin-round-detail'),
    path('admin/audit-logs/', AuditLogView.as_view(), name='admin-audit-logs'),
    path('admin/withdrawals/', WithdrawalAdminView.as_view(), name='admin-withdrawals'),
    path('admin/withdrawals/approve/', WithdrawalApproveView.as_view(), name='admin-withdrawal-approve'),
    path('admin/withdrawals/reject/', WithdrawalRejectView.as_view(), name='admin-withdrawal-reject'),
]
