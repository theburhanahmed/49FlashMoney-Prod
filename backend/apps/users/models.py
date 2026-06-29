from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.contrib.auth.models import Group, Permission
import uuid
import secrets
from datetime import datetime, timedelta

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)  # For Django admin access
    role = models.CharField(max_length=20, choices=[
        ('user', 'User'),
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
    ], default='user')
    wallet_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        validators=[MinValueValidator(0)]
    )
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
    password_reset_token = models.CharField(max_length=100, blank=True, null=True)
    password_reset_expires = models.DateTimeField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_user_agent = models.CharField(max_length=255, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    # Two-Factor Authentication fields
    is_2fa_enabled = models.BooleanField(default=False, help_text='Whether 2FA is enabled for this user')
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True, help_text='TOTP secret key')
    two_factor_backup_codes = models.JSONField(default=list, blank=True, help_text='Backup codes for 2FA')
    is_active = models.BooleanField(default=True)
    age_verified = models.BooleanField(default=False)
    age_verified_at = models.DateTimeField(null=True, blank=True)
    # Responsible Gaming fields
    self_excluded = models.BooleanField(default=False)
    self_exclusion_until = models.DateTimeField(null=True, blank=True)
    daily_deposit_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weekly_deposit_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    monthly_deposit_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    daily_loss_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    session_time_limit = models.IntegerField(null=True, blank=True, help_text='Session time limit in minutes')
    last_session_start = models.DateTimeField(null=True, blank=True)
    # KYC fields
    kyc_status = models.CharField(
        max_length=20,
        choices=[
            ('NOT_STARTED', 'Not Started'),
            ('PENDING', 'Pending'),
            ('VERIFIED', 'Verified'),
            ('REJECTED', 'Rejected'),
        ],
        default='NOT_STARTED'
    )
    kyc_submitted_at = models.DateTimeField(null=True, blank=True)
    kyc_verified_at = models.DateTimeField(null=True, blank=True)
    id_document = models.FileField(upload_to='kyc/id/', null=True, blank=True)
    address_proof = models.FileField(upload_to='kyc/address/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['is_admin']),
            models.Index(fields=['wallet_balance']),  # For balance queries
            models.Index(fields=['role', 'is_active']),  # For user filtering
        ]

    def __str__(self):
        return f"{self.username} ({self.email})"

    def add_balance(self, amount):
        """Add funds to user's wallet"""
        if amount > 0:
            self.wallet_balance += amount
            self.save()
            return True
        return False

    def deduct_balance(self, amount):
        """Deduct funds from user's wallet"""
        if 0 < amount <= self.wallet_balance:
            self.wallet_balance -= amount
            self.save()
            return True
        return False

    def generate_verification_token(self):
        """Generate email verification token"""
        token = secrets.token_urlsafe(32)
        self.email_verification_token = token
        self.email_verification_sent_at = datetime.now()
        self.save()
        return token

    def generate_password_reset_token(self):
        """Generate password reset token"""
        token = secrets.token_urlsafe(32)
        self.password_reset_token = token
        self.password_reset_expires = datetime.now() + timedelta(hours=1)
        self.save()
        return token

    def is_account_locked(self):
        """Check if account is locked due to failed login attempts"""
        if self.locked_until and datetime.now() < self.locked_until.replace(tzinfo=None):
            return True
        return False

    def reset_failed_login_attempts(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save()

    def increment_failed_login_attempts(self):
        """Increment failed login attempts and lock account if needed"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:  # Lock after 5 failed attempts
            self.locked_until = datetime.now() + timedelta(minutes=30)
        self.save()

    @property
    def is_user(self):
        return self.role == 'user'

    @property
    def is_moderator(self):
        return self.role == 'moderator'

    @property
    def is_super_admin(self):
        return self.role == 'admin'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_won = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_tickets_bought = models.IntegerField(default=0)
    total_lotteries_participated = models.IntegerField(default=0)
    total_wins = models.IntegerField(default=0)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)
    preferences = models.JSONField(default=dict, blank=True)
    # Referral tracking fields
    total_referrals = models.IntegerField(default=0, help_text='Total number of successful referrals')
    total_referral_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        help_text='Total earnings from referrals'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'
        ordering = ['-created_at']

    def __str__(self):
        return f"Profile of {self.user.username}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('REGISTER', 'User Registration'),
        ('PASSWORD_RESET_REQUEST', 'Password Reset Request'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('CHANGE_PASSWORD', 'Change Password'),
        ('EMAIL_VERIFICATION', 'Email Verification'),
        ('FAILED_LOGIN', 'Failed Login Attempt'),
        ('ACCOUNT_LOCKED', 'Account Locked'),
        ('ACCOUNT_UNLOCKED', 'Account Unlocked'),
        ('FAILED_REGISTER', 'Failed Registration'),
        ('CHANGE_ROLE', 'Change User Role'),
        ('TOGGLE_USER_STATUS', 'Toggle User Status'),
        ('BUY_TICKET', 'Bought Ticket'),
        ('WIN', 'Won Prize'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('DEPOSIT', 'Deposit'),
    ]
    
    RESOURCE_TYPE_CHOICES = [
        ('USER', 'User'),
        ('LOTTERY', 'Lottery'),
        ('TRANSACTION', 'Transaction'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('REFERRAL', 'Referral'),
        ('PAYMENT', 'Payment'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES, null=True, blank=True)
    resource_id = models.CharField(max_length=100, null=True, blank=True, help_text='UUID or ID of the affected resource')
    changes = models.JSONField(default=dict, blank=True, help_text='Before/after values for the change')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        username = self.user.username if self.user else "system"
        return f"{self.action} - {username} - {self.timestamp}"
