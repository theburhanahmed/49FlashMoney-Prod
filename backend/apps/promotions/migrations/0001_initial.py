"""Initial migration for Promotion model."""
import uuid
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Promotion',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                (
                    'promotion_type',
                    models.CharField(
                        choices=[
                            ('DEPOSIT_BONUS', 'Deposit Bonus'),
                            ('FREE_BET', 'Free Bet'),
                            ('CASHBACK', 'Cashback'),
                            ('REFERRAL', 'Referral'),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('DRAFT', 'Draft'),
                            ('ACTIVE', 'Active'),
                            ('EXPIRED', 'Expired'),
                            ('CANCELLED', 'Cancelled'),
                        ],
                        default='DRAFT',
                        max_length=20,
                    ),
                ),
                (
                    'bonus_percentage',
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal('0.00'),
                        max_digits=5,
                    ),
                ),
                (
                    'max_bonus_amount',
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal('0.00'),
                        max_digits=10,
                    ),
                ),
                (
                    'min_deposit',
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal('0.00'),
                        max_digits=10,
                    ),
                ),
                (
                    'wagering_requirement',
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal('1.00'),
                        max_digits=5,
                    ),
                ),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                (
                    'max_claims',
                    models.IntegerField(
                        default=0,
                        help_text='0 = unlimited',
                    ),
                ),
                ('total_claims', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'promotions',
                'ordering': ['-created_at'],
            },
        ),
    ]
