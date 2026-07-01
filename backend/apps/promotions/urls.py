"""Promotions URL configuration."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PromotionViewSet

app_name = 'promotions'

router = DefaultRouter()
router.register(r'promotions', PromotionViewSet, basename='promotion')

urlpatterns = [
    path('', include(router.urls)),
]
