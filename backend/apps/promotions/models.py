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
