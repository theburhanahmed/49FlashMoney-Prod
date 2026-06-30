"""
Wallet admin configuration for 49FlashMoney.
"""
from django.contrib import admin

from .models import Wallet, LedgerEntry


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'reserved_balance', 'currency', 'status', 'updated_at']
    list_filter = ['status', 'currency']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'balance', 'reserved_balance', 'created_at', 'updated_at']


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'wallet', 'entry_type', 'direction',
        'amount', 'balance_before', 'balance_after', 'idempotency_key',
    ]
    list_filter = ['entry_type', 'direction', 'created_at']
    search_fields = [
        'wallet__user__username', 'wallet__user__email',
        'reference_id', 'idempotency_key', 'description',
    ]
    readonly_fields = [
        'id', 'wallet', 'entry_type', 'direction', 'amount',
        'balance_before', 'balance_after', 'currency', 'reference_type',
        'reference_id', 'idempotency_key', 'description', 'metadata',
        'actor', 'created_at',
    ]
    ordering = ['-created_at']

    def has_change_permission(self, request, obj=None):
        """Ledger entries are immutable - no edits allowed."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Ledger entries are immutable - no deletes allowed."""
        return False
