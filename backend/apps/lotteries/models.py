from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from apps.users.models import User
from apps.common.constants import TIMEZONE_CHOICES, DEFAULT_MAX_TICKETS_PER_USER, DEFAULT_LOTTERY_TIMEZONE
import uuid
import random

class Lottery(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('DRAWN', 'Drawn'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_tickets = models.IntegerField()
    available_tickets = models.IntegerField()
    prize_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    draw_date = models.DateTimeField()
    start_date = models.DateTimeField(null=True, blank=True, help_text='When ticket sales start')
    end_date = models.DateTimeField(null=True, blank=True, help_text='When ticket sales end')
    timezone = models.CharField(
        max_length=50,
        choices=TIMEZONE_CHOICES,
        default=DEFAULT_LOTTERY_TIMEZONE,
        help_text='Timezone for lottery dates'
    )
    max_tickets_per_user = models.PositiveIntegerField(
        default=DEFAULT_MAX_TICKETS_PER_USER,
        validators=[MinValueValidator(1)],
        help_text='Maximum tickets a single user can purchase'
    )
    auto_draw = models.BooleanField(
        default=False,
        help_text='Automatically conduct draw when end_date is reached'
    )
    featured = models.BooleanField(
        default=False,
        help_text='Feature this lottery on homepage'
    )
    image = models.ImageField(
        upload_to='lotteries/',
        null=True,
        blank=True,
        help_text='Cover image for the lottery'
    )
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_lotteries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lotteries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['draw_date']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', 'draw_date']),  # Composite index for common queries
            models.Index(fields=['featured', '-created_at']),  # For featured lotteries
        ]

    def __str__(self):
        return f"{self.name} - {self.status}"

    def is_active(self):
        return self.status == 'ACTIVE' and self.available_tickets > 0

    def can_draw(self):
        return self.draw_date <= timezone.now() and self.status == 'CLOSED'

    def get_total_participants(self):
        return self.ticket_set.values('user').distinct().count()

    def get_total_tickets_sold(self):
        return self.total_tickets - self.available_tickets

    def get_revenue(self):
        return self.get_total_tickets_sold() * self.ticket_price

    def is_within_sale_period(self):
        """Check if current time is within ticket sale period."""
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True

    def get_user_ticket_count(self, user):
        """Get number of tickets purchased by a user for this lottery."""
        return self.ticket_set.filter(user=user).count()


class LotteryTemplate(models.Model):
    """Template for creating lotteries with predefined settings."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text='Template name')
    description = models.TextField(blank=True)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_tickets = models.IntegerField()
    prize_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_tickets_per_user = models.PositiveIntegerField(
        default=DEFAULT_MAX_TICKETS_PER_USER,
        validators=[MinValueValidator(1)]
    )
    timezone = models.CharField(
        max_length=50,
        choices=TIMEZONE_CHOICES,
        default=DEFAULT_LOTTERY_TIMEZONE
    )
    auto_draw = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, help_text='Whether template is available for use')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lottery_templates'
        ordering = ['-created_at']

    def __str__(self):
        return f"Template: {self.name}"


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    lottery = models.ForeignKey(Lottery, on_delete=models.CASCADE, related_name='ticket_set')
    ticket_number = models.IntegerField()
    is_winner = models.BooleanField(default=False)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tickets'
        unique_together = ['lottery', 'ticket_number']
        ordering = ['-purchased_at']
        indexes = [
            models.Index(fields=['user', 'lottery']),
            models.Index(fields=['lottery', 'is_winner']),
            models.Index(fields=['-purchased_at']),
        ]

    def __str__(self):
        return f"Ticket #{self.ticket_number} - {self.lottery.name}"


class Winner(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wins')
    lottery = models.ForeignKey(Lottery, on_delete=models.CASCADE, related_name='winners')
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='winner')
    prize_amount = models.DecimalField(max_digits=10, decimal_places=2)
    announced_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    is_claimed = models.BooleanField(default=False)

    class Meta:
        db_table = 'winners'
        ordering = ['-announced_at']
        indexes = [
            models.Index(fields=['user', '-announced_at']),
            models.Index(fields=['lottery']),
            models.Index(fields=['is_claimed']),
        ]

    def __str__(self):
        return f"{self.user.username} won {self.prize_amount} in {self.lottery.name}"

    def claim_prize(self):
        if not self.is_claimed:
            self.user.add_balance(self.prize_amount)
            self.is_claimed = True
            self.claimed_at = timezone.now()
            self.save()
            return True
        return False


class LotteryDrawLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lottery = models.OneToOneField(Lottery, on_delete=models.CASCADE, related_name='draw_log')
    conducted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    total_participants = models.IntegerField()
    total_tickets_sold = models.IntegerField()
    revenue = models.DecimalField(max_digits=10, decimal_places=2)
    random_seed = models.CharField(max_length=255)
    drawn_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lottery_draw_logs'
        ordering = ['-drawn_at']

    def __str__(self):
        return f"Draw Log - {self.lottery.name} - {self.drawn_at}"
