"""
Razorpay service for India-focused payments (UPI, cards, netbanking, wallets).
"""
import logging
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from apps.payments.models import RazorpayOrder
from apps.transactions.models import Transaction

logger = logging.getLogger(__name__)


def _get_client():
    """Return Razorpay client if configured."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return None
    try:
        import razorpay
        return razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    except Exception as e:
        logger.warning(f"Razorpay client not available: {e}")
        return None


class RazorpayService:
    """Service for Razorpay order creation, verification, and success handling."""

    @staticmethod
    def is_available():
        """Return True if Razorpay is configured."""
        return bool(
            settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET
        )

    @staticmethod
    def create_order(user, amount, currency=None):
        """
        Create a Razorpay order for deposit.
        Amount is in INR (or currency units); Razorpay expects amount in paise (INR * 100).
        Returns RazorpayOrder instance with razorpay_order_id set from API.
        """
        client = _get_client()
        if not client:
            raise ValueError("Razorpay is not configured")

        currency = (currency or settings.RAZORPAY_CURRENCY or "INR").upper()
        amount_decimal = Decimal(str(amount))

        # Razorpay amount in smallest currency unit (paise for INR)
        amount_paise = int(amount_decimal * 100)

        if amount_paise < 100:  # minimum 1 INR
            raise ValueError("Minimum amount is 1 INR")

        try:
            order_data = {
                "amount": amount_paise,
                "currency": currency,
                "receipt": f"deposit_{user.id}_{timezone.now().timestamp()}",
                "notes": {
                    "user_id": str(user.id),
                    "username": user.username,
                    "type": "deposit",
                },
            }
            razorpay_order = client.order.create(data=order_data)
            order_id = razorpay_order["id"]

            razorpay_order_obj = RazorpayOrder.objects.create(
                user=user,
                razorpay_order_id=order_id,
                amount=amount_decimal,
                currency=currency,
                status="created",
                metadata={"razorpay_response": razorpay_order},
            )
            logger.info(
                f"Created Razorpay order {order_id} for user {user.id}, amount: {amount} {currency}"
            )
            return razorpay_order_obj
        except Exception as e:
            logger.error(f"Razorpay create order error: {e}")
            raise

    @staticmethod
    def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verify that the payment was successful using Razorpay signature.
        Returns True if signature is valid.
        """
        client = _get_client()
        if not client:
            raise ValueError("Razorpay is not configured")

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
            return True
        except Exception as e:
            logger.warning(f"Razorpay signature verification failed: {e}")
            return False

    @staticmethod
    def handle_payment_success(razorpay_order_id, razorpay_payment_id=None):
        """
        Credit user wallet and create transaction for successful Razorpay payment.
        Idempotent: if order already processed, returns existing state.
        """
        try:
            razorpay_order = RazorpayOrder.objects.get(
                razorpay_order_id=razorpay_order_id
            )
        except RazorpayOrder.DoesNotExist:
            logger.error(f"Razorpay order not found: {razorpay_order_id}")
            raise ValueError("Razorpay order not found")

        if razorpay_order.transaction and razorpay_order.transaction.status == "COMPLETED":
            logger.warning(f"Razorpay order {razorpay_order_id} already processed")
            return razorpay_order

        user = razorpay_order.user
        amount = razorpay_order.amount

        # Credit user wallet
        user.add_balance(amount)

        # Create transaction
        transaction = Transaction.objects.create(
            user=user,
            type="DEPOSIT",
            amount=amount,
            status="COMPLETED",
            description=f"Deposit via Razorpay (UPI/Card/Netbanking) - Order {razorpay_order_id}",
            reference_id=razorpay_order_id,
        )

        razorpay_order.transaction = transaction
        razorpay_order.status = "paid"
        razorpay_order.completed_at = timezone.now()
        razorpay_order.metadata = {
            **razorpay_order.metadata,
            "razorpay_payment_id": razorpay_payment_id,
        }
        razorpay_order.save()

        # Referral deposit tracking
        try:
            from apps.referrals.services import ReferralService
            ReferralService.update_referral_deposit(user, amount)
        except Exception as e:
            logger.warning(f"Error updating referral deposit: {e}")

        # Optional: deposit confirmation email
        try:
            from apps.notifications.tasks import send_deposit_confirmation_email
            send_deposit_confirmation_email.delay(str(user.id), str(transaction.id))
        except Exception as e:
            logger.warning(f"Error sending deposit confirmation email: {e}")

        logger.info(
            f"Processed successful Razorpay payment {razorpay_order_id} for user {user.id}"
        )
        return razorpay_order
