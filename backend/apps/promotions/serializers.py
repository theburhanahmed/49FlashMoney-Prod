"""Promotions serializers."""
from rest_framework import serializers

from .models import Promotion, PromotionClaim


class PromotionSerializer(serializers.ModelSerializer):
    """Read/write serializer for Promotion (used by admin create/update)."""

    class Meta:
        model = Promotion
        fields = [
            'id',
            'name',
            'description',
            'promotion_type',
            'status',
            'bonus_percentage',
            'max_bonus_amount',
            'min_deposit',
            'wagering_requirement',
            'start_date',
            'end_date',
            'max_claims',
            'total_claims',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'total_claims', 'created_at', 'updated_at']


class PromotionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (omits heavy description)."""

    class Meta:
        model = Promotion
        fields = [
            'id',
            'name',
            'promotion_type',
            'status',
            'bonus_percentage',
            'max_bonus_amount',
            'min_deposit',
            'wagering_requirement',
            'start_date',
            'end_date',
            'max_claims',
            'total_claims',
        ]


class ClaimPromotionSerializer(serializers.Serializer):
    """Input serializer for the `claim` action."""

    deposit_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=0,
        help_text=(
            "Required for DEPOSIT_BONUS and CASHBACK promotion types. "
            "The amount the user is depositing alongside this claim."
        ),
    )


class PromotionClaimSerializer(serializers.ModelSerializer):
    """Serializer for PromotionClaim records (read-only for end-users)."""

    promotion = PromotionListSerializer(read_only=True)
    promotion_id = serializers.UUIDField(source='promotion.id', read_only=True)

    class Meta:
        model = PromotionClaim
        fields = [
            'id',
            'promotion_id',
            'promotion',
            'bonus_amount',
            'deposit_amount',
            'wagering_remaining',
            'status',
            'claimed_at',
        ]
        read_only_fields = fields
