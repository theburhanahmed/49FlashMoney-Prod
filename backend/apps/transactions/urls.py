from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.transactions.views import (
    TransactionViewSet, PaymentMethodViewSet, WithdrawalRequestViewSet,
    AdminTransactionViewSet
)

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'withdrawals', WithdrawalRequestViewSet, basename='withdrawal')
router.register(r'admin/transactions', AdminTransactionViewSet, basename='admin-transaction')

urlpatterns = [
    path('', include(router.urls)),
]
