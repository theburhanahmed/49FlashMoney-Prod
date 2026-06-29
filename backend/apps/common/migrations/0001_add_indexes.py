# Generated migration for additional database indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('lotteries', '0001_initial'),
        ('transactions', '0001_initial'),
        ('referrals', '0001_initial'),
    ]

    operations = [
        # Add composite index for user wallet balance queries
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['wallet_balance'], name='users_wallet_balance_idx'),
        ),
        # Add index for lottery status and draw date queries
        migrations.AddIndex(
            model_name='lottery',
            index=models.Index(fields=['status', 'draw_date'], name='lotteries_status_draw_date_idx'),
        ),
        # Add index for ticket user and purchased_at queries
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['user', '-purchased_at'], name='tickets_user_purchased_idx'),
        ),
        # Add index for transaction user and type queries
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'type', '-created_at'], name='transactions_user_type_created_idx'),
        ),
        # Add index for referral status queries
        migrations.AddIndex(
            model_name='referral',
            index=models.Index(fields=['referrer', 'status'], name='referrals_referrer_status_idx'),
        ),
        # Add index for referral bonus status queries
        migrations.AddIndex(
            model_name='referralbonus',
            index=models.Index(fields=['user', 'status'], name='referral_bonus_user_status_idx'),
        ),
    ]

