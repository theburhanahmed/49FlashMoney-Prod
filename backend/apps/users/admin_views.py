"""
Admin-specific views for user management.
"""
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination

from apps.users.models import User, AuditLog
from apps.users.serializers import UserDetailSerializer
from apps.users.permissions import IsAdminUser


class AdminUserViewSet(viewsets.ModelViewSet):
    """Admin user management"""
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdminUser]
    pagination_class = PageNumberPagination
    page_size = 20
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Filtering
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        # Date filtering
        created_after = self.request.query_params.get('created_after')
        if created_after:
            queryset = queryset.filter(created_at__gte=created_after)
        
        created_before = self.request.query_params.get('created_before')
        if created_before:
            queryset = queryset.filter(created_at__lte=created_before)
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a user"""
        user = self.get_object()
        user.is_active = False
        user.save()
        
        return Response({
            'message': f'User {user.username} has been suspended',
            'user': UserDetailSerializer(user).data
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a user"""
        user = self.get_object()
        user.is_active = True
        user.save()
        
        return Response({
            'message': f'User {user.username} has been activated',
            'user': UserDetailSerializer(user).data
        })
    
    @action(detail=True, methods=['post'])
    def adjust_wallet(self, request, pk=None):
        """Manually adjust user wallet balance"""
        user = self.get_object()
        amount = request.data.get('amount')
        reason = request.data.get('reason', 'Manual adjustment')
        
        try:
            amount = float(amount)
            if amount > 0:
                user.add_balance(amount)
            else:
                user.deduct_balance(abs(amount))
            
            from apps.transactions.models import Transaction
            Transaction.objects.create(
                user=user,
                type='ADMIN_ADJUSTMENT',
                amount=abs(amount),
                status='COMPLETED',
                description=f'Admin adjustment: {reason}'
            )
            
            return Response({
                'message': f'Wallet adjusted by ${abs(amount)}',
                'new_balance': str(user.wallet_balance)
            })
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def kyc_review(self, request, pk=None):
        """Approve or reject a user's KYC submission (admin only)."""
        user = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ('VERIFIED', 'REJECTED'):
            return Response(
                {'error': 'status must be VERIFIED or REJECTED'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.kyc_status = new_status
        if new_status == 'VERIFIED':
            user.kyc_verified_at = timezone.now()
        user.save()
        AuditLog.objects.create(
            user=request.user,
            action='EMAIL_VERIFICATION',
            description=f'KYC {new_status.lower()} for user {user.username}'
        )
        return Response({
            'message': f'KYC {new_status.lower()}',
            'kyc_status': user.kyc_status,
            'kyc_verified_at': user.kyc_verified_at.isoformat() if user.kyc_verified_at else None,
        })

