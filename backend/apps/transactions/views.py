from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Sum, Q
from django.utils import timezone

from apps.transactions.models import Transaction, PaymentMethod, WithdrawalRequest
from apps.transactions.serializers import (
    TransactionSerializer, PaymentMethodSerializer,
    WithdrawalRequestSerializer
)
from apps.transactions.services import WithdrawalService
from apps.users.models import AuditLog
from apps.users.permissions import IsAdminUser
from apps.notifications.tasks import send_withdrawal_status_task as send_withdrawal_status_email


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """View user transactions"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['type', 'status']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimize queries with select_related"""
        # Handle schema generation (drf_yasg uses AnonymousUser)
        if getattr(self, 'swagger_fake_view', False):
            return Transaction.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return Transaction.objects.none()
        
        queryset = Transaction.objects.filter(
            user=self.request.user
        ).select_related('lottery', 'user')
        
        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transaction summary for current user"""
        transactions = Transaction.objects.filter(user=request.user)
        total_spent = transactions.filter(type='TICKET_PURCHASE').aggregate(
            total=Sum('amount')
        )['total'] or 0
        total_earned = transactions.filter(type='PRIZE_AWARD').aggregate(
            total=Sum('amount')
        )['total'] or 0
        total_deposits = transactions.filter(type='DEPOSIT').aggregate(
            total=Sum('amount')
        )['total'] or 0

        return Response({
            'total_transactions': transactions.count(),
            'total_spent': str(total_spent),
            'total_earned': str(total_earned),
            'total_deposits': str(total_deposits),
            'net_balance': str(float(total_earned) + float(total_deposits) - float(total_spent))
        })
    
    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        """Generate receipt for a transaction"""
        from django.http import HttpResponse
        from datetime import datetime
        
        transaction = self.get_object()
        
        # Generate simple text receipt (can be enhanced with PDF generation)
        receipt_content = f"""
TRANSACTION RECEIPT
===================

Transaction ID: {transaction.id}
Date: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Type: {transaction.get_type_display()}
Amount: ${transaction.amount}
Status: {transaction.get_status_display()}

Description: {transaction.description}

User: {transaction.user.username}
Email: {transaction.user.email}

---
This is an automated receipt.
        """.strip()
        
        response = HttpResponse(receipt_content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="receipt_{transaction.id}.txt"'
        return response


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """Manage payment methods"""
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-is_primary', '-created_at']

    def get_queryset(self):
        # Handle schema generation (drf_yasg uses AnonymousUser)
        if getattr(self, 'swagger_fake_view', False):
            return PaymentMethod.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return PaymentMethod.objects.none()
        
        return PaymentMethod.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Add new payment method"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            AuditLog.objects.create(
                user=request.user,
                action='DEPOSIT',
                description=f'Added payment method: {serializer.data["name"]}'
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set payment method as primary"""
        payment_method = self.get_object()
        PaymentMethod.objects.filter(user=request.user).update(is_primary=False)
        payment_method.is_primary = True
        payment_method.save()
        AuditLog.objects.create(
            user=request.user,
            action='WITHDRAW',
            description=f'Set primary payment method: {payment_method.name}'
        )
        return Response({'message': 'Payment method set as primary'})


