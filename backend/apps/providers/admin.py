"""
Django admin registration for Provider models.
"""
from django.contrib import admin

from .models import ProviderConfig, ProviderGameCatalog, ProviderGameSession, ProviderRound


@admin.register(ProviderConfig)
class ProviderConfigAdmin(admin.ModelAdmin):
    list_display = ['slug', 'display_name', 'status', 'updated_at']
    list_filter = ['status']
    search_fields = ['slug', 'display_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ProviderGameCatalog)
class ProviderGameCatalogAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'category', 'is_active', 'min_bet', 'max_bet', 'rtp', 'synced_at']
    list_filter = ['provider', 'category', 'is_active']
    search_fields = ['name', 'provider_game_id']
    readonly_fields = ['id', 'created_at', 'synced_at']


@admin.register(ProviderGameSession)
class ProviderGameSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'provider', 'game', 'mode', 'status', 'created_at']
    list_filter = ['provider', 'status', 'mode']
    search_fields = ['user__username', 'session_token']
    readonly_fields = ['id', 'session_token', 'launch_url', 'created_at']


@admin.register(ProviderRound)
class ProviderRoundAdmin(admin.ModelAdmin):
    list_display = [
        'round_id', 'user', 'provider', 'game', 'bet_amount', 'payout',
        'currency', 'status', 'created_at', 'settled_at',
    ]
    list_filter = ['provider', 'status', 'currency']
    search_fields = ['round_id', 'provider_round_id', 'user__username']
    readonly_fields = [
        'id', 'round_id', 'bet_ledger_entry_id', 'payout_ledger_entry_id',
        'raw_bet_response', 'raw_settle_response', 'created_at', 'settled_at',
    ]
