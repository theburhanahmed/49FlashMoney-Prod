from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SlotsGameViewSet

router = DefaultRouter()
router.register(r'games', SlotsGameViewSet, basename='slots-game')

urlpatterns = [
    path('', include(router.urls)),
]
