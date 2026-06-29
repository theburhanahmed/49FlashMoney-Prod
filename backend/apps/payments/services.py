import stripe
from django.conf import settings
from django.utils import timezone
from apps.payments.models import StripeCustomer, PaymentIntent
from apps.transactions.models import Transaction
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service class for Stripe operations"""

    @staticmethod
    def create_customer(user):
        """
        Create or retrieve Stripe customer for a user
        Returns StripeCustomer instance
        """
        try:
            # Check if customer already exists
            stripe_customer_obj = StripeCustomer.objects.filter(user=user).first()
            if stripe_customer_obj:
                return stripe_customer_obj

            # Create customer in Stripe
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.username,
                metadata={
                    'user_id': str(user.id),
                    'username': user.username
                }
            )

            # Save to database
            stripe_customer_obj = StripeCustomer.objects.create(
                user=user,
                stripe_customer_id=customer.id
            )

            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return stripe_customer_obj

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating Stripe customer: {e}")
            raise

    @staticmethod
    def create_payment_intent(amount, user, payment_method_id=None, save_payment_method=False):
        """
        Create a payment intent for deposit
        Returns PaymentIntent instance
        """
        try:
            # Get or create Stripe customer
            stripe_customer = StripeService.create_customer(user)
            customer_id = stripe_customer.stripe_customer_id

            # Create payment intent parameters
            intent_params = {
                'amount': int(amount * 100),  # Convert to cents
                'currency': settings.STRIPE_CURRENCY.lower(),
                'customer': customer_id,
                'metadata': {
                    'user_id': str(user.id),
                    'username': user.username,
                    'type': 'deposit'
                }
            }

            # Add payment method if provided
            if payment_method_id:
                intent_params['payment_method'] = payment_method_id
                intent_params['confirmation_method'] = 'manual'
                intent_params['confirm'] = False

            # Create payment intent in Stripe
            intent = stripe.PaymentIntent.create(**intent_params)

            # Save payment method if requested
            if save_payment_method and payment_method_id:
                try:
                    stripe.PaymentMethod.attach(
                        payment_method_id,
                        customer=customer_id
                    )
                    # Set as default if it's the first payment method
                    payment_methods = stripe.PaymentMethod.list(
                        customer=customer_id,
                        type='card'
                    )
                    if len(payment_methods.data) == 1:
                        stripe.Customer.modify(
                            customer_id,
                            invoice_settings={'default_payment_method': payment_method_id}
                        )
                except stripe.error.StripeError as e:
                    logger.warning(f"Could not save payment method: {e}")

            # Create PaymentIntent record
            payment_intent = PaymentIntent.objects.create(
                user=user,
                stripe_payment_intent_id=intent.id,
                amount=amount,
                currency=settings.STRIPE_CURRENCY.lower(),
                status=intent.status,
                client_secret=intent.client_secret
            )

            logger.info(f"Created payment intent {intent.id} for user {user.id}, amount: {amount}")
            return payment_intent

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating payment intent: {e}")
            raise

    @staticmethod
    def confirm_payment_intent(payment_intent_id, payment_method_id=None):
        """
        Confirm a payment intent
        Returns updated PaymentIntent instance
        """
        try:
            payment_intent = PaymentIntent.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )

            # Confirm payment intent in Stripe
            confirm_params = {}
            if payment_method_id:
                confirm_params['payment_method'] = payment_method_id

            intent = stripe.PaymentIntent.confirm(
                payment_intent_id,
                **confirm_params
            )

            # Update payment intent status
            payment_intent.status = intent.status
            payment_intent.client_secret = intent.client_secret
            payment_intent.save()

            logger.info(f"Confirmed payment intent {payment_intent_id}, status: {intent.status}")
            return payment_intent

        except PaymentIntent.DoesNotExist:
            logger.error(f"Payment intent not found: {payment_intent_id}")
            raise ValueError("Payment intent not found")
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment intent: {e}")
            raise
        except Exception as e:
            logger.error(f"Error confirming payment intent: {e}")
            raise

    @staticmethod
    def save_payment_method(user, payment_method_id, set_as_primary=False):
        """
        Save a payment method to customer
        Returns payment method object
        """
        try:
            stripe_customer = StripeService.create_customer(user)
            customer_id = stripe_customer.stripe_customer_id

            # Attach payment method to customer
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )

            # Set as primary if requested
            if set_as_primary:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={'default_payment_method': payment_method_id}
                )

            # Update PaymentMethod model if it exists
            from apps.transactions.models import PaymentMethod
            payment_method_obj = PaymentMethod.objects.filter(
                user=user,
                payment_details__stripe_payment_method_id=payment_method_id
            ).first()

            if not payment_method_obj:
                # Determine method type from payment method
                method_type = 'CREDIT_CARD'  # Default
                if payment_method.type == 'card':
                    method_type = 'CREDIT_CARD' if payment_method.card.brand in ['visa', 'mastercard', 'amex'] else 'DEBIT_CARD'

                payment_method_obj = PaymentMethod.objects.create(
                    user=user,
                    method_type=method_type,
                    is_primary=set_as_primary,
                    payment_details={
                        'stripe_payment_method_id': payment_method_id,
                        'last4': payment_method.card.last4 if payment_method.type == 'card' else None,
                        'brand': payment_method.card.brand if payment_method.type == 'card' else None,
                        'type': payment_method.type
                    }
                )

                # If this is the first payment method or set as primary, update others
                if set_as_primary:
                    PaymentMethod.objects.filter(user=user).exclude(id=payment_method_obj.id).update(is_primary=False)

            logger.info(f"Saved payment method {payment_method_id} for user {user.id}")
            return payment_method

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error saving payment method: {e}")
            raise
        except Exception as e:
            logger.error(f"Error saving payment method: {e}")
            raise

    @staticmethod
    def list_payment_methods(user):
        """
        List saved payment methods for a user
        Returns list of payment methods
        """
        try:
            stripe_customer = StripeCustomer.objects.filter(user=user).first()
            if not stripe_customer:
                return []

            payment_methods = stripe.PaymentMethod.list(
                customer=stripe_customer.stripe_customer_id,
                type='card'
            )

            return payment_methods.data

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error listing payment methods: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing payment methods: {e}")
            raise

    @staticmethod
    def delete_payment_method(payment_method_id):
        """
        Delete a payment method
        """
        try:
            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
            stripe.PaymentMethod.detach(payment_method_id)

            # Also delete from PaymentMethod model
            from apps.transactions.models import PaymentMethod
            PaymentMethod.objects.filter(
                payment_details__stripe_payment_method_id=payment_method_id
            ).delete()

            logger.info(f"Deleted payment method {payment_method_id}")
            return True

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error deleting payment method: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deleting payment method: {e}")
            raise

    @staticmethod
    def handle_payment_success(payment_intent_id):
        """
        Handle successful payment - credit user wallet and create transaction
        """
        try:
            payment_intent = PaymentIntent.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )

            # Check if already processed
            if payment_intent.transaction and payment_intent.transaction.status == 'COMPLETED':
                logger.warning(f"Payment intent {payment_intent_id} already processed")
                return payment_intent

            user = payment_intent.user

            # Credit user wallet
            user.add_balance(payment_intent.amount)

            # Create transaction
            transaction = Transaction.objects.create(
                user=user,
                type='DEPOSIT',
                amount=payment_intent.amount,
                status='COMPLETED',
                description=f'Deposit via Stripe - Payment Intent {payment_intent_id}',
                reference_id=payment_intent_id
            )

            # Link transaction to payment intent
            payment_intent.transaction = transaction
            payment_intent.status = 'succeeded'
            payment_intent.completed_at = timezone.now()
            payment_intent.save()

            # Track referral deposit if user was referred
            try:
                from apps.referrals.services import ReferralService
                ReferralService.update_referral_deposit(user, payment_intent.amount)
            except Exception as e:
                logger.warning(f"Error updating referral deposit: {e}")

            # Send deposit confirmation email
            try:
                from apps.notifications.tasks import send_deposit_confirmation_email
                send_deposit_confirmation_email.delay(str(user.id), str(transaction.id))
            except Exception as e:
                logger.warning(f"Error sending deposit confirmation email: {e}")

            logger.info(f"Processed successful payment {payment_intent_id} for user {user.id}")
            return payment_intent

        except PaymentIntent.DoesNotExist:
            logger.error(f"Payment intent not found: {payment_intent_id}")
            raise ValueError("Payment intent not found")
        except Exception as e:
            logger.error(f"Error handling payment success: {e}")
            raise

    @staticmethod
    def handle_payment_failure(payment_intent_id):
        """
        Handle failed payment - log error and notify
        """
        try:
            payment_intent = PaymentIntent.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )

            payment_intent.status = 'canceled'
            payment_intent.save()

            if payment_intent.transaction:
                payment_intent.transaction.status = 'FAILED'
                payment_intent.transaction.save()

            logger.warning(f"Payment failed for payment intent {payment_intent_id}")
            return payment_intent

        except PaymentIntent.DoesNotExist:
            logger.error(f"Payment intent not found: {payment_intent_id}")
            raise ValueError("Payment intent not found")
        except Exception as e:
            logger.error(f"Error handling payment failure: {e}")
            raise

