"""VIP tier models."""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class VIPTier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    level = models.IntegerField(unique=True)
    min_wagered = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    cashback_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    withdrawal_limit_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.00'))
    benefits = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vip_tiers'
        ordering = ['level']

    def __str__(self):
        return f"{self.name} (Level {self.level})"


class UserVIPStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vip_status')
    tier = models.ForeignKey(VIPTier, on_delete=models.PROTECT, related_name='members')
    total_wagered = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    promoted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_vip_status'

    def __str__(self):
        return f"{self.user.username} - {self.tier.name}"
