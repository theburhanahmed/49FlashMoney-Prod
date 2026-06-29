from rest_framework import serializers
from apps.payments.models import StripeCustomer, PaymentIntent, RazorpayOrder
from apps.transactions.models import Transaction


class CreateRazorpayOrderSerializer(serializers.Serializer):
    """Serializer for creating a Razorpay order (India: UPI, cards, netbanking)."""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    currency = serializers.CharField(default="INR", max_length=3, required=False)


class VerifyRazorpayPaymentSerializer(serializers.Serializer):
    """Serializer for verifying Razorpay payment after checkout."""
    razorpay_order_id = serializers.CharField(required=True)
    razorpay_payment_id = serializers.CharField(required=True)
    razorpay_signature = serializers.CharField(required=True)


class PaymentIntentSerializer(serializers.ModelSerializer):
    """Serializer for PaymentIntent model"""
    class Meta:
        model = PaymentIntent
        fields = [
            'id', 'stripe_payment_intent_id', 'amount', 'currency',
            'status', 'client_secret', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'stripe_payment_intent_id', 'status', 'client_secret',
            'created_at', 'updated_at'
        ]


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating a payment intent"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    payment_method_id = serializers.CharField(required=False, allow_blank=True)
    save_payment_method = serializers.BooleanField(default=False)


class ConfirmPaymentIntentSerializer(serializers.Serializer):
    """Serializer for confirming a payment intent"""
    payment_intent_id = serializers.CharField(required=True)
    payment_method_id = serializers.CharField(required=False, allow_blank=True)


class SavePaymentMethodSerializer(serializers.Serializer):
    """Serializer for saving a payment method"""
    payment_method_id = serializers.CharField(required=True)
    set_as_primary = serializers.BooleanField(default=False)


class StripeCustomerSerializer(serializers.ModelSerializer):
    """Serializer for StripeCustomer model"""
    class Meta:
        model = StripeCustomer
        fields = ['id', 'stripe_customer_id', 'created_at']
        read_only_fields = ['id', 'stripe_customer_id', 'created_at']

