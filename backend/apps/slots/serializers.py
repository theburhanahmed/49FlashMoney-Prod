from rest_framework import serializers
from apps.slots.models import SlotsGame, SlotsSpin


class SlotsGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlotsGame
        fields = [
            'id', 'name', 'description', 'is_active',
            'paytable', 'reels', 'rtp_percent', 'min_bet', 'max_bet',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SlotsGameListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view - excludes reels/paytable payload."""
    class Meta:
        model = SlotsGame
        fields = [
            'id', 'name', 'description', 'is_active',
            'rtp_percent', 'min_bet', 'max_bet',
            'created_at',
        ]


class SlotsSpinSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source='game.name', read_only=True)

    class Meta:
        model = SlotsSpin
        fields = [
            'id', 'game', 'game_name', 'bet_amount', 'symbols',
            'payout', 'random_seed', 'created_at',
        ]
        read_only_fields = ['id', 'symbols', 'payout', 'random_seed', 'created_at']


class SlotsSpinRequestSerializer(serializers.Serializer):
    bet_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
