from django.contrib import admin
from apps.lotteries.models import Lottery, Ticket, Winner, LotteryDrawLog, LotteryTemplate


@admin.register(Lottery)
class LotteryAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'ticket_price', 'prize_amount', 'total_tickets', 'available_tickets', 'draw_date', 'created_at']
    list_filter = ['status', 'created_at', 'draw_date']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Lottery Information', {'fields': ('name', 'description', 'created_by')}),
        ('Pricing', {'fields': ('ticket_price', 'prize_amount')}),
        ('Tickets', {'fields': ('total_tickets', 'available_tickets')}),
        ('Status & Dates', {'fields': ('status', 'draw_date', 'created_at', 'updated_at')}),
    )


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'user', 'lottery', 'is_winner', 'purchased_at']
    list_filter = ['is_winner', 'purchased_at', 'lottery']
    search_fields = ['user__username', 'lottery__name']
    readonly_fields = ['purchased_at', 'ticket_number']


@admin.register(Winner)
class WinnerAdmin(admin.ModelAdmin):
    list_display = ['user', 'lottery', 'prize_amount', 'is_claimed', 'announced_at']
    list_filter = ['is_claimed', 'announced_at', 'lottery']
    search_fields = ['user__username', 'lottery__name']
    readonly_fields = ['announced_at', 'claimed_at']


@admin.register(LotteryDrawLog)
class LotteryDrawLogAdmin(admin.ModelAdmin):
    list_display = ['lottery', 'conducted_by', 'total_participants', 'total_tickets_sold', 'revenue', 'drawn_at']
    list_filter = ['drawn_at', 'lottery']
    search_fields = ['lottery__name', 'conducted_by__username']
    readonly_fields = ['drawn_at', 'random_seed']


@admin.register(LotteryTemplate)
class LotteryTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'ticket_price', 'prize_amount', 'total_tickets', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
