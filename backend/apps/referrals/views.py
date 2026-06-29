from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.cache import cache
from apps.common.cache import CacheKeys
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.contrib.auth.models import User
import uuid
import string
import random

from .models import (
    ReferralProgram,
    ReferralLink,
    Referral,
    ReferralBonus,
    ReferralWithdrawal
)
from .serializers import (
    ReferralProgramSerializer,
    ReferralLinkSerializer,
    ReferralDetailSerializer,
    ReferralBonusSerializer,
    ReferralWithdrawalSerializer,
    ReferralWithdrawalCreateSerializer,
    ReferralWithdrawalAdminSerializer,
    UserReferralStatsSerializer
)


class IsAdmin(permissions.BasePermission):
    """Check if user is admin."""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class ReferralProgramViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing referral program configuration.
    Only admins can view and edit.
    """
    queryset = ReferralProgram.objects.all()
    serializer_class = ReferralProgramSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        """Return the single referral program instance."""
        return ReferralProgram.objects.all()[:1]

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current referral program settings."""
        # Cache referral program settings
        cache_key = CacheKeys.referral_program_settings()
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return Response(cached_result)
        
        program = ReferralProgram.get_program()
        serializer = self.get_serializer(program)
        result = serializer.data
        
        # Cache for 10 minutes
        cache.set(cache_key, result, 600)
        
        return Response(result)


class ReferralLinkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user referral links.
    Users can view their own link, admins can view all.
    """
    queryset = ReferralLink.objects.all()
    serializer_class = ReferralLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by user unless admin."""
        # Handle schema generation (drf_yasg uses AnonymousUser)
        if getattr(self, 'swagger_fake_view', False):
            return ReferralLink.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return ReferralLink.objects.none()
        
        user = self.request.user
        if user.is_staff:
            return ReferralLink.objects.all()
        return ReferralLink.objects.filter(user=user)

    @action(detail=False, methods=['get'])
    def my_link(self, request):
        """Get current user's referral link."""
        try:
            link = request.user.referral_link
        except ReferralLink.DoesNotExist:
            # Create if doesn't exist
            code = self._generate_referral_code()
            link = ReferralLink.objects.create(
                user=request.user,
                referral_code=code
            )
        
        serializer = self.get_serializer(link, context={'request': request})
        return Response(serializer.data)

    @staticmethod
    def _generate_referral_code():
        """Generate unique referral code."""
        while True:
            code = f'{timezone.now().year}' + ''.join(
                random.choices(string.ascii_letters + string.digits, k=12)
            )
            if not ReferralLink.objects.filter(referral_code=code).exists():
                return code


class ReferralViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing referrals.
    Users can view their referrals, admins can manage all.
    """
    queryset = Referral.objects.all()
    serializer_class = ReferralDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by user unless admin."""
        # Handle schema generation (drf_yasg uses AnonymousUser)
        if getattr(self, 'swagger_fake_view', False):
            return Referral.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return Referral.objects.none()
        
        user = self.request.user
        if user.is_staff:
            return Referral.objects.all()
        # Users can view referrals they made or referrals where they're the referred user
        return Referral.objects.filter(
            Q(referrer=user) | Q(referred_user=user)
        )

    @action(detail=False, methods=['get'])
    def my_referrals(self, request):
        """Get referrals made by current user."""
        referrals = Referral.objects.filter(referrer=request.user)
        serializer = self.get_serializer(referrals, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get referral statistics for current user."""
        user = request.user
        
        # Try to get from cache
        cache_key = CacheKeys.referral_stats(user.id)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return Response(cached_result)
        
        try:
            link = user.referral_link
        except ReferralLink.DoesNotExist:
            code = ReferralLinkViewSet._generate_referral_code()
            link = ReferralLink.objects.create(
                user=user,
                referral_code=code
            )
        
        # Calculate stats
        referrals = Referral.objects.filter(referrer=user)
        pending = referrals.filter(status='PENDING').count()
        qualified = referrals.filter(status='QUALIFIED').count()
        
        bonuses = ReferralBonus.objects.filter(
            user=user,
            status='CREDITED'
        )
        available_balance = bonuses.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Pending withdrawals
        pending_withdrawals = ReferralWithdrawal.objects.filter(
            user=user,
            status__in=['PENDING', 'APPROVED', 'PROCESSING']
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Total withdrawn
        total_withdrawn = ReferralWithdrawal.objects.filter(
            user=user,
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        stats = {
            'total_referred': link.total_referred,
            'total_bonus_earned': link.total_bonus_earned,
            'pending_referrals': pending,
            'qualified_referrals': qualified,
            'available_balance': available_balance,
            'pending_withdrawals': pending_withdrawals,
            'total_withdrawn': total_withdrawn,
            'referral_code': link.referral_code,
            'referral_url': f'/register?ref={link.referral_code}'
        }
        
        # Cache for 1 minute
        cache.set(cache_key, stats, 60)
        
        return Response(stats)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Admin action to approve a referral."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admins can approve referrals.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        referral = self.get_object()
        program = ReferralProgram.get_program()
        
        if program.status != 'ACTIVE':
            return Response(
                {'error': 'Referral program is not active.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        referral.status = 'BONUS_AWARDED'
        referral.referrer_bonus = program.referral_bonus_amount
        referral.referred_user_bonus = program.referred_user_bonus
        referral.bonus_awarded_at = timezone.now()
        referral.save()
        
        # Create bonus records
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
        
        # Update referral link
        referral.referrer.referral_link.total_referred += 1
        referral.referrer.referral_link.total_bonus_earned += program.referral_bonus_amount
        referral.referrer.referral_link.save()
        
        # Credit bonuses to users
        referral.referrer.add_balance(program.referral_bonus_amount)
        referral.referred_user.add_balance(program.referred_user_bonus)
        
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
        
        serializer = self.get_serializer(referral)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Admin action to reject a referral."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admins can reject referrals.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        referral = self.get_object()
        referral.status = 'REJECTED'
        referral.rejection_reason = request.data.get('reason', '')
        referral.save()
        
        serializer = self.get_serializer(referral)
        return Response(serializer.data)


class ReferralBonusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing referral bonuses.
    Users can view their own, admins can view all.
    """
    queryset = ReferralBonus.objects.all()
    serializer_class = ReferralBonusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by user unless admin."""
        # Handle schema generation (drf_yasg uses AnonymousUser)
        if getattr(self, 'swagger_fake_view', False):
            return ReferralBonus.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return ReferralBonus.objects.none()
        
        user = self.request.user
        if user.is_staff:
            return ReferralBonus.objects.all()
        return ReferralBonus.objects.filter(user=user)

    @action(detail=False, methods=['get'])
    def my_bonuses(self, request):
        """Get all bonuses for current user."""
        bonuses = ReferralBonus.objects.filter(user=request.user)
        serializer = self.get_serializer(bonuses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available (credited) bonuses for withdrawal."""
        bonuses = ReferralBonus.objects.filter(
            user=request.user,
            status='CREDITED'
        )
        total = bonuses.aggregate(Sum('amount'))['amount__sum'] or 0
        data = {
            'available_balance': total,
            'bonuses': self.get_serializer(bonuses, many=True).data
        }
        return Response(data)


class ReferralWithdrawalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing referral bonus withdrawals.
    Users can request withdrawals, admins can manage all.
    """
    queryset = ReferralWithdrawal.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return ReferralWithdrawalCreateSerializer
        elif self.request.user.is_staff:
            return ReferralWithdrawalAdminSerializer
        return ReferralWithdrawalSerializer

    def get_queryset(self):
        """Filter by user unless admin."""
        # Handle schema generation (drf_yasg uses AnonymousUser)
        if getattr(self, 'swagger_fake_view', False):
            return ReferralWithdrawal.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return ReferralWithdrawal.objects.none()
        
        user = self.request.user
        if user.is_staff:
            return ReferralWithdrawal.objects.all()
        return ReferralWithdrawal.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        """Create a withdrawal request."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Admin action to approve withdrawal."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admins can approve withdrawals.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        withdrawal = self.get_object()
        withdrawal.status = 'APPROVED'
        withdrawal.admin_notes = request.data.get('notes', '')
        withdrawal.processed_by = request.user
        withdrawal.processed_at = timezone.now()
        withdrawal.save()
        
        serializer = self.get_serializer(withdrawal)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Admin action to reject withdrawal."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admins can reject withdrawals.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        withdrawal = self.get_object()
        withdrawal.status = 'REJECTED'
        withdrawal.rejection_reason = request.data.get('reason', '')
        withdrawal.processed_by = request.user
        withdrawal.processed_at = timezone.now()
        withdrawal.save()
        
        serializer = self.get_serializer(withdrawal)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Admin action to mark withdrawal as completed."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admins can complete withdrawals.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        withdrawal = self.get_object()
        if withdrawal.status not in ['APPROVED', 'PROCESSING']:
            return Response(
                {'error': 'Withdrawal must be approved or processing.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        withdrawal.status = 'COMPLETED'
        withdrawal.processed_by = request.user
        withdrawal.processed_at = timezone.now()
        withdrawal.save()
        
        # Update bonus status if needed
        ReferralBonus.objects.filter(
            user=withdrawal.user,
            status='CREDITED',
            amount__lte=withdrawal.amount
        ).update(status='WITHDRAWN')
        
        serializer = self.get_serializer(withdrawal)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending withdrawals (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admins can view pending withdrawals.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        withdrawals = ReferralWithdrawal.objects.filter(
            status='PENDING'
        )
        serializer = self.get_serializer(withdrawals, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_withdrawals(self, request):
        """Get current user's withdrawals."""
        withdrawals = ReferralWithdrawal.objects.filter(user=request.user)
        serializer = self.get_serializer(withdrawals, many=True)
        return Response(serializer.data)
