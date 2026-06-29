from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.referrals.models import ReferralProgram, ReferralLink, Referral, ReferralBonus
from decimal import Decimal
import uuid

User = get_user_model()


class ReferralProgramTestCase(TestCase):
    """Test ReferralProgram model"""

    def setUp(self):
        self.program = ReferralProgram.objects.create(
            is_active=True,
            bonus_amount=Decimal('10.00'),
            minimum_deposit=Decimal('50.00'),
            expiry_days=30
        )

    def test_create_referral_program(self):
        """Test creating a referral program"""
        self.assertTrue(self.program.is_active)
        self.assertEqual(self.program.bonus_amount, Decimal('10.00'))


class ReferralLinkTestCase(TestCase):
    """Test ReferralLink model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='referrer',
            email='referrer@example.com',
            password='Password123'
        )

    def test_create_referral_link(self):
        """Test creating a referral link"""
        link = ReferralLink.objects.create(
            user=self.user,
            referral_code='TESTCODE123'
        )

        self.assertEqual(link.user, self.user)
        self.assertEqual(link.referral_code, 'TESTCODE123')
        self.assertIsNotNone(link.referral_url)


class ReferralTestCase(TestCase):
    """Test Referral model"""

    def setUp(self):
        self.referrer = User.objects.create_user(
            username='referrer',
            email='referrer@example.com',
            password='Password123'
        )
        self.referred_user = User.objects.create_user(
            username='referred',
            email='referred@example.com',
            password='Password123'
        )
        self.referral_link = ReferralLink.objects.create(
            user=self.referrer,
            referral_code='TESTCODE123'
        )

    def test_create_referral(self):
        """Test creating a referral"""
        referral = Referral.objects.create(
            referrer=self.referrer,
            referred_user=self.referred_user,
            referral_link=self.referral_link,
            status='PENDING'
        )

        self.assertEqual(referral.referrer, self.referrer)
        self.assertEqual(referral.referred_user, self.referred_user)
        self.assertEqual(referral.status, 'PENDING')


class ReferralBonusTestCase(TestCase):
    """Test ReferralBonus model"""

    def setUp(self):
        self.referrer = User.objects.create_user(
            username='referrer',
            email='referrer@example.com',
            password='Password123'
        )
        self.referred_user = User.objects.create_user(
            username='referred',
            email='referred@example.com',
            password='Password123'
        )
        self.referral = Referral.objects.create(
            referrer=self.referrer,
            referred_user=self.referred_user,
            status='APPROVED'
        )

    def test_create_referral_bonus(self):
        """Test creating a referral bonus"""
        bonus = ReferralBonus.objects.create(
            referral=self.referral,
            amount=Decimal('10.00'),
            status='PENDING'
        )

        self.assertEqual(bonus.referral, self.referral)
        self.assertEqual(bonus.amount, Decimal('10.00'))
        self.assertEqual(bonus.status, 'PENDING')


class ReferralViewSetTestCase(TestCase):
    """Test ReferralViewSet endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123'
        )
        self.client.force_authenticate(user=self.user)

    def test_get_referral_link(self):
        """Test getting referral link"""
        ReferralLink.objects.create(
            user=self.user,
            referral_code='TESTCODE123'
        )

        response = self.client.get('/api/referrals/link/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('referral_code', response.data)

    def test_get_referral_stats(self):
        """Test getting referral statistics"""
        response = self.client.get('/api/referrals/stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_referred', response.data)

