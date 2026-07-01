from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from apps.common.throttling import SafeAnonRateThrottle
import logging

logger = logging.getLogger(__name__)
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils import timezone
from decimal import Decimal
from apps.notifications.services import EmailService
from apps.notifications.tasks import (
    send_welcome_email_task,
    send_email_verification_task,
    send_password_reset_task
)
from apps.users.models import User, UserProfile, AuditLog
from apps.users.serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    UserDetailSerializer, UserProfileSerializer,
    PasswordResetRequestSerializer, PasswordResetSerializer,
    EmailVerificationSerializer, ChangePasswordSerializer
)
from apps.users.permissions import IsSameUserOrAdmin


class RegisterThrottle(SafeAnonRateThrottle):
    """Custom throttle for registration: 100 requests per minute"""
    rate = '100/min'


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])  # Explicitly disable authentication
@throttle_classes([RegisterThrottle])
def register_view(request):
    """Handle user registration"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        AuditLog.objects.create(
            user=user,
            action='REGISTER',
            description='User registered',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        # Send welcome email asynchronously
        send_welcome_email_task.delay(str(user.id))
        return Response(
            {'message': 'User registered successfully'},
            status=status.HTTP_201_CREATED
        )
    else:
        # Log failed registration attempt
        AuditLog.objects.create(
            user=None,
            action='FAILED_REGISTER',
            description=f'Failed registration attempt: {str(serializer.errors)}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginThrottle(SafeAnonRateThrottle):
    """Custom throttle for login: 100 requests per minute"""
    rate = '100/min'


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])  # Explicitly disable authentication
@throttle_classes([LoginThrottle])
def login_view(request):
    """Handle user login"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        # Update last login info
        user.last_login_ip = get_client_ip(request)
        user.last_login_user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
        user.save(update_fields=['last_login_ip', 'last_login_user_agent'])
        
        AuditLog.objects.create(
            user=user,
            action='LOGIN',
            description='User logged in',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        # Generate token using simplejwt
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)
        
        return Response({
            'token': token,
            'user': UserDetailSerializer(user).data
        })
    else:
        # Log failed login attempt
        identifier = request.data.get('username') or request.data.get('email')
        if identifier:
            from django.db.models import Q
            try:
                user = User.objects.get(Q(username__iexact=identifier) | Q(email__iexact=identifier))
                AuditLog.objects.create(
                    user=user,
                    action='FAILED_LOGIN',
                    description='Failed login attempt',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )
            except User.DoesNotExist:
                # User doesn't exist, but we still want to log the attempt
                AuditLog.objects.create(
                    user=None,
                    action='FAILED_LOGIN',
                    description=f'Failed login attempt for non-existent user identifier: {identifier}',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetThrottle(AnonRateThrottle):
    """Custom throttle for password reset: 3 requests per hour"""
    rate = '3/hour'


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                if user.is_active:
                    # Generate password reset token
                    token = user.generate_password_reset_token()
                    
                    # Send password reset email asynchronously
                    send_password_reset_task.delay(str(user.id), token)
                    
                    # Create audit log
                    AuditLog.objects.create(
                        user=user,
                        action='PASSWORD_RESET_REQUEST',
                        description='Password reset request sent',
                        ip_address=get_client_ip(request)
                    )
            except User.DoesNotExist:
                # Don't reveal if email exists to prevent enumeration attacks
                pass
            
            # Always return success to prevent email enumeration
            return Response({'message': 'If an account with that email exists, a password reset link has been sent.'},
                          status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            new_password = serializer.validated_data['new_password']
            
            # Set new password
            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None
            user.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action='PASSWORD_RESET',
                description='Password reset successful',
                ip_address=get_client_ip(request)
            )
            
            return Response({'message': 'Password has been reset successfully'},
                          status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            
            user = request.user
            
            # Check if old password is correct
            if not user.check_password(old_password):
                return Response({'old_password': 'Incorrect password'},
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            # Create audit log
            AuditLog.objects.create(
                user=user,
                action='CHANGE_PASSWORD',
                description='Password changed',
                ip_address=get_client_ip(request)
            )
            
            return Response({'message': 'Password changed successfully'},
                          status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            try:
                user = User.objects.get(email_verification_token=token)
                
                # Verify email
                user.email_verified = True
                user.email_verification_token = None
                user.save()
                
                # Create audit log
                AuditLog.objects.create(
                    user=user,
                    action='EMAIL_VERIFICATION',
                    description='Email verified successfully',
                    ip_address=get_client_ip(request)
                )
                
                return Response({'message': 'Email verified successfully'},
                              status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'token': 'Invalid verification token'},
                              status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'email': 'Email is required'},
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            if user.email_verified:
                return Response({'message': 'Email is already verified'},
                              status=status.HTTP_200_OK)
            
            # Generate new verification token
            token = user.generate_verification_token()
            
            # Send verification email asynchronously
            send_email_verification_task.delay(str(user.id))
            
            return Response({'message': 'Verification email sent successfully'},
                          status=status.HTTP_200_OK)
        except User.DoesNotExist:
            # Don't reveal if email exists
            return Response({'message': 'If an account with that email exists, verification email has been sent'},
                          status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """Manage user accounts"""
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            # Only admin users can update or delete other users
            permission_classes = [IsSameUserOrAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        # Handle schema generation (drf_yasg uses AnonymousUser)
        if getattr(self, 'swagger_fake_view', False):
            return User.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return User.objects.none()
        
        # Admin users can see all users, regular users can only see themselves
        if self.request.user.is_admin or self.request.user.role in ['admin', 'moderator']:
            return User.objects.all()
        else:
            # Regular users can only see their own profile
            return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user profile"""
        user = request.user
        serializer = UserDetailSerializer(user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """Get dashboard summary with stats and recent activity"""
        from apps.transactions.models import Transaction
        from apps.lotteries.models import Ticket, Lottery
        from apps.referrals.models import ReferralBonus
        from django.db.models import Sum, Count, Q
        from django.core.cache import cache
        from apps.common.cache import CacheKeys
        
        user = request.user
        
        # Try to get from cache
        cache_key = CacheKeys.user_dashboard(user.id)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return Response(cached_result)
        
        # User statistics
        from apps.users.models import UserProfile
        profile, created = UserProfile.objects.get_or_create(user=user)
        stats = {
            'tickets_bought': profile.total_tickets_bought,
            'total_spent': str(profile.total_spent),
            'total_won': str(profile.total_won),
            'total_wins': profile.total_wins,
            'total_lotteries_participated': profile.total_lotteries_participated,
        }
        
        # Recent transactions (last 5) - optimized with select_related
        recent_transactions = Transaction.objects.filter(
            user=user
        ).select_related('lottery').order_by('-created_at')[:5]
        transactions_data = []
        for trans in recent_transactions:
            transactions_data.append({
                'id': str(trans.id),
                'type': trans.type,
                'amount': str(trans.amount),
                'status': trans.status,
                'description': trans.description,
                'created_at': trans.created_at.isoformat(),
                'lottery_name': trans.lottery.name if trans.lottery else None,
            })
        
        # Recent tickets (last 5)
        recent_tickets = Ticket.objects.filter(user=user).select_related('lottery').order_by('-purchased_at')[:5]
        tickets_data = []
        for ticket in recent_tickets:
            tickets_data.append({
                'id': str(ticket.id),
                'lottery_name': ticket.lottery.name,
                'ticket_number': ticket.ticket_number,
                'is_winner': ticket.is_winner,
                'lottery_status': ticket.lottery.status,
                'purchased_at': ticket.purchased_at.isoformat(),
            })
        
        # Referral bonus balance
        referral_balance = Decimal('0.00')
        try:
            bonuses = ReferralBonus.objects.filter(
                user=user,
                status='CREDITED'
            ).aggregate(total=Sum('amount'))
            referral_balance = bonuses['total'] or Decimal('0.00')
        except:
            pass
        
        # Pending withdrawals count
        from apps.transactions.models import WithdrawalRequest
        pending_withdrawals = WithdrawalRequest.objects.filter(
            user=user,
            status='REQUESTED'
        ).count()
        
        from apps.wallet.services import WalletService
        wallet = WalletService.get_or_create_wallet(user)
        response_data = {
            'wallet_balance': str(wallet.balance),
            'stats': stats,
            'recent_transactions': transactions_data,
            'recent_tickets': tickets_data,
            'referral_bonus_balance': str(referral_balance),
            'pending_withdrawals': pending_withdrawals,
        }
        
        # Cache the result for 1 minute
        cache.set(cache_key, response_data, 60)
        
        return Response(response_data)

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """Update current user profile"""
        user = request.user
        serializer = UserDetailSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def wallet(self, request):
        """Get user wallet balance from the ledger-backed Wallet model."""
        from apps.wallet.services import WalletService
        user = request.user
        wallet = WalletService.get_or_create_wallet(user)
        return Response({
            'wallet_balance': str(wallet.balance),
            'user_id': str(user.id)
        })

    @action(detail=False, methods=['post'])
    def add_funds(self, request):
        """Add funds to user wallet via Stripe payment intent"""
        from apps.users.responsible_gaming import ResponsibleGamingService
        from apps.payments.services import StripeService
        
        user = request.user
        
        # Check self-exclusion
        is_excluded, exclusion_reason = ResponsibleGamingService.check_self_exclusion(user)
        if is_excluded:
            return Response(
                {'error': exclusion_reason},
                status=status.HTTP_403_FORBIDDEN
            )
        
        amount = request.data.get('amount', 0)
        payment_method_id = request.data.get('payment_method_id')
        save_payment_method = request.data.get('save_payment_method', False)
        
        try:
            amount = float(amount)
            if amount <= 0:
                return Response(
                    {'error': 'Amount must be greater than 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check deposit limits
            is_valid, error_message = ResponsibleGamingService.check_deposit_limit(user, amount)
            if not is_valid:
                return Response(
                    {'error': error_message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create Stripe payment intent
            try:
                payment_intent = StripeService.create_payment_intent(
                    amount=amount,
                    user=user,
                    payment_method_id=payment_method_id,
                    save_payment_method=save_payment_method
                )
                
                AuditLog.objects.create(
                    user=user,
                    action='DEPOSIT',
                    description=f'Created payment intent for ${amount}'
                )
                
                return Response({
                    'message': 'Payment intent created successfully',
                    'payment_intent_id': payment_intent.stripe_payment_intent_id,
                    'client_secret': payment_intent.client_secret,
                    'amount': str(amount),
                    'currency': payment_intent.currency
                })
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating payment intent: {e}")
                return Response(
                    {'error': 'Failed to create payment intent. Please try again.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except ValueError:
            return Response(
                {'error': 'Invalid amount'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get user transactions"""
        from apps.transactions.models import Transaction
        from apps.transactions.serializers import TransactionSerializer
        transactions = Transaction.objects.filter(user=request.user)
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Handle user logout"""
        user = request.user
        AuditLog.objects.create(
            user=user,
            action='LOGOUT',
            description='User logged out'
        )
        return Response({'message': 'Logged out successfully'})

    @action(detail=False, methods=['post'], url_path='refresh-token')
    def refresh_token(self, request):
        """Refresh JWT token. Exposed as .../users/refresh-token/ for frontend compatibility."""
        from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
            return Response({'access': new_access_token})
        except Exception as e:
            return Response(
                {'error': 'Invalid refresh token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def token_verify(self, request):
        """Verify JWT token"""
        from rest_framework_simplejwt.tokens import AccessToken
        try:
            token = request.data.get('token')
            if not token:
                return Response(
                    {'error': 'Token is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            AccessToken(token)
            return Response({'valid': True})
        except Exception as e:
            return Response(
                {'valid': False, 'error': str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

    @action(detail=True, methods=['patch'], permission_classes=[IsSameUserOrAdmin])
    def update_role(self, request, pk=None):
        """Update user role (admin only)"""
        if not (request.user.is_admin or request.user.role in ['admin', 'moderator']):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in ['user', 'admin', 'moderator']:
            return Response(
                {'error': 'Invalid role'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_role = user.role
        user.role = new_role
        user.is_admin = (new_role == 'admin')
        user.save()
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='CHANGE_ROLE',
            description=f'Changed user {user.username} role from {old_role} to {new_role}',
            ip_address=get_client_ip(request)
        )
        
        return Response({'message': 'Role updated successfully', 'user': UserDetailSerializer(user).data})

    @action(detail=True, methods=['post'], permission_classes=[IsSameUserOrAdmin])
    def toggle_user_status(self, request, pk=None):
        """Toggle user active status (admin only)"""
        if not (request.user.is_admin or request.user.role in ['admin', 'moderator']):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        status_str = 'activated' if user.is_active else 'deactivated'
        
        # Create audit log
        AuditLog.objects.create(
            user=request.user,
            action='TOGGLE_USER_STATUS',
            description=f'{status_str.capitalize()} user {user.username}',
            ip_address=get_client_ip(request)
        )
        
        return Response({'message': f'User {status_str} successfully', 'is_active': user.is_active})
    
    @action(detail=False, methods=['post'])
    def verify_age(self, request):
        """Verify age for current user"""
        user = request.user
        date_of_birth = request.data.get('date_of_birth')
        
        if not date_of_birth:
            return Response(
                {'error': 'Date of birth is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from datetime import date
            dob = date.fromisoformat(str(date_of_birth))
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 18:
                return Response(
                    {'error': 'You must be at least 18 years old'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.date_of_birth = dob
            user.age_verified = True
            user.age_verified_at = timezone.now()
            user.save()
            
            AuditLog.objects.create(
                user=user,
                action='EMAIL_VERIFICATION',  # Reusing action type
                description='Age verified'
            )
            
            return Response({
                'message': 'Age verified successfully',
                'age_verified': True
            })
        except (ValueError, TypeError) as e:
            return Response(
                {'error': 'Invalid date format'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def self_exclude(self, request):
        """Request self-exclusion"""
        from apps.users.responsible_gaming import ResponsibleGamingService
        
        user = request.user
        days = request.data.get('days')  # None for permanent
        
        if days is not None:
            try:
                days = int(days)
                if days < 1:
                    return Response(
                        {'error': 'Days must be at least 1'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid days value'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        ResponsibleGamingService.apply_self_exclusion(user, days)
        
        AuditLog.objects.create(
            user=user,
            action='ACCOUNT_LOCKED',  # Reusing action type
            description=f'Self-exclusion requested for {days} days' if days else 'Permanent self-exclusion requested'
        )
        
        return Response({
            'message': f'Self-exclusion applied for {days} days' if days else 'Permanent self-exclusion applied',
            'self_excluded': True,
            'self_exclusion_until': user.self_exclusion_until.isoformat() if user.self_exclusion_until else None
        })
    
    @action(detail=False, methods=['post'])
    def set_deposit_limits(self, request):
        """Set deposit limits"""
        user = request.user
        
        daily_limit = request.data.get('daily_deposit_limit')
        weekly_limit = request.data.get('weekly_deposit_limit')
        monthly_limit = request.data.get('monthly_deposit_limit')
        
        if daily_limit is not None:
            try:
                user.daily_deposit_limit = float(daily_limit)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid daily_deposit_limit'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if weekly_limit is not None:
            try:
                user.weekly_deposit_limit = float(weekly_limit)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid weekly_deposit_limit'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if monthly_limit is not None:
            try:
                user.monthly_deposit_limit = float(monthly_limit)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid monthly_deposit_limit'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        user.save()
        
        return Response({
            'message': 'Deposit limits updated',
            'daily_deposit_limit': str(user.daily_deposit_limit) if user.daily_deposit_limit else None,
            'weekly_deposit_limit': str(user.weekly_deposit_limit) if user.weekly_deposit_limit else None,
            'monthly_deposit_limit': str(user.monthly_deposit_limit) if user.monthly_deposit_limit else None,
        })
    
    @action(detail=False, methods=['post'])
    def submit_kyc(self, request):
        """Submit KYC documents"""
        user = request.user
        
        id_document = request.FILES.get('id_document')
        address_proof = request.FILES.get('address_proof')
        
        if not id_document and not address_proof:
            return Response(
                {'error': 'At least one document (ID or address proof) is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if id_document:
            user.id_document = id_document
        if address_proof:
            user.address_proof = address_proof
        
        user.kyc_status = 'PENDING'
        user.kyc_submitted_at = timezone.now()
        user.save()
        
        AuditLog.objects.create(
            user=user,
            action='EMAIL_VERIFICATION',  # Reusing action type
            description='KYC documents submitted'
        )
        
        return Response({
            'message': 'KYC documents submitted successfully',
            'kyc_status': user.kyc_status
        })
    
    @action(detail=False, methods=['get'])
    def kyc_status(self, request):
        """Get KYC status"""
        user = request.user
        return Response({
            'kyc_status': user.kyc_status,
            'kyc_submitted_at': user.kyc_submitted_at.isoformat() if user.kyc_submitted_at else None,
            'kyc_verified_at': user.kyc_verified_at.isoformat() if user.kyc_verified_at else None,
        })
    
    @action(detail=False, methods=['get'])
    def data_export(self, request):
        """Export user data (GDPR)"""
        from apps.users.gdpr import GDPRService
        
        user = request.user
        format_type = request.query_params.get('format', 'json')
        
        if format_type == 'csv':
            csv_data = GDPRService.export_user_data_csv(user)
            from django.http import HttpResponse
            response = HttpResponse(csv_data, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="user_data_{user.id}.csv"'
            return response
        else:
            data = GDPRService.export_user_data(user)
            return Response(data)
    
    @action(detail=False, methods=['post'])
    def delete_account(self, request):
        """Request account deletion (GDPR)"""
        from apps.users.gdpr import GDPRService
        
        user = request.user
        confirmation = request.data.get('confirmation')
        
        if confirmation != 'DELETE':
            return Response(
                {'error': 'Account deletion requires confirmation. Send confirmation: "DELETE"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        GDPRService.delete_user_data(user)
        
        AuditLog.objects.create(
            user=user,
            action='ACCOUNT_LOCKED',
            description='Account deleted (GDPR request)'
        )
        
        return Response({
            'message': 'Account data has been anonymized and deleted'
        })
    
    @action(detail=False, methods=['get'])
    def responsible_gaming_status(self, request):
        """Get responsible gaming status and limits"""
        from apps.users.responsible_gaming import ResponsibleGamingService
        
        user = request.user
        is_excluded, exclusion_reason = ResponsibleGamingService.check_self_exclusion(user)
        is_valid, error_msg, minutes_remaining = ResponsibleGamingService.check_session_time(user)
        
        return Response({
            'self_excluded': is_excluded,
            'exclusion_reason': exclusion_reason,
            'self_exclusion_until': user.self_exclusion_until.isoformat() if user.self_exclusion_until else None,
            'daily_deposit_limit': str(user.daily_deposit_limit) if user.daily_deposit_limit else None,
            'weekly_deposit_limit': str(user.weekly_deposit_limit) if user.weekly_deposit_limit else None,
            'monthly_deposit_limit': str(user.monthly_deposit_limit) if user.monthly_deposit_limit else None,
            'daily_loss_limit': str(user.daily_loss_limit) if user.daily_loss_limit else None,
            'session_time_limit': user.session_time_limit,
            'session_time_remaining': minutes_remaining,
            'last_session_start': user.last_session_start.isoformat() if user.last_session_start else None,
        })


class Setup2FAView(APIView):
    """Setup 2FA for user."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Generate 2FA secret and QR code."""
        from apps.users.otp import generate_totp_secret, generate_totp_uri, generate_qr_code
        
        user = request.user
        
        if user.is_2fa_enabled:
            return Response(
                {'error': '2FA is already enabled. Disable it first to set up a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate secret
        secret = generate_totp_secret()
        user.two_factor_secret = secret
        user.save()
        
        # Generate QR code
        uri = generate_totp_uri(user, secret)
        qr_code = generate_qr_code(uri)
        
        return Response({
            'secret': secret,
            'qr_code': qr_code,
            'message': 'Scan the QR code with your authenticator app'
        })


class Verify2FASetupView(APIView):
    """Verify 2FA setup with token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Verify 2FA token and enable 2FA."""
        from apps.users.otp import verify_totp, generate_backup_codes
        
        user = request.user
        token = request.data.get('token')
        
        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.two_factor_secret:
            return Response(
                {'error': '2FA setup not initiated. Please set up 2FA first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify token
        if not verify_totp(user.two_factor_secret, token):
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate backup codes
        backup_codes = generate_backup_codes()
        user.two_factor_backup_codes = backup_codes
        user.is_2fa_enabled = True
        user.save()
        
        return Response({
            'message': '2FA enabled successfully',
            'backup_codes': backup_codes,
            'warning': 'Save these backup codes in a safe place. You will need them if you lose access to your authenticator app.'
        })


class Disable2FAView(APIView):
    """Disable 2FA for user."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Disable 2FA."""
        user = request.user
        
        if not user.is_2fa_enabled:
            return Response(
                {'error': '2FA is not enabled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_2fa_enabled = False
        user.two_factor_secret = None
        user.two_factor_backup_codes = []
        user.save()
        
        return Response({'message': '2FA disabled successfully'})