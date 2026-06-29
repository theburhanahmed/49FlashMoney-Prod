from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.notifications.models import Notification
from apps.notifications.services import EmailService
from unittest.mock import patch, MagicMock

User = get_user_model()


class NotificationModelTestCase(TestCase):
    """Test Notification model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    def test_create_notification(self):
        """Test creating a notification"""
        notification = Notification.objects.create(
            user=self.user,
            type='SYSTEM',
            title='Test Notification',
            message='This is a test notification',
            action_url='/dashboard'
        )

        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.type, 'SYSTEM')
        self.assertFalse(notification.is_read)

    def test_mark_as_read(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            user=self.user,
            type='SYSTEM',
            title='Test Notification',
            message='This is a test notification'
        )

        notification.mark_as_read()

        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)


class EmailServiceTestCase(TestCase):
    """Test EmailService"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    @patch('apps.notifications.services.EmailMultiAlternatives.send')
    def test_send_welcome_email(self, mock_send):
        """Test sending welcome email"""
        result = EmailService.send_welcome_email(self.user)
        self.assertTrue(result)
        mock_send.assert_called_once()

    @patch('apps.notifications.services.EmailMultiAlternatives.send')
    def test_send_email_verification(self, mock_send):
        """Test sending email verification"""
        result = EmailService.send_email_verification(self.user)
        self.assertTrue(result)
        mock_send.assert_called_once()

    @patch('apps.notifications.services.EmailMultiAlternatives.send')
    def test_send_password_reset(self, mock_send):
        """Test sending password reset email"""
        token = 'test_token_123'
        result = EmailService.send_password_reset(self.user, token)
        self.assertTrue(result)
        mock_send.assert_called_once()

    @patch('apps.notifications.services.EmailMultiAlternatives.send')
    def test_send_deposit_confirmation(self, mock_send):
        """Test sending deposit confirmation email"""
        from apps.transactions.models import Transaction
        from decimal import Decimal
        
        transaction = Transaction.objects.create(
            user=self.user,
            type='DEPOSIT',
            amount=Decimal('100.00'),
            status='COMPLETED'
        )
        
        result = EmailService.send_deposit_confirmation(self.user, transaction)
        self.assertTrue(result)
        mock_send.assert_called_once()


class NotificationViewSetTestCase(TestCase):
    """Test NotificationViewSet endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )
        self.client.force_authenticate(user=self.user)

    def test_list_notifications(self):
        """Test listing notifications"""
        Notification.objects.create(
            user=self.user,
            type='SYSTEM',
            title='Test Notification',
            message='Test message'
        )

        response = self.client.get('/api/notifications/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_mark_notification_as_read(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            user=self.user,
            type='SYSTEM',
            title='Test Notification',
            message='Test message'
        )

        response = self.client.post(f'/api/notifications/{notification.id}/mark_read/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

