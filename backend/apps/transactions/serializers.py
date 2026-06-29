from rest_framework import serializers
from apps.transactions.models import Transaction, PaymentMethod, WithdrawalRequest
from apps.users.serializers import UserSerializer
from apps.lotteries.serializers import LotterySerializer


class TransactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    lottery = LotterySerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'type', 'amount', 'status', 'description',
            'lottery', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'method_type', 'is_primary', 'is_active',
            'payment_details', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    payment_method_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = WithdrawalRequest
        fields = [
            'id', 'user', 'amount', 'status', 'payment_method', 'payment_method_id',
            'bank_details', 'remarks', 'requested_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'requested_at', 'processed_at'
        ]
