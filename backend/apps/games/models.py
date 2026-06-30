"""
Game platform models: rooms, players, state.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from apps.users.models import User


class GameKind:
    """Game type constants."""
    SNAKES_LADDERS = 'SNAKES_LADDERS'
    LUDO = 'LUDO'
    CARROM = 'CARROM'
    AVIATOR = 'AVIATOR'
    WINGO = 'WINGO'

    CHOICES = [
        (SNAKES_LADDERS, 'Snakes & Ladders'),
        (LUDO, 'Ludo'),
        (CARROM, 'Carrom'),
        (AVIATOR, 'Aviator'),
        (WINGO, 'Wingo'),
    ]


class GameRoom(models.Model):
    STATUS_WAITING = 'WAITING'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_WAITING, 'Waiting'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game_kind = models.CharField(max_length=32, choices=GameKind.CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WAITING)
    entry_fee = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    min_players = models.PositiveSmallIntegerField(default=2)
    max_players = models.PositiveSmallIntegerField(default=4)
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='created_game_rooms'
    )
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'games_rooms'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['game_kind']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.get_game_kind_display()} - {self.status} - {self.id}"


class GameRoomPlayer(models.Model):
    RESULT_WON = 'WON'
    RESULT_LOST = 'LOST'
    RESULT_DRAW = 'DRAW'
    RESULT_DISCONNECTED = 'DISCONNECTED'
    RESULT_PENDING = 'PENDING'

    RESULT_CHOICES = [
        (RESULT_WON, 'Won'),
        (RESULT_LOST, 'Lost'),
        (RESULT_DRAW, 'Draw'),
        (RESULT_DISCONNECTED, 'Disconnected'),
        (RESULT_PENDING, 'Pending'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        GameRoom, on_delete=models.CASCADE, related_name='players'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='game_room_players'
    )
    position = models.PositiveSmallIntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    balance_snapshot = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    result = models.CharField(
        max_length=20, choices=RESULT_CHOICES,
        default=RESULT_PENDING, blank=True
    )
    payout = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, null=True, blank=True
    )

    class Meta:
        db_table = 'games_room_players'
        ordering = ['room', 'position']
        unique_together = [['room', 'user']]
        indexes = [
            models.Index(fields=['room']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.room_id}"


class GameState(models.Model):
    """One state record per room. state JSON is game-type-specific."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.OneToOneField(
        GameRoom, on_delete=models.CASCADE, related_name='game_state'
    )
    state = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'games_state'

    def __str__(self):
        return f"State for {self.room_id} v{self.version}"
