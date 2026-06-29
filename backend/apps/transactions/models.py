from django.db import models
from apps.users.models import User
from apps.lotteries.models import Lottery
import uuid

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('TICKET_PURCHASE', 'Ticket Purchase'),
        ('PRIZE_AWARD', 'Prize Award'),
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('REFUND', 'Refund'),
        ('ADMIN_ADJUSTMENT', 'Admin Adjustment'),
        ('REFERRAL_BONUS', 'Referral Bonus'),
        ('SLOTS_BET', 'Slots Bet'),
        ('SLOTS_WIN', 'Slots Win'),
        ('GAME_ENTRY', 'Game Entry'),
        ('GAME_WIN', 'Game Win'),
        ('GAME_REFUND', 'Game Refund'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    lottery = models.ForeignKey(
        Lottery,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    game_room = models.ForeignKey(
        'games.GameRoom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    description = models.TextField(blank=True)
    reference_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['type', '-created_at']),
        models.Index(fields=['status']),
        models.Index(fields=['lottery']),
        models.Index(fields=['game_room']),
    ]

    def __str__(self):
        return f"{self.type} - {self.user.username} - {self.amount} ({self.status})"

    def mark_completed(self):
        from django.utils import timezone
        if self.status == 'PENDING':
            self.status = 'COMPLETED'
            self.completed_at = timezone.now()
            self.save()
            return True
        return False

    def mark_failed(self):
        if self.status == 'PENDING':
            self.status = 'FAILED'
            self.save()
            return True
        return False


class PaymentMethod(models.Model):
    METHOD_CHOICES = [
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('NET_BANKING', 'Net Banking'),
        ('DIGITAL_WALLET', 'Digital Wallet'),
        ('UPI', 'UPI'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=50, choices=METHOD_CHOICES)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    payment_details = models.JSONField(default=dict)  # Encrypted in production
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_methods'
        unique_together = ['user', 'method_type']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.method_type}"


class WithdrawalRequest(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawal_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')
    bank_details = models.JSONField(default=dict)  # For bank transfers
    remarks = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='withdrawal_request'
    )

    class Meta:
        db_table = 'withdrawal_requests'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Withdrawal - {self.user.username} - {self.amount} ({self.status})"
