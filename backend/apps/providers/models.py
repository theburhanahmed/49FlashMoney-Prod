"""
Provider platform models for 49FlashMoney.

All records are append-only — never modified after creation.
Corrections / state changes use status transitions, not field mutation.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator

from apps.users.models import User


# --------------------------------------------------------------------------- #
# Provider configuration                                                        #
# --------------------------------------------------------------------------- #

class ProviderConfig(models.Model):
    """
    Stores credentials and settings for each casino game provider.

    One row per provider slug.  Credentials are stored as an encrypted JSON
    blob (use environment secrets or a vault in production; the `credentials`
    field itself is treated as opaque storage here).
    """

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_MAINTENANCE = 'MAINTENANCE'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_MAINTENANCE, 'Maintenance'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(
        max_length=64,
        unique=True,
        help_text='Provider identifier matching the adapter slug (e.g. "demo", "pragmatic").',
    )
    display_name = models.CharField(max_length=128)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    # Opaque credentials blob — store API keys / secrets here.
    # In production, encrypt this field at the application layer or use a vault.
    credentials = models.JSONField(
        default=dict,
        blank=True,
        help_text='Provider API credentials (api_key, secret, endpoint, …).',
    )
    # Operational settings: timeout, retry policy, RTP overrides, etc.
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text='Adapter-specific operational settings.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'provider_configs'
        ordering = ['slug']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.slug}) [{self.status}]"


# --------------------------------------------------------------------------- #
# Game catalogue                                                                #
# --------------------------------------------------------------------------- #

class ProviderGameCatalog(models.Model):
    """
    Cached copy of a provider's game catalogue.

    Populated by a periodic sync task (or on-demand via admin).
    The platform reads from this table to avoid hitting the provider API on
    every player request.
    """

    CATEGORY_SLOTS = 'slots'
    CATEGORY_TABLE = 'table'
    CATEGORY_LIVE = 'live'
    CATEGORY_INSTANT_WIN = 'instant_win'
    CATEGORY_OTHER = 'other'

    CATEGORY_CHOICES = [
        (CATEGORY_SLOTS, 'Slots'),
        (CATEGORY_TABLE, 'Table Games'),
        (CATEGORY_LIVE, 'Live Casino'),
        (CATEGORY_INSTANT_WIN, 'Instant Win'),
        (CATEGORY_OTHER, 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        ProviderConfig,
        on_delete=models.CASCADE,
        related_name='games',
    )
    # Provider's own identifier for the game
    provider_game_id = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    thumbnail_url = models.URLField(blank=True, max_length=1024)
    is_active = models.BooleanField(default=True)
    min_bet = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.10'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    max_bet = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('10000.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    rtp = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('96.00'),
        help_text='Return-to-player percentage.',
    )
    tags = models.JSONField(default=list, blank=True)
    extra = models.JSONField(default=dict, blank=True)
    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'provider_game_catalog'
        unique_together = [['provider', 'provider_game_id']]
        ordering = ['provider', 'name']
        indexes = [
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['category']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self) -> str:
        return f"{self.provider.slug}/{self.provider_game_id} – {self.name}"


# --------------------------------------------------------------------------- #
# Game sessions                                                                 #
# --------------------------------------------------------------------------- #

class ProviderGameSession(models.Model):
    """
    Records every game session launched by a user.

    Sessions are append-only.  When a session expires or is closed,
    its status is updated via a status transition (never field edit).
    """

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_EXPIRED = 'EXPIRED'
    STATUS_CLOSED = 'CLOSED'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_CLOSED, 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='provider_sessions',
    )
    provider = models.ForeignKey(
        ProviderConfig,
        on_delete=models.PROTECT,
        related_name='sessions',
    )
    game = models.ForeignKey(
        ProviderGameCatalog,
        on_delete=models.PROTECT,
        related_name='sessions',
        null=True,
        blank=True,
    )
    # Provider's session token (opaque string)
    session_token = models.CharField(max_length=512, unique=True)
    # Fully-qualified launch URL provided to the client
    launch_url = models.URLField(max_length=2048)
    currency = models.CharField(max_length=3, default='INR')
    mode = models.CharField(
        max_length=8,
        choices=[('real', 'Real'), ('demo', 'Demo')],
        default='real',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'provider_game_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['session_token']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self) -> str:
        return f"Session({self.user.username} / {self.provider.slug} / {self.status})"


# --------------------------------------------------------------------------- #
# Game rounds                                                                   #
# --------------------------------------------------------------------------- #

class ProviderRound(models.Model):
    """
    Immutable record of every provider game round.

    Each row represents one complete bet → settle lifecycle.
    Refunds produce a separate row with status='REFUNDED'.
    """

    STATUS_PENDING = 'PENDING'
    STATUS_WON = 'WON'
    STATUS_LOST = 'LOST'
    STATUS_PUSH = 'PUSH'
    STATUS_SETTLED = 'SETTLED'
    STATUS_REFUNDED = 'REFUNDED'
    STATUS_VOIDED = 'VOIDED'
    STATUS_ERROR = 'ERROR'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_WON, 'Won'),
        (STATUS_LOST, 'Lost'),
        (STATUS_PUSH, 'Push'),
        (STATUS_SETTLED, 'Settled'),
        (STATUS_REFUNDED, 'Refunded'),
        (STATUS_VOIDED, 'Voided'),
        (STATUS_ERROR, 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ProviderGameSession,
        on_delete=models.PROTECT,
        related_name='rounds',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='provider_rounds',
    )
    provider = models.ForeignKey(
        ProviderConfig,
        on_delete=models.PROTECT,
        related_name='rounds',
    )
    game = models.ForeignKey(
        ProviderGameCatalog,
        on_delete=models.PROTECT,
        related_name='rounds',
        null=True,
        blank=True,
    )
    # Platform-side round ID (used as idempotency key with WalletService)
    round_id = models.CharField(max_length=128, unique=True)
    # Provider's own round reference (may differ from our round_id)
    provider_round_id = models.CharField(max_length=256, blank=True)
    bet_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    payout = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
    )
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    # IDs of the ledger entries created for this round
    bet_ledger_entry_id = models.CharField(max_length=64, blank=True)
    payout_ledger_entry_id = models.CharField(max_length=64, blank=True)
    # Raw provider response (for audit / debugging)
    raw_bet_response = models.JSONField(default=dict, blank=True)
    raw_settle_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'provider_rounds'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['provider', 'status']),
            models.Index(fields=['round_id']),
            models.Index(fields=['provider_round_id']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self) -> str:
        return (
            f"Round({self.round_id} / {self.provider.slug} / "
            f"{self.user.username} / {self.status})"
        )
