from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.slots.views import SlotsGameViewSet, SlotsSpinViewSet

router = DefaultRouter()
router.register(r'games', SlotsGameViewSet, basename='slots-game')
router.register(r'spins', SlotsSpinViewSet, basename='slots-spin')

urlpatterns = [
    path('', include(router.urls)),
]
