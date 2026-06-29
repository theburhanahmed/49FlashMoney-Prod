from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from .models import (
    ReferralProgram,
    ReferralLink,
    Referral,
    ReferralBonus,
    ReferralWithdrawal
)


@admin.register(ReferralProgram)
class ReferralProgramAdmin(admin.ModelAdmin):
    """
    Admin interface for referral program configuration.
    """
    fieldsets = (
        ('Program Status', {
            'fields': ('status',)
        }),
        ('Bonus Configuration', {
            'fields': (
                'referral_bonus_amount',
                'referred_user_bonus',
                'minimum_referral_deposit',
                'bonus_expiry_days'
            ),
            'description': 'Set bonus amounts and requirements'
        }),
        ('Withdrawal Control', {
            'fields': (
                'min_referral_balance_to_withdraw',
                'max_withdrawals_per_month'
            ),
            'description': 'Control withdrawal limits and requirements'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    list_display = ('get_status_display', 'referral_bonus_amount', 'referred_user_bonus', 'bonus_expiry_days')

    def has_add_permission(self, request):
        """Only one program instance should exist."""
        return not ReferralProgram.objects.exists()


@admin.register(ReferralLink)
class ReferralLinkAdmin(admin.ModelAdmin):
    """
    Admin interface for user referral links.
    """
    list_display = ('username', 'referral_code', 'total_referred', 'total_bonus_earned', 'created_at')
    list_filter = ('created_at', 'total_referred')
    search_fields = ('user__username', 'referral_code')
    readonly_fields = ('user', 'referral_code', 'total_referred', 'total_bonus_earned', 'total_referrals_clicked', 'created_at', 'updated_at')

    def username(self, obj):
        """Display username."""
        return obj.user.username
    username.short_description = 'Username'

    def has_add_permission(self, request):
        """Referral links are created automatically."""
        return False


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    """
    Admin interface for managing referrals.
    """
    fieldsets = (
        ('Users', {
            'fields': ('referrer', 'referred_user')
        }),
        ('Status & Bonuses', {
            'fields': ('status', 'referrer_bonus', 'referred_user_bonus', 'bonus_awarded_at')
        }),
        ('Requirements Tracking', {
            'fields': ('referred_user_deposit', 'deposit_date')
        }),
        ('Admin Actions', {
            'fields': ('rejection_reason',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_display = ('referrer_name', 'referred_name', 'status_colored', 'referrer_bonus', 'days_remaining', 'created_at')
    list_filter = ('status', 'created_at', 'bonus_awarded_at')
    search_fields = ('referrer__username', 'referred_user__username')
    readonly_fields = ('referrer', 'referred_user', 'bonus_awarded_at', 'created_at', 'updated_at', 'expires_at')
    actions = ['approve_referrals', 'reject_referrals']

    def referrer_name(self, obj):
        """Display referrer username."""
        return obj.referrer.username
    referrer_name.short_description = 'Referrer'

    def referred_name(self, obj):
        """Display referred user username."""
        return obj.referred_user.username
    referred_name.short_description = 'Referred User'

    def status_colored(self, obj):
        """Display status with color."""
        colors = {
            'PENDING': '#FFA500',
            'QUALIFIED': '#4169E1',
            'BONUS_AWARDED': '#228B22',
            'REJECTED': '#DC143C',
            'CANCELLED': '#808080'
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def days_remaining(self, obj):
        """Display days until expiry."""
        from django.utils import timezone
        if obj.status == 'PENDING':
            delta = obj.expires_at - timezone.now()
            days = delta.days
            if days < 0:
                return format_html('<span style="color: red;">Expired</span>')
            elif days <= 7:
                return format_html('<span style="color: orange;">{} days</span>', days)
            else:
                return f"{days} days"
        return '-'
    days_remaining.short_description = 'Days Remaining'

    def approve_referrals(self, request, queryset):
        """Admin action to approve referrals."""
        from django.utils import timezone
        program = ReferralProgram.get_program()
        
        count = 0
        for referral in queryset.filter(status='PENDING'):
            referral.status = 'BONUS_AWARDED'
            referral.referrer_bonus = program.referral_bonus_amount
            referral.referred_user_bonus = program.referred_user_bonus
            referral.bonus_awarded_at = timezone.now()
            referral.save()
            
            # Create bonuses
            ReferralBonus.objects.create(
                user=referral.referrer,
                referral=referral,
                bonus_type='REFERRER',
                amount=program.referral_bonus_amount,
                status='CREDITED',
                credited_at=timezone.now()
            )
            
            ReferralBonus.objects.create(
                user=referral.referred_user,
                referral=referral,
                bonus_type='REFERRED',
                amount=program.referred_user_bonus,
                status='CREDITED',
                credited_at=timezone.now()
            )
            
            # Credit bonuses to users
            referral.referrer.add_balance(program.referral_bonus_amount)
            referral.referred_user.add_balance(program.referred_user_bonus)
            
            # Update referral link
            referral.referrer.referral_link.total_referred += 1
            referral.referrer.referral_link.total_bonus_earned += program.referral_bonus_amount
            referral.referrer.referral_link.save()
            
            # Send notification emails
            from apps.notifications.tasks import send_referral_bonus_credited_task
            send_referral_bonus_credited_task.delay(
                str(referral.referrer.id),
                float(program.referral_bonus_amount),
                str(referral.id)
            )
            send_referral_bonus_credited_task.delay(
                str(referral.referred_user.id),
                float(program.referred_user_bonus),
                str(referral.id)
            )
            
            count += 1
        
        self.message_user(request, f'{count} referrals approved and bonuses awarded.')
    
    approve_referrals.short_description = 'Approve selected referrals'

    def reject_referrals(self, request, queryset):
        """Admin action to reject referrals."""
        count = queryset.filter(status='PENDING').update(status='REJECTED')
        self.message_user(request, f'{count} referrals rejected.')
    
    reject_referrals.short_description = 'Reject selected referrals'


@admin.register(ReferralBonus)
class ReferralBonusAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing referral bonuses.
    """
    list_display = ('username', 'bonus_type', 'amount', 'status', 'credited_at', 'created_at')
    list_filter = ('status', 'bonus_type', 'created_at')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'referral', 'bonus_type', 'amount', 'credited_at', 'created_at', 'updated_at')
    
    def username(self, obj):
        """Display username."""
        return obj.user.username
    username.short_description = 'Username'

    def has_add_permission(self, request):
        """Bonuses are created automatically."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of bonus records."""
        return False


@admin.register(ReferralWithdrawal)
class ReferralWithdrawalAdmin(admin.ModelAdmin):
    """
    Admin interface for managing referral bonus withdrawals.
    """
    fieldsets = (
        ('Withdrawal Info', {
            'fields': ('user', 'amount', 'status', 'payment_method')
        }),
        ('Admin Actions', {
            'fields': ('admin_notes', 'rejection_reason')
        }),
        ('Processing', {
            'fields': ('processed_by', 'processed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    list_display = ('username', 'amount', 'status_colored', 'payment_method', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'created_at', 'updated_at', 'processed_by', 'processed_at')
    actions = ['approve_withdrawals', 'reject_withdrawals', 'mark_as_processing', 'mark_as_completed']

    def username(self, obj):
        """Display username."""
        return obj.user.username
    username.short_description = 'Username'

    def status_colored(self, obj):
        """Display status with color."""
        colors = {
            'PENDING': '#FFA500',
            'APPROVED': '#4169E1',
            'PROCESSING': '#FF6347',
            'COMPLETED': '#228B22',
            'REJECTED': '#DC143C',
            'CANCELLED': '#808080'
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def approve_withdrawals(self, request, queryset):
        """Admin action to approve withdrawals."""
        from django.utils import timezone
        count = queryset.filter(status='PENDING').update(
            status='APPROVED',
            processed_by=request.user,
            processed_at=timezone.now()
        )
        self.message_user(request, f'{count} withdrawals approved.')
    approve_withdrawals.short_description = 'Approve selected withdrawals'

    def reject_withdrawals(self, request, queryset):
        """Admin action to reject withdrawals."""
        from django.utils import timezone
        count = queryset.filter(status__in=['PENDING', 'APPROVED']).update(
            status='REJECTED',
            processed_by=request.user,
            processed_at=timezone.now()
        )
        self.message_user(request, f'{count} withdrawals rejected.')
    reject_withdrawals.short_description = 'Reject selected withdrawals'

    def mark_as_processing(self, request, queryset):
        """Admin action to mark as processing."""
        count = queryset.filter(status='APPROVED').update(status='PROCESSING')
        self.message_user(request, f'{count} withdrawals marked as processing.')
    mark_as_processing.short_description = 'Mark as processing'

    def mark_as_completed(self, request, queryset):
        """Admin action to mark as completed."""
        from django.utils import timezone
        count = queryset.filter(status__in=['APPROVED', 'PROCESSING']).update(
            status='COMPLETED',
            processed_by=request.user,
            processed_at=timezone.now()
        )
        self.message_user(request, f'{count} withdrawals marked as completed.')
    mark_as_completed.short_description = 'Mark as completed'
