"""
Wallet serializers for 49FlashMoney.
"""
from decimal import Decimal

from rest_framework import serializers

from .models import Wallet, LedgerEntry


class WalletSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Wallet
        fields = [
            'id', 'username', 'balance', 'reserved_balance',
            'available_balance', 'currency', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = [
            'id', 'entry_type', 'direction', 'amount',
            'balance_before', 'balance_after', 'currency',
            'reference_type', 'reference_id', 'idempotency_key',
            'description', 'metadata', 'actor', 'created_at',
        ]
        read_only_fields = fields


class DepositSerializer(serializers.Serializer):
    """Serializer for deposit requests."""
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('1.00'),
        max_value=Decimal('100000.00'),
    )
    idempotency_key = serializers.CharField(
        max_length=255,
        required=True,
        help_text='Unique key to prevent duplicate deposits.',
    )
    payment_reference = serializers.CharField(
        max_length=255,
        required=False,
        default='',
    )


class WithdrawSerializer(serializers.Serializer):
    """Serializer for withdrawal requests."""
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('10.00'),
        max_value=Decimal('10000.00'),
    )
    idempotency_key = serializers.CharField(
        max_length=255,
        required=True,
        help_text='Unique key to prevent duplicate withdrawals.',
    )
    bank_details = serializers.DictField(required=False, default=dict)


class AdminAdjustmentSerializer(serializers.Serializer):
    """Serializer for admin balance adjustments."""
    user_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
    )
    direction = serializers.ChoiceField(choices=['CREDIT', 'DEBIT'])
    reason = serializers.CharField(max_length=500)
    idempotency_key = serializers.CharField(max_length=255, required=True)


class ReconciliationSerializer(serializers.Serializer):
    """Output serializer for reconciliation results."""
    user_id = serializers.CharField()
    derived_balance = serializers.CharField()
    cached_balance = serializers.CharField()
    match = serializers.BooleanField()
    difference = serializers.CharField()
