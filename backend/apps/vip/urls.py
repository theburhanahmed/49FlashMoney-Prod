from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VIPViewSet, VIPAdminViewSet

app_name = 'vip'

router = DefaultRouter()
router.register(r'', VIPViewSet, basename='vip')
router.register(r'admin/tiers', VIPAdminViewSet, basename='vip-admin')

urlpatterns = [
    path('', include(router.urls)),
]
