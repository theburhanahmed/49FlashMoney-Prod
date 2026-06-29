"""
Payment views for Stripe integration.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from apps.payments.services import StripeService
from apps.payments.serializers import (
    PaymentIntentSerializer,
    CreatePaymentIntentSerializer,
    ConfirmPaymentIntentSerializer,
    SavePaymentMethodSerializer,
    StripeCustomerSerializer,
    CreateRazorpayOrderSerializer,
    VerifyRazorpayPaymentSerializer,
)
from apps.payments.models import PaymentIntent, RazorpayOrder
from apps.payments.razorpay_service import RazorpayService
from apps.common.exceptions import PaymentError

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_intent(request):
    """
    Create a payment intent for deposit.
    POST /api/payments/create-intent/
    """
    from apps.users.responsible_gaming import ResponsibleGamingService
    
    serializer = CreatePaymentIntentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = request.user
        amount = serializer.validated_data['amount']
        payment_method_id = serializer.validated_data.get('payment_method_id')
        save_payment_method = serializer.validated_data.get('save_payment_method', False)

        # Check self-exclusion
        is_excluded, exclusion_reason = ResponsibleGamingService.check_self_exclusion(user)
        if is_excluded:
            return Response(
                {'error': exclusion_reason},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check deposit limits
        is_valid, error_message = ResponsibleGamingService.check_deposit_limit(user, float(amount))
        if not is_valid:
            return Response(
                {'error': error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_intent = StripeService.create_payment_intent(
            amount=amount,
            user=user,
            payment_method_id=payment_method_id,
            save_payment_method=save_payment_method
        )

        response_serializer = PaymentIntentSerializer(payment_intent)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error creating payment intent: {e}")
        return Response(
            {'error': 'Failed to create payment intent', 'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_payment_intent(request):
    """
    Confirm a payment intent.
    POST /api/payments/confirm-intent/
    """
    serializer = ConfirmPaymentIntentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment_intent_id = serializer.validated_data['payment_intent_id']
        payment_method_id = serializer.validated_data.get('payment_method_id')

        payment_intent = StripeService.confirm_payment_intent(
            payment_intent_id=payment_intent_id,
            payment_method_id=payment_method_id
        )

        # Check if payment succeeded
        if payment_intent.status == 'succeeded':
            # Handle successful payment
            StripeService.handle_payment_success(payment_intent_id)

        response_serializer = PaymentIntentSerializer(payment_intent)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error confirming payment intent: {e}")
        return Response(
            {'error': 'Failed to confirm payment intent', 'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_intent(request, payment_intent_id):
    """
    Get payment intent details.
    GET /api/payments/intent/<payment_intent_id>/
    """
    try:
        payment_intent = PaymentIntent.objects.get(
            stripe_payment_intent_id=payment_intent_id,
            user=request.user
        )
        serializer = PaymentIntentSerializer(payment_intent)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except PaymentIntent.DoesNotExist:
        return Response(
            {'error': 'Payment intent not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_payment_method(request):
    """
    Save a payment method to customer.
    POST /api/payments/save-method/
    """
    serializer = SavePaymentMethodSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment_method_id = serializer.validated_data['payment_method_id']
        set_as_primary = serializer.validated_data.get('set_as_primary', False)

        payment_method = StripeService.save_payment_method(
            user=request.user,
            payment_method_id=payment_method_id,
            set_as_primary=set_as_primary
        )

        return Response(
            {
                'message': 'Payment method saved successfully',
                'payment_method_id': payment_method.id,
                'last4': payment_method.card.last4 if hasattr(payment_method, 'card') else None,
                'brand': payment_method.card.brand if hasattr(payment_method, 'card') else None,
            },
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        logger.error(f"Error saving payment method: {e}")
        return Response(
            {'error': 'Failed to save payment method', 'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_payment_methods(request):
    """
    List saved payment methods for user.
    GET /api/payments/methods/
    """
    try:
        payment_methods = StripeService.list_payment_methods(request.user)
        return Response(
            {
                'payment_methods': [
                    {
                        'id': pm.id,
                        'type': pm.type,
                        'card': {
                            'last4': pm.card.last4 if hasattr(pm, 'card') else None,
                            'brand': pm.card.brand if hasattr(pm, 'card') else None,
                            'exp_month': pm.card.exp_month if hasattr(pm, 'card') else None,
                            'exp_year': pm.card.exp_year if hasattr(pm, 'card') else None,
                        } if hasattr(pm, 'card') else None
                    }
                    for pm in payment_methods
                ]
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error listing payment methods: {e}")
        return Response(
            {'error': 'Failed to list payment methods', 'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_payment_method(request, payment_method_id):
    """
    Delete a payment method.
    DELETE /api/payments/methods/<payment_method_id>/
    """
    try:
        StripeService.delete_payment_method(payment_method_id)
        return Response(
            {'message': 'Payment method deleted successfully'},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error deleting payment method: {e}")
        return Response(
            {'error': 'Failed to delete payment method', 'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stripe_customer(request):
    """
    Get or create Stripe customer for user.
    GET /api/payments/customer/
    """
    try:
        stripe_customer = StripeService.create_customer(request.user)
        serializer = StripeCustomerSerializer(stripe_customer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting Stripe customer: {e}")
        return Response(
            {'error': 'Failed to get Stripe customer', 'detail': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([])  # Public endpoint
def get_stripe_config(request):
    """
    Get Stripe public key for frontend.
    GET /api/payments/config/
    """
    from django.conf import settings
    return Response(
        {
            'public_key': settings.STRIPE_PUBLIC_KEY,
            'currency': settings.STRIPE_CURRENCY
        },
        status=status.HTTP_200_OK
    )


@csrf_exempt
@api_view(['POST'])
def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    POST /api/payments/webhook/
    """
    import stripe
    from django.conf import settings

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent['id']
        logger.info(f"Payment succeeded: {payment_intent_id}")
        try:
            StripeService.handle_payment_success(payment_intent_id)
        except Exception as e:
            logger.error(f"Error handling payment success: {e}")

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        payment_intent_id = payment_intent['id']
        logger.warning(f"Payment failed: {payment_intent_id}")
        try:
            StripeService.handle_payment_failure(payment_intent_id)
        except Exception as e:
            logger.error(f"Error handling payment failure: {e}")

    else:
        logger.info(f"Unhandled event type: {event['type']}")

    return Response({'status': 'success'}, status=status.HTTP_200_OK)


