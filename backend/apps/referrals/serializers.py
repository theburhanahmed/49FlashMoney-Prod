from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ReferralProgram,
    ReferralLink,
    Referral,
    ReferralBonus,
    ReferralWithdrawal
)


class ReferralProgramSerializer(serializers.ModelSerializer):
    """
    Serializer for referral program configuration.
    Readable by all users, editable by admin only.
    """
    class Meta:
        model = ReferralProgram
        fields = [
            'id',
            'status',
            'referral_bonus_amount',
            'referred_user_bonus',
            'minimum_referral_deposit',
            'bonus_expiry_days',
            'min_referral_balance_to_withdraw',
            'max_withdrawals_per_month',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ReferralLinkSerializer(serializers.ModelSerializer):
    """
    Serializer for user referral links.
    Shows referral code and stats.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    referral_url = serializers.SerializerMethodField()

    class Meta:
        model = ReferralLink
        fields = [
            'id',
            'username',
            'referral_code',
            'referral_url',
            'total_referred',
            'total_bonus_earned',
            'total_referrals_clicked',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'referral_code',
            'total_referred',
            'total_bonus_earned',
            'total_referrals_clicked',
            'created_at',
            'updated_at'
        ]

    def get_referral_url(self, obj):
        """Generate full referral URL."""
        request = self.context.get('request')
        if request:
            domain = request.META.get('HTTP_HOST', 'localhost')
            return f'https://{domain}/register?ref={obj.referral_code}'
        return f'/register?ref={obj.referral_code}'


class ReferralSimpleSerializer(serializers.ModelSerializer):
    """
    Simple serializer for displaying referral info.
    """
    referrer_username = serializers.CharField(source='referrer.username', read_only=True)
    referred_username = serializers.CharField(source='referred_user.username', read_only=True)

    class Meta:
        model = Referral
        fields = [
            'id',
            'referrer_username',
            'referred_username',
            'status',
            'referrer_bonus',
            'referred_user_bonus',
            'created_at'
        ]


class ReferralDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for referral information.
    """
    referrer_username = serializers.CharField(source='referrer.username', read_only=True)
    referred_username = serializers.CharField(source='referred_user.username', read_only=True)
    referred_email = serializers.CharField(source='referred_user.email', read_only=True)
    bonuses = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = [
            'id',
            'referrer_username',
            'referred_username',
            'referred_email',
            'status',
            'referrer_bonus',
            'referred_user_bonus',
            'bonus_awarded_at',
            'referred_user_deposit',
            'deposit_date',
            'rejection_reason',
            'bonuses',
            'is_expired',
            'days_until_expiry',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'referrer_username',
            'referred_username',
            'referred_email',
            'bonuses',
            'is_expired',
            'created_at',
            'updated_at'
        ]

    def get_bonuses(self, obj):
        """Get associated bonuses."""
        bonuses = obj.bonuses.all()
        return ReferralBonusSerializer(bonuses, many=True).data

    def get_days_until_expiry(self, obj):
        """Calculate days until expiry."""
        from django.utils import timezone
        from datetime import timedelta
        
        if obj.status == 'PENDING':
            delta = obj.expires_at - timezone.now()
            return max(0, delta.days)
        return None


class ReferralBonusSerializer(serializers.ModelSerializer):
    """
    Serializer for referral bonuses.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    referrer = serializers.CharField(
        source='referral.referrer.username',
        read_only=True
    )
    referred = serializers.CharField(
        source='referral.referred_user.username',
        read_only=True
    )

    class Meta:
        model = ReferralBonus
        fields = [
            'id',
            'username',
            'referrer',
            'referred',
            'bonus_type',
            'amount',
            'status',
            'credited_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'username',
            'referrer',
            'referred',
            'amount',
            'credited_at',
            'created_at',
            'updated_at'
        ]


class ReferralWithdrawalSerializer(serializers.ModelSerializer):
    """
    Serializer for referral bonus withdrawals.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    processed_by_username = serializers.CharField(
        source='processed_by.username',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = ReferralWithdrawal
        fields = [
            'id',
            'username',
            'amount',
            'status',
            'payment_method',
            'admin_notes',
            'rejection_reason',
            'processed_by_username',
            'processed_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'username',
            'status',
            'admin_notes',
            'rejection_reason',
            'processed_by_username',
            'processed_at',
            'created_at',
            'updated_at'
        ]


class ReferralWithdrawalCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating referral withdrawal requests.
    """
    available_balance = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ReferralWithdrawal
        fields = [
            'id',
            'amount',
            'payment_method',
            'available_balance',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'available_balance']

    def get_available_balance(self, obj):
        """Get user's available referral bonus balance."""
        from django.contrib.auth.models import User
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            bonuses = ReferralBonus.objects.filter(
                user=request.user,
                status='CREDITED'
            )
            return sum(float(b.amount) for b in bonuses)
        return 0.00

    def validate_amount(self, value):
        """Validate withdrawal amount."""
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        
        # Check minimum balance requirement
        program = ReferralProgram.get_program()
        if value < program.min_referral_balance_to_withdraw:
            raise serializers.ValidationError(
                f'Minimum withdrawal amount is {program.min_referral_balance_to_withdraw}'
            )
        
        return value

    def validate(self, data):
        """Validate withdrawal request."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('User must be authenticated.')
        
        # Check available balance
        bonuses = ReferralBonus.objects.filter(
            user=request.user,
            status='CREDITED'
        )
        available = sum(float(b.amount) for b in bonuses)
        
        if data['amount'] > available:
            raise serializers.ValidationError(
                f'Insufficient balance. Available: {available}'
            )
        
        # Check withdrawal limit
        program = ReferralProgram.get_program()
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        
        month_ago = timezone.now() - relativedelta(months=1)
        withdrawals_this_month = ReferralWithdrawal.objects.filter(
            user=request.user,
            created_at__gte=month_ago
        ).exclude(status='REJECTED').count()
        
        if withdrawals_this_month >= program.max_withdrawals_per_month:
            raise serializers.ValidationError(
                f'Maximum withdrawals per month ({program.max_withdrawals_per_month}) reached.'
            )
        
        return data

    def create(self, validated_data):
        """Create withdrawal request."""
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)


class ReferralWithdrawalAdminSerializer(serializers.ModelSerializer):
    """
    Admin serializer for managing withdrawal requests.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    processed_by_username = serializers.CharField(
        source='processed_by.username',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = ReferralWithdrawal
        fields = [
            'id',
            'username',
            'amount',
            'status',
            'payment_method',
            'admin_notes',
            'rejection_reason',
            'processed_by_username',
            'processed_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserReferralStatsSerializer(serializers.Serializer):
    """
    Serializer for user referral statistics.
    """
    total_referred = serializers.IntegerField()
    total_bonus_earned = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_referrals = serializers.IntegerField()
    qualified_referrals = serializers.IntegerField()
    available_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_withdrawals = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_withdrawn = serializers.DecimalField(max_digits=15, decimal_places=2)
    referral_code = serializers.CharField()
    referral_url = serializers.CharField()
