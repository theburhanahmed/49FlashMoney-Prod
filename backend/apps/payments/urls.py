"""
URL configuration for payments app.
"""
from django.urls import path
from apps.payments import views

app_name = 'payments'

urlpatterns = [
    # Stripe endpoints
    path('config/', views.get_stripe_config, name='get_stripe_config'),
    path('create-intent/', views.create_payment_intent, name='create_payment_intent'),
    path('confirm-intent/', views.confirm_payment_intent, name='confirm_payment_intent'),
    path('intent/<str:payment_intent_id>/', views.get_payment_intent, name='get_payment_intent'),
    path('save-method/', views.save_payment_method, name='save_payment_method'),
    path('methods/', views.list_payment_methods, name='list_payment_methods'),
    path('methods/<str:payment_method_id>/', views.delete_payment_method, name='delete_payment_method'),
    path('customer/', views.get_stripe_customer, name='get_stripe_customer'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    # Razorpay (India: UPI, cards, netbanking, wallets)
    path('razorpay/config/', views.get_razorpay_config, name='get_razorpay_config'),
    path('razorpay/create-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('razorpay/verify/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('razorpay/webhook/', views.razorpay_webhook, name='razorpay_webhook'),
]
