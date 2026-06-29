from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from apps.payments.models import StripeCustomer, PaymentIntent
from apps.payments.services import StripeService
from apps.transactions.models import Transaction
import uuid

User = get_user_model()


class StripeServiceTestCase(TestCase):
    """Test StripeService methods"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    @patch('apps.payments.services.stripe.Customer.create')
    def test_create_customer(self, mock_create):
        """Test creating a Stripe customer"""
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_create.return_value = mock_customer

        stripe_customer = StripeService.create_customer(self.user)

        self.assertIsNotNone(stripe_customer)
        self.assertEqual(stripe_customer.stripe_customer_id, 'cus_test123')
        self.assertEqual(stripe_customer.user, self.user)

    @patch('apps.payments.services.stripe.PaymentIntent.create')
    @patch('apps.payments.services.StripeService.create_customer')
    def test_create_payment_intent(self, mock_create_customer, mock_create_intent):
        """Test creating a payment intent"""
        mock_customer = MagicMock()
        mock_customer.stripe_customer_id = 'cus_test123'
        mock_create_customer.return_value = mock_customer

        mock_intent = MagicMock()
        mock_intent.id = 'pi_test123'
        mock_intent.status = 'requires_payment_method'
        mock_intent.client_secret = 'secret_test123'
        mock_create_intent.return_value = mock_intent

        payment_intent = StripeService.create_payment_intent(
            amount=100.00,
            user=self.user
        )

        self.assertIsNotNone(payment_intent)
        self.assertEqual(payment_intent.stripe_payment_intent_id, 'pi_test123')
        self.assertEqual(payment_intent.amount, 100.00)

    @patch('apps.payments.services.stripe.PaymentIntent.confirm')
    def test_confirm_payment_intent(self, mock_confirm):
        """Test confirming a payment intent"""
        payment_intent = PaymentIntent.objects.create(
            user=self.user,
            stripe_payment_intent_id='pi_test123',
            amount=100.00,
            status='requires_confirmation',
            client_secret='secret_test123'
        )

        mock_intent = MagicMock()
        mock_intent.status = 'succeeded'
        mock_intent.client_secret = 'secret_test123'
        mock_confirm.return_value = mock_intent

        result = StripeService.confirm_payment_intent('pi_test123')

        self.assertEqual(result.status, 'succeeded')

    @patch('apps.payments.services.stripe.PaymentMethod.attach')
    @patch('apps.payments.services.StripeService.create_customer')
    def test_save_payment_method(self, mock_create_customer, mock_attach):
        """Test saving a payment method"""
        mock_customer = MagicMock()
        mock_customer.stripe_customer_id = 'cus_test123'
        mock_create_customer.return_value = mock_customer

        mock_payment_method = MagicMock()
        mock_payment_method.id = 'pm_test123'
        mock_payment_method.type = 'card'
        mock_payment_method.card = MagicMock()
        mock_payment_method.card.last4 = '4242'
        mock_payment_method.card.brand = 'visa'
        mock_attach.return_value = mock_payment_method

        result = StripeService.save_payment_method(
            user=self.user,
            payment_method_id='pm_test123',
            set_as_primary=True
        )

        self.assertIsNotNone(result)


class PaymentIntentViewSetTestCase(TestCase):
    """Test PaymentIntentViewSet endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )
        self.client.force_authenticate(user=self.user)

    @patch('apps.payments.services.StripeService.create_payment_intent')
    @patch('apps.users.responsible_gaming.ResponsibleGamingService.check_self_exclusion')
    @patch('apps.users.responsible_gaming.ResponsibleGamingService.check_deposit_limit')
    def test_create_payment_intent(self, mock_deposit_limit, mock_self_exclusion, mock_create):
        """Test creating a payment intent via API"""
        mock_self_exclusion.return_value = (False, None)
        mock_deposit_limit.return_value = (True, None)
        
        mock_payment_intent = PaymentIntent(
            id=uuid.uuid4(),
            user=self.user,
            stripe_payment_intent_id='pi_test123',
            amount=100.00,
            status='requires_payment_method',
            client_secret='secret_test123'
        )
        mock_create.return_value = mock_payment_intent

        response = self.client.post('/api/payments/create-intent/', {
            'amount': 100.00
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('client_secret', response.data)


class PaymentWebhookTestCase(TestCase):
    """Test Stripe webhook handling"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    @patch('apps.payments.webhooks.stripe.Webhook.construct_event')
    @patch('apps.payments.services.StripeService.handle_payment_success')
    def test_payment_intent_succeeded_webhook(self, mock_handle, mock_construct):
        """Test handling payment_intent.succeeded webhook"""
        payment_intent = PaymentIntent.objects.create(
            user=self.user,
            stripe_payment_intent_id='pi_test123',
            amount=100.00,
            status='processing'
        )

        mock_handle.return_value = payment_intent

        event_data = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_test123',
                    'amount': 10000,
                    'status': 'succeeded'
                }
            }
        }
        mock_construct.return_value = event_data

        from apps.payments.webhooks import handle_payment_intent_succeeded
        handle_payment_intent_succeeded(event_data['data']['object'])

        mock_handle.assert_called_once_with('pi_test123')

