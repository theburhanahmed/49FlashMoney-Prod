# Generated manually for payments app

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
        ('transactions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StripeCustomer',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('stripe_customer_id', models.CharField(max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stripe_customer', to='users.user')),
            ],
            options={
                'db_table': 'stripe_customers',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentIntent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('stripe_payment_intent_id', models.CharField(max_length=255, unique=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='usd', max_length=3)),
                ('status', models.CharField(choices=[('requires_payment_method', 'Requires Payment Method'), ('requires_confirmation', 'Requires Confirmation'), ('requires_action', 'Requires Action'), ('processing', 'Processing'), ('requires_capture', 'Requires Capture'), ('succeeded', 'Succeeded'), ('canceled', 'Canceled')], default='requires_payment_method', max_length=50)),
                ('client_secret', models.CharField(blank=True, max_length=255)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('transaction', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_intent', to='transactions.transaction')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_intents', to='users.user')),
            ],
            options={
                'db_table': 'payment_intents',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='paymentintent',
            index=models.Index(fields=['user', '-created_at'], name='payment_int_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentintent',
            index=models.Index(fields=['status'], name='payment_int_status_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentintent',
            index=models.Index(fields=['stripe_payment_intent_id'], name='payment_int_stripe_idx'),
        ),
    ]

