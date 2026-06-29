from rest_framework import serializers
from apps.users.models import User
from .models import GameRoom, GameRoomPlayer, GameState, GameKind


class GameRoomPlayerSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)

    class Meta:
        model = GameRoomPlayer
        fields = ['id', 'user_id', 'username', 'position', 'result', 'payout', 'joined_at']


class GameRoomListSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    player_count = serializers.SerializerMethodField()

    class Meta:
        model = GameRoom
        fields = [
            'id', 'game_kind', 'status', 'entry_fee',
            'min_players', 'max_players', 'created_by_username',
            'player_count', 'created_at',
        ]

    def get_player_count(self, obj):
        return obj.players.count()


class GameRoomDetailSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    players = GameRoomPlayerSerializer(many=True, read_only=True)
    state = serializers.SerializerMethodField()

    class Meta:
        model = GameRoom
        fields = [
            'id', 'game_kind', 'status', 'entry_fee',
            'min_players', 'max_players', 'created_by', 'created_by_username',
            'config', 'players', 'state', 'created_at', 'started_at', 'ended_at',
        ]

    def get_state(self, obj):
        try:
            gs = obj.game_state
            return gs.state
        except GameState.DoesNotExist:
            return None


class CreateRoomSerializer(serializers.Serializer):
    game_kind = serializers.ChoiceField(choices=GameKind.CHOICES)
    entry_fee = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    config = serializers.JSONField(required=False, default=dict)
