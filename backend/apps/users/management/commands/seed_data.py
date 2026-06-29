from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.users.models import UserProfile, AuditLog
from apps.lotteries.models import Lottery, Ticket, Winner, LotteryDrawLog
from apps.transactions.models import Transaction, PaymentMethod, WithdrawalRequest
from apps.referrals.models import ReferralProgram, ReferralLink, Referral, ReferralBonus
from django.core.validators import MinValueValidator
import random
from datetime import datetime, timedelta
import uuid


class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        AuditLog.objects.all().delete()
        ReferralBonus.objects.all().delete()
        Referral.objects.all().delete()
        ReferralLink.objects.all().delete()
        ReferralProgram.objects.all().delete()
        Winner.objects.all().delete()
        Ticket.objects.all().delete()
        LotteryDrawLog.objects.all().delete()
        Lottery.objects.all().delete()
        WithdrawalRequest.objects.all().delete()
        Transaction.objects.all().delete()
        PaymentMethod.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.exclude(username='admin').delete()  # Keep admin user
        
        # Create sample users
        self.stdout.write('Creating sample users...')
        
        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@lottery.com',
                'is_admin': True,
                'is_staff': True,
                'is_superuser': True,
                'role': 'admin',
                'wallet_balance': 1000.00
            }
        )
        if created:
            admin_user.set_password('Admin123!')
            admin_user.save()
        else:
            # Update existing admin user to ensure proper role and permissions
            admin_user.is_admin = True
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.role = 'admin'
            admin_user.email = 'admin@lottery.com'
            admin_user.save()
        
        # Create regular users
        users_data = [
            {'username': 'john_doe', 'email': 'john@example.com', 'wallet_balance': 500.00},
            {'username': 'jane_smith', 'email': 'jane@example.com', 'wallet_balance': 250.00},
            {'username': 'bob_wilson', 'email': 'bob@example.com', 'wallet_balance': 750.00},
            {'username': 'alice_brown', 'email': 'alice@example.com', 'wallet_balance': 100.00},
            {'username': 'charlie_davis', 'email': 'charlie@example.com', 'wallet_balance': 300.00},
        ]
        
        users = [admin_user]
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'wallet_balance': user_data['wallet_balance'],
                    'is_active': True
                }
            )
            if created:
                user.set_password('Password123!')
                user.save()
            users.append(user)
        
        # Create user profiles
        self.stdout.write('Creating user profiles...')
        for user in users:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'total_spent': random.randint(0, 1000),
                    'total_won': random.randint(0, 500),
                    'total_tickets_bought': random.randint(0, 20),
                    'total_lotteries_participated': random.randint(0, 10),
                    'total_wins': random.randint(0, 5),
                    'bio': f"Profile for {user.username}",
                    'preferences': {'theme': 'light', 'notifications': True}
                }
            )
        
        # Create referral program
        self.stdout.write('Creating referral program...')
        referral_program, created = ReferralProgram.objects.get_or_create(
            id=1,
            defaults={
                'status': 'ACTIVE',
                'referral_bonus_amount': 50.00,
                'referred_user_bonus': 25.00,
                'minimum_referral_deposit': 10.00,
                'bonus_expiry_days': 30,
                'min_referral_balance_to_withdraw': 100.00,
                'max_withdrawals_per_month': 12
            }
        )
        
        # Create referral links and referrals
        self.stdout.write('Creating referral links and referrals...')
        for i, user in enumerate(users[1:4]):  # Skip admin and last user
            referral_link, created = ReferralLink.objects.get_or_create(
                user=user,
                defaults={
                    'referral_code': f'REF{user.username[:3].upper()}{i+1:03d}',
                    'total_referred': random.randint(0, 10),
                    'total_bonus_earned': random.randint(0, 200)
                }
            )
        
        # Create some referrals
        if len(users) > 2:
            referrer = users[1]  # john_doe
            referred = users[2]  # jane_smith
            
            referral, created = Referral.objects.get_or_create(
                referrer=referrer,
                referred_user=referred,
                defaults={
                    'status': 'BONUS_AWARDED',
                    'referrer_bonus': 50.00,
                    'referred_user_bonus': 25.00,
                    'bonus_awarded_at': timezone.now(),
                    'referred_user_deposit': 50.00,
                    'deposit_date': timezone.now() - timedelta(days=5)
                }
            )
        
        # Create payment methods
        self.stdout.write('Creating payment methods...')
        for user in users:
            for i in range(random.randint(1, 3)):
                PaymentMethod.objects.get_or_create(
                    user=user,
                    method_type=random.choice(['CREDIT_CARD', 'DEBIT_CARD', 'DIGITAL_WALLET', 'NET_BANKING'])[0:2],
                    defaults={
                        'is_primary': i == 0,
                        'is_active': True,
                        'payment_details': {
                            'card_last_four': str(random.randint(1000, 9999)),
                            'expiry_month': str(random.randint(1, 12)),
                            'expiry_year': str(random.randint(24, 28)),
                            'holder_name': user.username
                        }
                    }
                )
        
        # Create lotteries
        self.stdout.write('Creating lotteries...')
        lottery_names = [
            "Weekly Jackpot",
            "Lucky Numbers",
            "Golden Draw",
            "Millionaire Dreams",
            "Lucky Stars"
        ]
        
        for i, name in enumerate(lottery_names):
            lottery = Lottery.objects.create(
                name=name,
                description=f"Exciting lottery event: {name}. Win big with your lucky numbers!",
                ticket_price=10.00,
                total_tickets=1000,
                available_tickets=random.randint(500, 900),
                prize_amount=10000.00 + (i * 5000),
                status=random.choice(['ACTIVE', 'DRAFT', 'CLOSED', 'DRAWN']),
                draw_date=timezone.now() + timedelta(days=random.randint(1, 30)),
                created_by=users[0]  # admin user
            )
            
            # Create tickets for active lotteries
            if lottery.status in ['ACTIVE', 'CLOSED']:
                sold_tickets = lottery.total_tickets - lottery.available_tickets
                for j in range(min(sold_tickets, 50)):  # Limit for performance
                    user = random.choice(users[1:])  # Exclude admin
                    ticket = Ticket.objects.create(
                        user=user,
                        lottery=lottery,
                        ticket_number=j + 1
                    )
                    
                    # Create transaction for ticket purchase
                    Transaction.objects.create(
                        user=user,
                        type='TICKET_PURCHASE',
                        amount=lottery.ticket_price,
                        status='COMPLETED',
                        lottery=lottery,
                        description=f'Purchased ticket #{ticket.ticket_number} for {lottery.name}'
                    )
                    
                    # Update user profile
                    user_profile = user.profile
                    user_profile.total_tickets_bought += 1
                    user_profile.total_spent += float(lottery.ticket_price)
                    user_profile.save()
                    
                    # Deduct balance from user
                    user.deduct_balance(lottery.ticket_price)
        
        # Create some winners for drawn lotteries
        drawn_lotteries = Lottery.objects.filter(status='DRAWN')
        for lottery in drawn_lotteries:
            # Get a random ticket to be the winner
            tickets = Ticket.objects.filter(lottery=lottery)
            if tickets.exists():
                winning_ticket = random.choice(list(tickets))
                Winner.objects.get_or_create(
                    user=winning_ticket.user,
                    lottery=lottery,
                    ticket=winning_ticket,
                    defaults={
                        'prize_amount': lottery.prize_amount,
                        'is_claimed': random.choice([True, False])
                    }
                )
                
                # Create transaction for prize award
                Transaction.objects.create(
                    user=winning_ticket.user,
                    type='PRIZE_AWARD',
                    amount=lottery.prize_amount,
                    status='COMPLETED',
                    lottery=lottery,
                    description=f'Won prize in {lottery.name}'
                )
        
        # Create some deposit transactions
        self.stdout.write('Creating transactions...')
        transaction_types = ['DEPOSIT', 'WITHDRAWAL', 'REFUND', 'ADMIN_ADJUSTMENT']
        for user in users[1:]:  # Exclude admin
            for _ in range(random.randint(2, 5)):
                Transaction.objects.create(
                    user=user,
                    type=random.choice(transaction_types),
                    amount=random.choice([50.00, 100.00, 200.00, 500.00]),
                    status=random.choice(['COMPLETED', 'PENDING', 'FAILED']),
                    description=f'Sample {random.choice(transaction_types).lower()} transaction'
                )
        
        # Create audit logs
        self.stdout.write('Creating audit logs...')
        actions = ['LOGIN', 'BUY_TICKET', 'WIN', 'WITHDRAWAL', 'DEPOSIT']
        for user in users:
            for _ in range(random.randint(3, 8)):
                AuditLog.objects.create(
                    user=user,
                    action=random.choice(actions),
                    description=f'{random.choice(actions)} action performed by {user.username}',
                    ip_address='127.0.0.1',
                    user_agent='Mozilla/5.0 (Sample User Agent)'
                )
        
        # Create some withdrawal requests
        self.stdout.write('Creating withdrawal requests...')
        for user in users[1:]:  # Exclude admin
            if user.wallet_balance > 0:
                payment_methods = user.payment_methods.all()
                if payment_methods.exists():
                    WithdrawalRequest.objects.create(
                        user=user,
                        amount=min(user.wallet_balance, 100.00),
                        payment_method=payment_methods.first(),
                        status=random.choice(['REQUESTED', 'APPROVED', 'COMPLETED', 'REJECTED']),
                        remarks='Sample withdrawal request'
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created sample data for {len(users)} users, '
                f'{Lottery.objects.count()} lotteries, '
                f'{Ticket.objects.count()} tickets, '
                f'{Transaction.objects.count()} transactions, '
                f'{AuditLog.objects.count()} audit logs'
            )
        )