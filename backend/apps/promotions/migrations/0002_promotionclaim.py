"""Migration to add PromotionClaim model."""
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('promotions', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PromotionClaim',
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
                (
                    'bonus_amount',
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                (
                    'deposit_amount',
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    'wagering_remaining',
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal('0.00'),
                        max_digits=10,
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('PENDING', 'Pending'),
                            ('CREDITED', 'Credited'),
                            ('COMPLETED', 'Completed'),
                            ('EXPIRED', 'Expired'),
                        ],
                        default='PENDING',
                        max_length=20,
                    ),
                ),
                ('claimed_at', models.DateTimeField(auto_now_add=True)),
                (
                    'promotion',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='claims',
                        to='promotions.promotion',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='promotion_claims',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'db_table': 'promotion_claims',
                'ordering': ['-claimed_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='promotionclaim',
            unique_together={('user', 'promotion')},
        ),
    ]
