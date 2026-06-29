from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.lotteries.views import LotteryViewSet, TicketViewSet

router = DefaultRouter()
router.register(r'lotteries', LotteryViewSet, basename='lottery')
router.register(r'tickets', TicketViewSet, basename='ticket')

urlpatterns = [
    path('', include(router.urls)),
]
