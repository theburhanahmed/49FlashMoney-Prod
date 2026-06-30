"""
Initial migration for Wallet and LedgerEntry models.
"""
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('balance', models.DecimalField(
                    decimal_places=2, default=Decimal('0.00'),
                    help_text='Cached balance derived from ledger entries.',
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                )),
                ('reserved_balance', models.DecimalField(
                    decimal_places=2, default=Decimal('0.00'),
                    help_text='Funds reserved for active bets or pending withdrawals.',
                    max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                )),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('status', models.CharField(
                    choices=[('ACTIVE', 'Active'), ('RESTRICTED', 'Restricted'), ('FROZEN', 'Frozen')],
                    default='ACTIVE', max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='wallet_account',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'wallets',
                'indexes': [
                    models.Index(fields=['user'], name='wallets_user_idx'),
                    models.Index(fields=['status'], name='wallets_status_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='LedgerEntry',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('entry_type', models.CharField(
                    choices=[
                        ('DEPOSIT', 'Deposit'), ('WITHDRAWAL', 'Withdrawal'),
                        ('BET', 'Bet'), ('WINNING', 'Winning'),
                        ('BONUS', 'Bonus'), ('REFUND', 'Refund'),
                        ('REFERRAL_REWARD', 'Referral Reward'),
                        ('ADJUSTMENT', 'Adjustment'), ('REVERSAL', 'Reversal'),
                        ('RESERVATION', 'Reservation'),
                        ('RESERVATION_RELEASE', 'Reservation Release'),
                    ],
                    max_length=30,
                )),
                ('direction', models.CharField(
                    choices=[('CREDIT', 'Credit'), ('DEBIT', 'Debit')],
                    max_length=6,
                )),
                ('amount', models.DecimalField(
                    decimal_places=2, max_digits=12,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                )),
                ('balance_before', models.DecimalField(decimal_places=2, max_digits=12)),
                ('balance_after', models.DecimalField(decimal_places=2, max_digits=12)),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('reference_type', models.CharField(blank=True, max_length=50)),
                ('reference_id', models.CharField(blank=True, max_length=255)),
                ('idempotency_key', models.CharField(
                    blank=True, max_length=255, null=True, unique=True,
                )),
                ('description', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('actor', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('wallet', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='ledger_entries',
                    to='wallet.wallet',
                )),
            ],
            options={
                'db_table': 'ledger_entries',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['wallet', '-created_at'], name='ledger_wallet_created_idx'),
                    models.Index(fields=['entry_type', '-created_at'], name='ledger_type_created_idx'),
                    models.Index(fields=['reference_type', 'reference_id'], name='ledger_ref_idx'),
                    models.Index(fields=['idempotency_key'], name='ledger_idemp_idx'),
                    models.Index(fields=['created_at'], name='ledger_created_idx'),
                ],
            },
        ),
    ]
