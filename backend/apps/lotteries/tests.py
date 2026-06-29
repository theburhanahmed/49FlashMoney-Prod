from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.lotteries.models import Lottery, Ticket, Winner
from apps.transactions.models import Transaction
from decimal import Decimal
import uuid

User = get_user_model()


class LotteryModelTestCase(TestCase):
    """Test Lottery model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )

    def test_create_lottery(self):
        """Test creating a lottery"""
        lottery = Lottery.objects.create(
            name='Test Lottery',
            description='Test Description',
            ticket_price=Decimal('10.00'),
            total_tickets=100,
            available_tickets=100,
            prize_amount=Decimal('500.00'),
            status='ACTIVE'
        )

        self.assertEqual(lottery.name, 'Test Lottery')
        self.assertEqual(lottery.status, 'ACTIVE')
        self.assertEqual(lottery.available_tickets, 100)


class TicketPurchaseTestCase(TestCase):
    """Test ticket purchase flow"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123',
            wallet_balance=Decimal('100.00')
        )
        self.lottery = Lottery.objects.create(
            name='Test Lottery',
            description='Test Description',
            ticket_price=Decimal('10.00'),
            total_tickets=100,
            available_tickets=100,
            prize_amount=Decimal('500.00'),
            status='ACTIVE'
        )
        self.client.force_authenticate(user=self.user)

    def test_purchase_ticket_success(self):
        """Test successful ticket purchase"""
        response = self.client.post(f'/api/lotteries/{self.lottery.id}/buy_ticket/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('ticket', response.data)

        # Check ticket was created
        ticket = Ticket.objects.filter(user=self.user, lottery=self.lottery).first()
        self.assertIsNotNone(ticket)

        # Check wallet balance was deducted
        self.user.refresh_from_db()
        self.assertEqual(self.user.wallet_balance, Decimal('90.00'))

        # Check transaction was created
        transaction = Transaction.objects.filter(
            user=self.user,
            type='TICKET_PURCHASE',
            lottery=self.lottery
        ).first()
        self.assertIsNotNone(transaction)

    def test_purchase_ticket_insufficient_balance(self):
        """Test ticket purchase with insufficient balance"""
        self.user.wallet_balance = Decimal('5.00')
        self.user.save()

        response = self.client.post(f'/api/lotteries/{self.lottery.id}/buy_ticket/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class DrawExecutionTestCase(TestCase):
    """Test lottery draw execution"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='Password123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='Password123'
        )
        self.lottery = Lottery.objects.create(
            name='Test Lottery',
            description='Test Description',
            ticket_price=Decimal('10.00'),
            total_tickets=100,
            available_tickets=2,
            prize_amount=Decimal('500.00'),
            status='ACTIVE'
        )

    def test_draw_execution(self):
        """Test executing a lottery draw"""
        # Create tickets
        ticket1 = Ticket.objects.create(
            user=self.user1,
            lottery=self.lottery,
            ticket_number=1
        )
        ticket2 = Ticket.objects.create(
            user=self.user2,
            lottery=self.lottery,
            ticket_number=2
        )

        # Execute draw
        from apps.lotteries.services import LotteryService
        winner = LotteryService.conduct_draw(self.lottery)

        self.assertIsNotNone(winner)
        self.assertIn(winner.user, [self.user1, self.user2])

        # Check lottery status updated
        self.lottery.refresh_from_db()
        self.assertEqual(self.lottery.status, 'COMPLETED')

        # Check winner ticket marked
        winner_ticket = Ticket.objects.get(id=winner.ticket.id)
        self.assertTrue(winner_ticket.is_winner)


class LotteryViewSetTestCase(TestCase):
    """Test LotteryViewSet endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123',
            role='admin'
        )
        self.client.force_authenticate(user=self.user)

    def test_list_lotteries(self):
        """Test listing lotteries"""
        Lottery.objects.create(
            name='Lottery 1',
            ticket_price=Decimal('10.00'),
            total_tickets=100,
            available_tickets=100,
            prize_amount=Decimal('500.00'),
            status='ACTIVE'
        )

        response = self.client.get('/api/lotteries/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_create_lottery(self):
        """Test creating a lottery (admin only)"""
        response = self.client.post('/api/lotteries/', {
            'name': 'New Lottery',
            'description': 'New Description',
            'ticket_price': '10.00',
            'total_tickets': 100,
            'prize_amount': '500.00',
            'status': 'ACTIVE'
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Lottery')

