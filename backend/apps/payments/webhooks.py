import stripe
import json
import logging
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from apps.payments.services import StripeService
from apps.payments.models import PaymentIntent
from apps.notifications.tasks import send_deposit_confirmation_email

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhook events
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return JsonResponse({'error': 'Webhook secret not configured'}, status=500)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Handle the event
    event_type = event['type']
    event_data = event['data']['object']

    logger.info(f"Received Stripe webhook: {event_type}")

    try:
        if event_type == 'payment_intent.succeeded':
            handle_payment_intent_succeeded(event_data)
        elif event_type == 'payment_intent.payment_failed':
            handle_payment_intent_failed(event_data)
        elif event_type == 'payment_intent.canceled':
            handle_payment_intent_canceled(event_data)
        elif event_type == 'payment_method.attached':
            logger.info(f"Payment method attached: {event_data.get('id')}")
        else:
            logger.info(f"Unhandled event type: {event_type}")

        return JsonResponse({'status': 'success'})

    except Exception as e:
        logger.error(f"Error processing webhook {event_type}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def handle_payment_intent_succeeded(event_data):
    """Handle successful payment intent"""
    payment_intent_id = event_data['id']
    amount = event_data['amount'] / 100  # Convert from cents

    logger.info(f"Processing successful payment: {payment_intent_id}")

    try:
        payment_intent = StripeService.handle_payment_success(payment_intent_id)

        # Send confirmation email
        if payment_intent.user:
            send_deposit_confirmation_task.delay(
                str(payment_intent.user.id),
                str(payment_intent.transaction.id) if payment_intent.transaction else None
            )

        logger.info(f"Successfully processed payment: {payment_intent_id}")

    except Exception as e:
        logger.error(f"Error handling payment success: {e}")
        raise


def handle_payment_intent_failed(event_data):
    """Handle failed payment intent"""
    payment_intent_id = event_data['id']
    error_message = event_data.get('last_payment_error', {}).get('message', 'Payment failed')

    logger.warning(f"Processing failed payment: {payment_intent_id} - {error_message}")

    try:
        StripeService.handle_payment_failure(payment_intent_id)
        logger.info(f"Successfully processed payment failure: {payment_intent_id}")
    except Exception as e:
        logger.error(f"Error handling payment failure: {e}")
        raise


def handle_payment_intent_canceled(event_data):
    """Handle canceled payment intent"""
    payment_intent_id = event_data['id']

    logger.info(f"Processing canceled payment: {payment_intent_id}")

    try:
        payment_intent = PaymentIntent.objects.get(
            stripe_payment_intent_id=payment_intent_id
        )
        payment_intent.status = 'canceled'
        payment_intent.save()

        if payment_intent.transaction:
            payment_intent.transaction.status = 'CANCELLED'
            payment_intent.transaction.save()

        logger.info(f"Successfully processed payment cancellation: {payment_intent_id}")
    except PaymentIntent.DoesNotExist:
        logger.error(f"Payment intent not found: {payment_intent_id}")
    except Exception as e:
        logger.error(f"Error handling payment cancellation: {e}")
        raise