class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    """Manage withdrawal requests"""
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-requested_at']

    def get_queryset(self):
        # Handle schema generation (drf_yasg uses AnonymousUser)
        if getattr(self, 'swagger_fake_view', False):
            return WithdrawalRequest.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return WithdrawalRequest.objects.none()
        
        return WithdrawalRequest.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Request withdrawal"""
        user = request.user
        amount = request.data.get('amount')
        payment_method_id = request.data.get('payment_method') or request.data.get('payment_method_id')
        bank_details = request.data.get('bank_details', {})
        remarks = request.data.get('remarks', '')

        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                return Response(
                    {'error': 'Amount must be greater than 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate withdrawal using service
        is_valid, error_message = WithdrawalService.validate_withdrawal_request(user, amount)
        if not is_valid:
            return Response(
                {'error': error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get payment method if provided
        payment_method = None
        if payment_method_id:
            try:
                payment_method = PaymentMethod.objects.get(
                    id=payment_method_id, user=user
                )
            except PaymentMethod.DoesNotExist:
                return Response(
                    {'error': 'Payment method not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Create withdrawal request
        withdrawal = WithdrawalRequest.objects.create(
            user=user,
            amount=amount,
            payment_method=payment_method,
            bank_details=bank_details,
            remarks=remarks,
            status='REQUESTED'
        )

        # Create transaction
        transaction = Transaction.objects.create(
            user=user,
            type='WITHDRAWAL',
            amount=amount,
            status='PENDING',
            description=f'Withdrawal request - {payment_method.method_type if payment_method else "Bank Transfer"}'
        )

        withdrawal.transaction = transaction
        withdrawal.save()

        # Log action
        AuditLog.objects.create(
            user=user,
            action='WITHDRAW',
            description=f'Withdrawal request for ${amount}'
        )

        # Send email notification
        send_withdrawal_status_email.delay(str(user.id), str(withdrawal.id), 'Withdrawal request submitted')

        return Response(
            WithdrawalRequestSerializer(withdrawal).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve withdrawal (admin only)"""
        withdrawal = self.get_object()

        if withdrawal.status != 'REQUESTED':
            return Response(
                {'error': 'Only requested withdrawals can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        admin_notes = request.data.get('admin_notes', '')

        # Deduct from user wallet
        withdrawal.user.deduct_balance(withdrawal.amount)

        # Update withdrawal
        withdrawal.status = 'APPROVED'
        withdrawal.processed_at = timezone.now()
        if admin_notes:
            withdrawal.remarks = f"{withdrawal.remarks}\nAdmin Notes: {admin_notes}" if withdrawal.remarks else f"Admin Notes: {admin_notes}"
        withdrawal.save()

        # Update transaction
        if withdrawal.transaction:
            withdrawal.transaction.status = 'COMPLETED'
            withdrawal.transaction.completed_at = timezone.now()
            withdrawal.transaction.save()

        # Log action
        AuditLog.objects.create(
            user=request.user,
            action='WITHDRAW',
            description=f'Approved withdrawal of ${withdrawal.amount} for {withdrawal.user.username}'
        )

        # Send email notification
        send_withdrawal_status_email.delay(str(withdrawal.user.id), str(withdrawal.id), 'Withdrawal approved')

        return Response({
            'message': 'Withdrawal approved',
            'withdrawal': WithdrawalRequestSerializer(withdrawal).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject withdrawal (admin only)"""
        withdrawal = self.get_object()

        if withdrawal.status != 'REQUESTED':
            return Response(
                {'error': 'Only requested withdrawals can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('rejection_reason', '')
        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update withdrawal
        withdrawal.status = 'REJECTED'
        withdrawal.processed_at = timezone.now()
        withdrawal.remarks = f"{withdrawal.remarks}\nRejection Reason: {rejection_reason}" if withdrawal.remarks else f"Rejection Reason: {rejection_reason}"
        withdrawal.save()

        # Update transaction
        if withdrawal.transaction:
            withdrawal.transaction.status = 'FAILED'
            withdrawal.transaction.save()

        # Log action
        AuditLog.objects.create(
            user=request.user,
            action='WITHDRAW',
            description=f'Rejected withdrawal of ${withdrawal.amount} for {withdrawal.user.username}. Reason: {rejection_reason}'
        )

        # Send email notification
        send_withdrawal_status_email.delay(str(withdrawal.user.id), str(withdrawal.id), f'Withdrawal rejected: {rejection_reason}')

        return Response({
            'message': 'Withdrawal rejected',
            'withdrawal': WithdrawalRequestSerializer(withdrawal).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def process(self, request, pk=None):
        """Mark withdrawal as processing or completed (admin only)"""
        withdrawal = self.get_object()
        new_status = request.data.get('status', 'PROCESSING')
        
        if new_status not in ['PROCESSING', 'COMPLETED']:
            return Response(
                {'error': 'Invalid status. Must be PROCESSING or COMPLETED'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if withdrawal.status not in ['APPROVED', 'PROCESSING']:
            return Response(
                {'error': 'Withdrawal must be approved or processing to update status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        withdrawal.status = new_status
        if new_status == 'COMPLETED':
            withdrawal.processed_at = timezone.now()
            if withdrawal.transaction:
                withdrawal.transaction.status = 'COMPLETED'
                withdrawal.transaction.completed_at = timezone.now()
                withdrawal.transaction.save()
        withdrawal.save()
        
        # Send email notification
        send_withdrawal_status_email.delay(str(withdrawal.user.id), str(withdrawal.id), f'Withdrawal status updated to {new_status}')
        
        return Response({
            'message': f'Withdrawal marked as {new_status}',
            'withdrawal': WithdrawalRequestSerializer(withdrawal).data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def admin_list(self, request):
        """List all withdrawals for admin with filters"""
        
        queryset = WithdrawalRequest.objects.all()
        
        # Filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Date range filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(requested_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(requested_at__lte=end_date)
        
        # Search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(id__icontains=search)
            )
        
        # Ordering
        queryset = queryset.order_by('-requested_at')
        
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def limits(self, request):
        """Get withdrawal limits for current user"""
        limits_info = WithdrawalService.check_withdrawal_limits(request.user, 0)
        return Response(limits_info['limits'])


class AdminTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin transaction management"""
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAdminUser]
    pagination_class = PageNumberPagination
    page_size = 20
    
    def get_queryset(self):
        """Optimize queries with select_related"""
        queryset = Transaction.objects.all().select_related('user', 'lottery', 'user__profile')
        
        # Filtering
        type_filter = self.request.query_params.get('type')
        if type_filter:
            queryset = queryset.filter(type=type_filter)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Process refund for a transaction"""
        transaction = self.get_object()
        
        if transaction.status != 'COMPLETED':
            return Response(
                {'error': 'Only completed transactions can be refunded'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'Admin refund')
        
        # Refund amount to user
        transaction.user.add_balance(transaction.amount)
        
        # Create refund transaction
        refund_transaction = Transaction.objects.create(
            user=transaction.user,
            type='REFUND',
            amount=transaction.amount,
            status='COMPLETED',
            description=f'Refund for transaction {transaction.id}: {reason}',
            reference_id=str(transaction.id)
        )
        
        # Log action
        from apps.users.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action='WITHDRAWAL',  # Reusing action
            description=f'Refunded transaction {transaction.id} for user {transaction.user.username}. Reason: {reason}'
        )
        
        return Response({
            'message': 'Refund processed successfully',
            'refund_transaction': TransactionSerializer(refund_transaction).data
        })
