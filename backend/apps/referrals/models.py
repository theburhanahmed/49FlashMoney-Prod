from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class ReferralProgram(models.Model):
    """
    Global referral program configuration.
    Only one instance should exist - managed by admin.
    """
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('PAUSED', 'Paused'),
    )

    # Program control
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        help_text='Enable/disable the entire referral program'
    )
    
    # Bonus configuration
    referral_bonus_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00,
        validators=[MinValueValidator(0)],
        help_text='Bonus amount credited to referrer when new user registers'
    )
    
    referred_user_bonus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=25.00,
        validators=[MinValueValidator(0)],
        help_text='Bonus amount credited to newly referred user'
    )
    
    # Requirements
    minimum_referral_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text='Minimum deposit required by referred user to qualify for bonus'
    )
    
    bonus_expiry_days = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text='Days before unclaimed bonus expires'
    )
    
    # Withdrawal control
    min_referral_balance_to_withdraw = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100.00,
        validators=[MinValueValidator(0)],
        help_text='Minimum referral bonus balance required to initiate withdrawal'
    )
    
    max_withdrawals_per_month = models.PositiveIntegerField(
        default=12,
        validators=[MinValueValidator(1)],
        help_text='Maximum number of referral bonus withdrawals per user per month'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Referral Program'
        verbose_name_plural = 'Referral Program'

    def __str__(self):
        return f'Referral Program ({self.get_status_display()})'

    @staticmethod
    def get_program():
        """Get or create the global referral program."""
        program, _ = ReferralProgram.objects.get_or_create(
            id=1,
            defaults={'status': 'ACTIVE'}
        )
        return program


class ReferralLink(models.Model):
    """
    Unique referral link for each user.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_link'
    )
    
    # Unique code for referral URL
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text='Unique code for referral link'
    )
    
    # Tracking
    total_referred = models.PositiveIntegerField(
        default=0,
        help_text='Total number of successful referrals'
    )
    
    total_bonus_earned = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        help_text='Total bonus earned from all referrals'
    )
    
    total_referrals_clicked = models.PositiveIntegerField(
        default=0,
        help_text='Total number of clicks on referral link'
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Referral Link'
        verbose_name_plural = 'Referral Links'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['referral_code']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.referral_code}'


class Referral(models.Model):
    """
    Individual referral record.
    Tracks when a user refers another user.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),      # User registered but hasn't met requirements
        ('QUALIFIED', 'Qualified'),   # User met all requirements
        ('BONUS_AWARDED', 'Bonus Awarded'),  # Bonus was credited
        ('REJECTED', 'Rejected'),     # Referral rejected by admin
        ('CANCELLED', 'Cancelled'),   # User cancelled referral
    )

    # Relationships
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referrals_made',
        help_text='User who made the referral'
    )
    
    referred_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referred_by',
        help_text='User who was referred'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text='Current status of the referral'
    )
    
    # Bonus tracking
    referrer_bonus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Bonus amount for referrer'
    )
    
    referred_user_bonus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Bonus amount for referred user'
    )
    
    bonus_awarded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When bonus was awarded'
    )
    
    # Requirements tracking
    referred_user_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Total deposit amount by referred user'
    )
    
    deposit_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date when deposit requirement was met'
    )
    
    # Admin notes
    rejection_reason = models.TextField(
        blank=True,
        help_text='Reason for rejection if status is REJECTED'
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        help_text='When the referral bonus expires if not qualified'
    )

    class Meta:
        verbose_name = 'Referral'
        verbose_name_plural = 'Referrals'
        indexes = [
            models.Index(fields=['referrer', 'status']),
            models.Index(fields=['referred_user', 'status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.referrer.username} referred {self.referred_user.username}'

    def save(self, *args, **kwargs):
        """Set expiry date on creation."""
        if not self.pk:
            program = ReferralProgram.get_program()
            self.expires_at = timezone.now() + timezone.timedelta(
                days=program.bonus_expiry_days
            )
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if referral bonus has expired."""
        return timezone.now() > self.expires_at and self.status == 'PENDING'


class ReferralBonus(models.Model):
    """
    Track individual bonus credits from referrals.
    """
    TYPE_CHOICES = (
        ('REFERRER', 'Referrer Bonus'),
        ('REFERRED', 'Referred User Bonus'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_bonuses',
        help_text='User who received the bonus'
    )
    
    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name='bonuses',
        help_text='Referral that triggered this bonus'
    )
    
    bonus_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        help_text='Type of bonus'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Bonus amount'
    )
    
    status = models.CharField(
        max_length=20,
        default='PENDING',
        choices=[
            ('PENDING', 'Pending'),
            ('CREDITED', 'Credited'),
            ('EXPIRED', 'Expired'),
            ('WITHDRAWN', 'Withdrawn'),
        ],
        help_text='Bonus status'
    )
    
    credited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When bonus was credited to wallet'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Referral Bonus'
        verbose_name_plural = 'Referral Bonuses'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.bonus_type} - {self.amount}'


class ReferralWithdrawal(models.Model):
    """
    Track withdrawals of referral bonus funds.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_withdrawals',
        help_text='User requesting withdrawal'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text='Amount to withdraw'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text='Withdrawal status'
    )
    
    # Payment info
    payment_method = models.CharField(
        max_length=100,
        blank=True,
        help_text='Payment method (bank, wallet, etc.)'
    )
    
    # Admin notes
    admin_notes = models.TextField(
        blank=True,
        help_text='Notes from admin'
    )
    
    rejection_reason = models.TextField(
        blank=True,
        help_text='Reason for rejection if status is REJECTED'
    )
    
    # Tracking
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_referral_withdrawals',
        help_text='Admin who processed this withdrawal'
    )
    
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When withdrawal was processed'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Referral Withdrawal'
        verbose_name_plural = 'Referral Withdrawals'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.amount} - {self.get_status_display()}'
