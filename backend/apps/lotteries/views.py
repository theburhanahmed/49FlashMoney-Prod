from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count
from django.core.cache import cache
from django.core.exceptions import ValidationError
from apps.common.cache import CacheKeys
import random
import secrets

from apps.lotteries.models import Lottery, Ticket, Winner, LotteryDrawLog
from apps.lotteries.serializers import (
    LotterySerializer, TicketSerializer, WinnerSerializer,
    LotteryDrawLogSerializer
)
from apps.transactions.models import Transaction
from apps.users.models import AuditLog, UserProfile, User
from apps.notifications.tasks import (
    send_ticket_purchase_confirmation_task,
    send_draw_result_win_task,
    send_draw_result_loss_task
)


class LotteryViewSet(viewsets.ModelViewSet):
    """Manage lottery operations"""
    queryset = Lottery.objects.all()
    serializer_class = LotterySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'draw_date']
    ordering = ['-created_at']

    def get_queryset(self):
        """Optimize queries with select_related and prefetch_related"""
        queryset = Lottery.objects.select_related('created_by').prefetch_related('ticket_set', 'winners')
        return queryset

    def _validate_image(self, image_file):
        """Validate uploaded image file."""
        if not image_file:
            return None, None
        
        # Check file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB
        if image_file.size > max_size:
            return None, {'image': ['Image file size exceeds 5MB limit.']}
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if image_file.content_type not in allowed_types:
            return None, {'image': ['Invalid image format. Allowed formats: JPEG, PNG, WebP.']}
        
        # Check file extension as additional validation
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        file_name = image_file.name.lower()
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            return None, {'image': ['Invalid file extension. Allowed: .jpg, .jpeg, .png, .webp']}
        
        return image_file, None

    def create(self, request, *args, **kwargs):
        """Create new lottery (admin only)"""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can create lotteries'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate image if provided
        image_file = request.FILES.get('image')
        if image_file:
            validated_image, image_errors = self._validate_image(image_file)
            if image_errors:
                return Response(image_errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create a mutable copy of request.data for file handling
        data = request.data.copy()
        if image_file:
            data['image'] = validated_image
        
        serializer = self.get_serializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            AuditLog.objects.create(
                user=request.user,
                action='BUY_TICKET',
                description=f'Created lottery: {serializer.data["name"]}'
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update lottery (admin only)"""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can update lotteries'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate image if provided
        image_file = request.FILES.get('image')
        if image_file:
            validated_image, image_errors = self._validate_image(image_file)
            if image_errors:
                return Response(image_errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create a mutable copy of request.data for file handling
        data = request.data.copy()
        if image_file:
            data['image'] = validated_image
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=data, partial=partial, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Delete lottery (admin only)"""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can delete lotteries'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def buy_ticket(self, request, pk=None):
        """Purchase a lottery ticket via TicketPurchaseService (ledger-backed)."""
        from apps.users.responsible_gaming import ResponsibleGamingService
        from apps.lotteries.services import TicketPurchaseService
        from apps.common.exceptions import LotteryError

        lottery = self.get_object()

        # Responsible gaming checks (view-level policy, not business logic)
        is_excluded, exclusion_reason = ResponsibleGamingService.check_self_exclusion(request.user)
        if is_excluded:
            return Response(
                {'error': exclusion_reason},
                status=status.HTTP_403_FORBIDDEN
            )

        is_valid, error_msg, _mins = ResponsibleGamingService.check_session_time(request.user)
        if not is_valid:
            return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)

        is_valid, error_message = ResponsibleGamingService.check_loss_limit(request.user, lottery.ticket_price)
        if not is_valid:
            return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)

        # Update session start if not set
        if not request.user.last_session_start:
            request.user.last_session_start = timezone.now()
            request.user.save(update_fields=['last_session_start'])

        # Delegate to service (atomic, ledger-backed, idempotent)
        try:
            tickets = TicketPurchaseService.purchase_ticket(request.user, lottery, quantity=1)
        except LotteryError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        ticket = tickets[0]

        # Fire-and-forget email notification
        try:
            send_ticket_purchase_confirmation_task.delay(
                str(request.user.id),
                str(ticket.id),
                str(lottery.id)
            )
        except Exception:
            pass  # Email failure should not block purchase

        return Response(
            {
                'message': 'Ticket purchased successfully',
                'ticket': TicketSerializer(ticket).data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """Get lottery results"""
        lottery = self.get_object()
        
        # Cache lottery results
        cache_key = CacheKeys.lottery_detail(lottery.id) + '_results'
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return Response(cached_result)
        
        winners = Winner.objects.filter(lottery=lottery).select_related('user', 'ticket')
        serializer = WinnerSerializer(winners, many=True)
        result = {
            'lottery': LotterySerializer(lottery).data,
            'winners': serializer.data,
            'total_winners': winners.count()
        }
        
        # Cache for 2 minutes
        cache.set(cache_key, result, 120)
        
        return Response(result)

    @action(detail=True, methods=['get'])
    def winner(self, request, pk=None):
        """Get lottery winner"""
        lottery = self.get_object()
        try:
            winner = Winner.objects.select_related('user', 'ticket').get(lottery=lottery)
            return Response(WinnerSerializer(winner).data)
        except Winner.DoesNotExist:
            return Response(
                {'error': 'No winner yet for this lottery'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def draw(self, request, pk=None):
        """Conduct lottery draw (admin only)"""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can conduct draws'},
                status=status.HTTP_403_FORBIDDEN
            )

        lottery = self.get_object()

        # Validation
        if lottery.status != 'CLOSED':
            return Response(
                {'error': 'Lottery must be closed to conduct draw'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if lottery.draw_date > timezone.now():
            return Response(
                {'error': 'Draw date has not been reached yet'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get all tickets
        tickets = Ticket.objects.filter(lottery=lottery)
        if not tickets.exists():
            return Response(
                {'error': 'No tickets purchased for this lottery'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Select random winner
        random_seed = secrets.token_hex(16)
        random.seed(random_seed)
        winning_ticket = random.choice(list(tickets))

        # Create winner record
        winner = Winner.objects.create(
            user=winning_ticket.user,
            lottery=lottery,
            ticket=winning_ticket,
            prize_amount=lottery.prize_amount
        )

        winning_ticket.is_winner = True
        winning_ticket.save()

        # Create draw log
        LotteryDrawLog.objects.create(
            lottery=lottery,
            conducted_by=request.user,
            total_participants=lottery.get_total_participants(),
            total_tickets_sold=lottery.get_total_tickets_sold(),
            revenue=lottery.get_revenue(),
            random_seed=random_seed
        )

        # Update lottery status
        lottery.status = 'DRAWN'
        lottery.save()

        # Update user profile
        profile, _ = UserProfile.objects.get_or_create(user=winner.user)
        profile.total_won += float(lottery.prize_amount)
        profile.total_wins += 1
        profile.save()

        # Log action
        AuditLog.objects.create(
            user=request.user,
            action='WIN',
            description=f'Lottery draw conducted for {lottery.name}. Winner: {winner.user.username}'
        )

        # Send draw result emails asynchronously
        # Send win email to winner
        send_draw_result_win_task.delay(
            str(winner.user.id),
            str(winner.id),
            str(lottery.id)
        )

        # Send loss emails to all other participants
        losing_tickets = tickets.exclude(id=winning_ticket.id)
        for ticket in losing_tickets:
            send_draw_result_loss_task.delay(
                str(ticket.user.id),
                str(lottery.id)
            )

        return Response(
            {
                'message': 'Draw conducted successfully',
                'winner': WinnerSerializer(winner).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def my_tickets(self, request, pk=None):
        """Get user's tickets for this lottery"""
        lottery = self.get_object()
        tickets = Ticket.objects.filter(user=request.user, lottery=lottery)
        serializer = TicketSerializer(tickets, many=True)
        return Response({
            'lottery': LotterySerializer(lottery).data,
            'tickets': serializer.data,
            'count': tickets.count()
        })

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def participants(self, request, pk=None):
        """Get lottery participants (admin only)"""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can view participants'},
                status=status.HTTP_403_FORBIDDEN
            )

        lottery = self.get_object()
        participants = Ticket.objects.filter(lottery=lottery).values('user').distinct().count()
        return Response({
            'lottery': LotterySerializer(lottery).data,
            'total_participants': participants,
            'total_tickets': Ticket.objects.filter(lottery=lottery).count()
        })

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def stats(self, request, pk=None):
        """Get lottery statistics"""
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can view stats'},
                status=status.HTTP_403_FORBIDDEN
            )

        lottery = self.get_object()
        return Response({
            'lottery': LotterySerializer(lottery).data,
            'total_participants': lottery.get_total_participants(),
            'total_tickets_sold': lottery.get_total_tickets_sold(),
            'total_tickets_remaining': lottery.available_tickets,
            'revenue': str(lottery.get_revenue()),
            'revenue_percentage': f"{(lottery.get_total_tickets_sold() / lottery.total_tickets * 100) if lottery.total_tickets > 0 else 0:.2f}%"
        })


class TicketViewSet(viewsets.ReadOnlyModelViewSet):
    """View user tickets"""
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-purchased_at']
    filterset_fields = ['lottery', 'is_winner']

    def get_queryset(self):
        # Handle schema generation (drf_yasg uses AnonymousUser)
        if getattr(self, 'swagger_fake_view', False):
            return Ticket.objects.none()
        
        # Check if user is authenticated
        if not self.request.user.is_authenticated:
            return Ticket.objects.none()
        
        queryset = Ticket.objects.filter(user=self.request.user).select_related('lottery')
        
        # Filter by lottery status
        lottery_status = self.request.query_params.get('lottery_status')
        if lottery_status:
            queryset = queryset.filter(lottery__status=lottery_status)
        
        # Filter by winning status
        is_winner = self.request.query_params.get('is_winner')
        if is_winner is not None:
            queryset = queryset.filter(is_winner=is_winner.lower() == 'true')
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        """Get all user tickets with enhanced filtering"""
        queryset = self.get_queryset()
        
        # Filter by lottery name (search)
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(lottery__name__icontains=search)
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Add lottery information to each ticket
        tickets_data = []
        for ticket in queryset:
            ticket_data = serializer.data[queryset.index(ticket)] if queryset else {}
            ticket_data['lottery'] = {
                'id': str(ticket.lottery.id),
                'name': ticket.lottery.name,
                'status': ticket.lottery.status,
                'draw_date': ticket.lottery.draw_date.isoformat() if ticket.lottery.draw_date else None,
            }
            tickets_data.append(ticket_data)
        
        return Response({
            'tickets': tickets_data,
            'count': queryset.count(),
            'winning_count': queryset.filter(is_winner=True).count(),
        })
