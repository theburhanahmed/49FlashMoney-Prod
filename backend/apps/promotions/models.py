"""Promotions models - promotional campaigns and bonus offers."""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class Promotion(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]
    TYPE_CHOICES = [
        ('DEPOSIT_BONUS', 'Deposit Bonus'),
        ('FREE_BET', 'Free Bet'),
        ('CASHBACK', 'Cashback'),
        ('REFERRAL', 'Referral'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    promotion_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    max_bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    min_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    wagering_requirement = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.00'))
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    max_claims = models.IntegerField(default=0, help_text='0 = unlimited')
    total_claims = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'promotions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.status})"


class PromotionClaim(models.Model):
    """Records a single user's claim of a promotion and its bonus lifecycle."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CREDITED', 'Credited'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='promotion_claims',
    )
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name='claims',
    )
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    wagering_remaining = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='PENDING'
    )
    claimed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promotion_claims'
        unique_together = ['user', 'promotion']
        ordering = ['-claimed_at']

    def __str__(self):
        return f"Claim({self.user_id}, {self.promotion.name}) bonus={self.bonus_amount}"
