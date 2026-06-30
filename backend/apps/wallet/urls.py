"""
Wallet URL patterns for 49FlashMoney.
"""
from django.urls import path

from .views import (
    WalletDetailView,
    LedgerHistoryView,
    ReconcileView,
    AdminAdjustmentView,
    AdminWalletLookupView,
    AdminReconcileView,
)

app_name = 'wallet'

urlpatterns = [
    # User-facing endpoints
    path('', WalletDetailView.as_view(), name='detail'),
    path('ledger/', LedgerHistoryView.as_view(), name='ledger'),
    path('reconcile/', ReconcileView.as_view(), name='reconcile'),

    # Admin endpoints
    path('admin/adjust/', AdminAdjustmentView.as_view(), name='admin-adjust'),
    path('admin/lookup/<uuid:user_id>/', AdminWalletLookupView.as_view(), name='admin-lookup'),
    path('admin/reconcile/<uuid:user_id>/', AdminReconcileView.as_view(), name='admin-reconcile'),
]
