from django.contrib import admin
from apps.slots.models import SlotsGame, SlotsSpin


@admin.register(SlotsGame)
class SlotsGameAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'min_bet', 'max_bet', 'rtp_percent', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Game Info', {'fields': ('name', 'description', 'is_active')}),
        ('Configuration', {'fields': ('paytable', 'reels', 'rtp_percent', 'min_bet', 'max_bet')}),
        ('Metadata', {'fields': ('created_by', 'created_at', 'updated_at')}),
    )


@admin.register(SlotsSpin)
class SlotsSpinAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'game', 'bet_amount', 'symbols_display', 'payout', 'created_at']
    list_filter = ['game', 'created_at']
    search_fields = ['user__username', 'game__name']
    readonly_fields = ['id', 'random_seed', 'created_at']

    def symbols_display(self, obj):
        return str(obj.symbols) if obj.symbols else '-'

    symbols_display.short_description = 'Symbols'