# ---------- Razorpay (India: UPI, cards, netbanking, wallets) ----------


@api_view(['GET'])
@permission_classes([])
def get_razorpay_config(request):
    """
    Get Razorpay key and currency for frontend.
    GET /api/payments/razorpay/config/
    """
    from django.conf import settings
    return Response(
        {
            'key_id': settings.RAZORPAY_KEY_ID,
            'currency': getattr(settings, 'RAZORPAY_CURRENCY', 'INR'),
            'available': RazorpayService.is_available(),
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_razorpay_order(request):
    """
    Create a Razorpay order for deposit (India: UPI, cards, netbanking, wallets).
    POST /api/payments/razorpay/create-order/
    """
    from apps.users.responsible_gaming import ResponsibleGamingService

    if not RazorpayService.is_available():
        return Response(
            {'error': 'Razorpay is not configured'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    serializer = CreateRazorpayOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    amount = serializer.validated_data['amount']
    currency = serializer.validated_data.get('currency', 'INR')

    is_excluded, exclusion_reason = ResponsibleGamingService.check_self_exclusion(user)
    if is_excluded:
        return Response(
            {'error': exclusion_reason},
            status=status.HTTP_403_FORBIDDEN
        )

    is_valid, error_message = ResponsibleGamingService.check_deposit_limit(user, float(amount))
    if not is_valid:
        return Response(
            {'error': error_message},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        order = RazorpayService.create_order(user, amount=amount, currency=currency)
        return Response(
            {
                'order_id': order.razorpay_order_id,
                'amount': str(order.amount),
                'currency': order.currency,
            },
            status=status.HTTP_201_CREATED
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Razorpay create order error: {e}")
        return Response(
            {'error': 'Failed to create payment order. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_razorpay_payment(request):
    """
    Verify Razorpay payment after successful checkout and credit wallet.
    POST /api/payments/razorpay/verify/
    """
    if not RazorpayService.is_available():
        return Response(
            {'error': 'Razorpay is not configured'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    serializer = VerifyRazorpayPaymentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    order_id = data['razorpay_order_id']
    payment_id = data['razorpay_payment_id']
    signature = data['razorpay_signature']

    if not RazorpayService.verify_payment_signature(order_id, payment_id, signature):
        return Response(
            {'error': 'Payment verification failed'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        order = RazorpayOrder.objects.get(
            razorpay_order_id=order_id,
            user=request.user
        )
    except RazorpayOrder.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        RazorpayService.handle_payment_success(order_id, razorpay_payment_id=payment_id)
        return Response(
            {'message': 'Payment successful', 'order_id': order_id},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Razorpay verify/handle success error: {e}")
        return Response(
            {'error': 'Failed to complete payment'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
def razorpay_webhook(request):
    """
    Handle Razorpay webhook (e.g. payment.captured).
    POST /api/payments/razorpay/webhook/
    """
    from django.conf import settings
    import hmac
    import hashlib

    if not RazorpayService.is_available():
        return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

    payload = request.body
    sig_header = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    if not webhook_secret:
        return Response({'status': 'success'}, status=status.HTTP_200_OK)

    try:
        expected_sig = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, sig_header):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': 'Invalid webhook'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

    event_type = event.get('event')
    if event_type == 'payment.captured':
        payment_entity = event.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')
        if order_id:
            try:
                RazorpayService.handle_payment_success(order_id, razorpay_payment_id=payment_id)
            except Exception as e:
                logger.error(f"Razorpay webhook handle_payment_success error: {e}")
    else:
        logger.info(f"Razorpay unhandled event: {event_type}")

    return Response({'status': 'success'}, status=status.HTTP_200_OK)
