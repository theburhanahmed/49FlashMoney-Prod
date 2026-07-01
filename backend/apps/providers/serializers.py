"""
Provider serializers for 49FlashMoney.
"""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import ProviderConfig, ProviderGameCatalog, ProviderGameSession, ProviderRound


class ProviderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderConfig
        fields = ['id', 'slug', 'display_name', 'status', 'settings', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProviderGameCatalogSerializer(serializers.ModelSerializer):
    provider_slug = serializers.CharField(source='provider.slug', read_only=True)

    class Meta:
        model = ProviderGameCatalog
        fields = [
            'id', 'provider_slug', 'provider_game_id', 'name', 'category',
            'thumbnail_url', 'is_active', 'min_bet', 'max_bet', 'rtp',
            'tags', 'synced_at', 'created_at',
        ]
        read_only_fields = fields


class ProviderGameSessionSerializer(serializers.ModelSerializer):
    provider_slug = serializers.CharField(source='provider.slug', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True, default='')

    class Meta:
        model = ProviderGameSession
        fields = [
            'id', 'provider_slug', 'game_name', 'session_token', 'launch_url',
            'currency', 'mode', 'status', 'created_at', 'expires_at', 'closed_at',
        ]
        read_only_fields = fields


class ProviderRoundSerializer(serializers.ModelSerializer):
    provider_slug = serializers.CharField(source='provider.slug', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True, default='')

    class Meta:
        model = ProviderRound
        fields = [
            'id', 'round_id', 'provider_slug', 'game_name', 'bet_amount',
            'payout', 'currency', 'status', 'created_at', 'settled_at',
        ]
        read_only_fields = fields


# ---------- Request serializers ------------------------------------------- #

class LaunchGameRequestSerializer(serializers.Serializer):
    slug = serializers.CharField(max_length=64)
    provider_game_id = serializers.CharField(max_length=256)
    currency = serializers.CharField(max_length=3, default='INR')
    language = serializers.CharField(max_length=5, default='en')
    mode = serializers.ChoiceField(choices=['real', 'demo'], default='real')
    return_url = serializers.URLField(required=False, allow_blank=True, default='')


class PlaceBetRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    bet_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        min_value=Decimal('0.01'),
    )


class SettleRoundRequestSerializer(serializers.Serializer):
    round_id = serializers.CharField(max_length=128)
    payout = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.00'))


class RefundRoundRequestSerializer(serializers.Serializer):
    round_id = serializers.CharField(max_length=128)
    reason = serializers.CharField(max_length=512, required=False, allow_blank=True, default='')
