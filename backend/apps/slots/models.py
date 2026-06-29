"""
Slots game models.
"""
from django.db import models
from django.core.validators import MinValueValidator
from apps.users.models import User
import uuid


# Default 3-reel slots configuration
DEFAULT_REELS = [
    ["cherry", "lemon", "orange", "plum", "bell", "bar", "seven", "seven"],
    ["cherry", "lemon", "orange", "plum", "bell", "bar", "seven", "seven"],
    ["cherry", "lemon", "orange", "plum", "bell", "bar", "seven", "seven"],
]

DEFAULT_PAYTABLE = {
    "seven": 100,   # 3x seven = 100x bet
    "bar": 50,
    "bell": 25,
    "plum": 10,
    "orange": 5,
    "lemon": 3,
    "cherry": 2,     # 3x cherry = 2x bet
}


class SlotsGame(models.Model):
    """
    Admin-configurable slots game.
    Paytable: symbol -> multiplier (payout = bet * multiplier for 3 matching),
    Reels: list of reels, each reel is list of symbols.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    # Paytable: { "symbol": multiplier } for 3-of-a-kind
    paytable = models.JSONField(default=dict, help_text="Symbol -> multiplier for 3 matching")
    # Reels: [ [symbol, symbol, ...], [symbol, ...], [symbol, ...] ]
    reels = models.JSONField(default=list, help_text="List of 3 reels, each with symbols")
    # RTP (Return to Player) target percentage - informational
    rtp_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=96.00,
        validators=[MinValueValidator(1)]
    )
    min_bet = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.10,
        validators=[MinValueValidator(0.01)]
    )
    max_bet = models.DecimalField(
        max_digits=10, decimal_places=2, default=100.00,
        validators=[MinValueValidator(0.01)]
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='created_slots_games', null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'slots_games'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {'Active' if self.is_active else 'Inactive'}"

    def get_payout(self, symbol):
        """Get multiplier for symbol from paytable."""
        return self.paytable.get(symbol, 0)


class SlotsSpin(models.Model):
    """
    Immutable record of each spin for provably fair verification.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='slots_spins')
    game = models.ForeignKey(SlotsGame, on_delete=models.PROTECT, related_name='spins')
    bet_amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Result: [symbol1, symbol2, symbol3] for 3 reels
    symbols = models.JSONField(default=list)
    payout = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Provably fair: store seed so user can verify
    random_seed = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'slots_spins'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['game', '-created_at']),
        ]

    def __str__(self):
        return f"Spin {self.id} - {self.user.username} - {self.symbols}"
