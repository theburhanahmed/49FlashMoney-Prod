"""
GDPR compliance service for data export and deletion.
"""
import json
import csv
from io import StringIO
from django.utils import timezone
from django.db import transaction
import logging

from apps.users.models import User, UserProfile, AuditLog
from apps.lotteries.models import Ticket
from apps.transactions.models import Transaction, WithdrawalRequest, PaymentMethod
from apps.referrals.models import ReferralLink, Referral, ReferralBonus, ReferralWithdrawal

logger = logging.getLogger(__name__)


class GDPRService:
    """Service for GDPR compliance operations."""
    
    @staticmethod
    def export_user_data(user):
        """
        Export all user data in JSON format.
        
        Args:
            user: User instance
            
        Returns:
            dict: Complete user data
        """
        data = {
            'export_date': timezone.now().isoformat(),
            'user_id': str(user.id),
            'profile': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone_number': user.phone_number,
                'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
                'address': user.address,
                'city': user.city,
                'country': user.country,
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            },
            'user_profile': {},
            'tickets': [],
            'transactions': [],
            'withdrawals': [],
            'payment_methods': [],
            'referrals': {
                'referral_link': None,
                'referrals_made': [],
                'referrals_received': None,
                'bonuses': [],
                'withdrawals': [],
            },
            'audit_logs': [],
        }
        
        # User profile data
        profile, created = UserProfile.objects.get_or_create(user=user)
        data['user_profile'] = {
            'total_spent': str(profile.total_spent),
            'total_won': str(profile.total_won),
            'total_tickets_bought': profile.total_tickets_bought,
            'total_lotteries_participated': profile.total_lotteries_participated,
            'total_wins': profile.total_wins,
            'total_referrals': profile.total_referrals,
            'total_referral_earnings': str(profile.total_referral_earnings),
        }
        
        # Tickets
        tickets = Ticket.objects.filter(user=user)
        for ticket in tickets:
            data['tickets'].append({
                'id': str(ticket.id),
                'lottery_name': ticket.lottery.name,
                'ticket_number': ticket.ticket_number,
                'is_winner': ticket.is_winner,
                'purchased_at': ticket.purchased_at.isoformat(),
            })
        
        # Transactions
        transactions = Transaction.objects.filter(user=user)
        for trans in transactions:
            data['transactions'].append({
                'id': str(trans.id),
                'type': trans.type,
                'amount': str(trans.amount),
                'status': trans.status,
                'description': trans.description,
                'created_at': trans.created_at.isoformat(),
            })
        
        # Withdrawals
        withdrawals = WithdrawalRequest.objects.filter(user=user)
        for withdrawal in withdrawals:
            data['withdrawals'].append({
                'id': str(withdrawal.id),
                'amount': str(withdrawal.amount),
                'status': withdrawal.status,
                'requested_at': withdrawal.requested_at.isoformat(),
                'processed_at': withdrawal.processed_at.isoformat() if withdrawal.processed_at else None,
            })
        
        # Payment methods (anonymized)
        payment_methods = PaymentMethod.objects.filter(user=user)
        for pm in payment_methods:
            data['payment_methods'].append({
                'id': str(pm.id),
                'method_type': pm.method_type,
                'is_primary': pm.is_primary,
                'created_at': pm.created_at.isoformat(),
            })
        
        # Referral data
        try:
            referral_link = user.referral_link
            data['referrals']['referral_link'] = {
                'referral_code': referral_link.referral_code,
                'total_referred': referral_link.total_referred,
                'total_bonus_earned': str(referral_link.total_bonus_earned),
            }
        except ReferralLink.DoesNotExist:
            pass
        
        referrals_made = Referral.objects.filter(referrer=user)
        for ref in referrals_made:
            data['referrals']['referrals_made'].append({
                'id': str(ref.id),
                'status': ref.status,
                'created_at': ref.created_at.isoformat(),
            })
        
        try:
            referred_by = user.referred_by
            data['referrals']['referrals_received'] = {
                'id': str(referred_by.id),
                'status': referred_by.status,
            }
        except:
            pass
        
        bonuses = ReferralBonus.objects.filter(user=user)
        for bonus in bonuses:
            data['referrals']['bonuses'].append({
                'id': str(bonus.id),
                'amount': str(bonus.amount),
                'status': bonus.status,
                'created_at': bonus.created_at.isoformat(),
            })
        
        # Audit logs
        audit_logs = AuditLog.objects.filter(user=user)[:100]  # Limit to last 100
        for log in audit_logs:
            data['audit_logs'].append({
                'action': log.action,
                'description': log.description,
                'timestamp': log.timestamp.isoformat(),
            })
        
        return data
    
    @staticmethod
    def export_user_data_csv(user):
        """
        Export user data as CSV format.
        
        Args:
            user: User instance
            
        Returns:
            str: CSV formatted string
        """
        data = GDPRService.export_user_data(user)
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Field', 'Value'])
        writer.writerow(['User ID', data['user_id']])
        writer.writerow(['Username', data['profile']['username']])
        writer.writerow(['Email', data['profile']['email']])
        writer.writerow(['Created', data['profile']['created_at']])
        writer.writerow(['Total Tickets', data['user_profile'].get('total_tickets_bought', 0)])
        writer.writerow(['Total Spent', data['user_profile'].get('total_spent', '0')])
        writer.writerow(['Total Won', data['user_profile'].get('total_won', '0')])
        
        return output.getvalue()
    
    @staticmethod
    @transaction.atomic
    def delete_user_data(user):
        """
        Anonymize/delete user data according to GDPR requirements.
        This anonymizes rather than deleting to maintain referential integrity.
        
        Args:
            user: User instance
            
        Returns:
            bool: Success status
        """
        # Generate anonymized username and email
        anonymized_id = str(user.id)[:8]
        user.username = f'deleted_user_{anonymized_id}'
        user.email = f'deleted_{anonymized_id}@deleted.local'
        user.first_name = 'Deleted'
        user.last_name = 'User'
        user.phone_number = ''
        user.address = ''
        user.city = ''
        user.country = ''
        user.date_of_birth = None
        user.is_active = False
        user.save()
        
        # Anonymize profile
        try:
            profile = user.profile
            profile.bio = ''
            profile.save()
        except:
            pass
        
        # Delete or anonymize sensitive data
        # Note: We keep transaction records but could anonymize them further
        # Payment methods - delete sensitive data
        PaymentMethod.objects.filter(user=user).update(
            payment_details={}
        )
        
        logger.info(f'Anonymized user data for user {user.id}')
        return True

