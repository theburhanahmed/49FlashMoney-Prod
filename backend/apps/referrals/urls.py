from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .views import (
    ReferralProgramViewSet,
    ReferralLinkViewSet,
    ReferralViewSet,
    ReferralBonusViewSet,
    ReferralWithdrawalViewSet
)

router = DefaultRouter()
router.register(r'programs', ReferralProgramViewSet, basename='referral-program')
router.register(r'links', ReferralLinkViewSet, basename='referral-link')
router.register(r'', ReferralViewSet, basename='referral')
router.register(r'bonuses', ReferralBonusViewSet, basename='referral-bonus')
router.register(r'withdrawals', ReferralWithdrawalViewSet, basename='referral-withdrawal')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stats_view(request):
    """Direct endpoint for referral stats."""
    viewset = ReferralViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    return viewset.stats(request)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_referrals_view(request):
    """Direct endpoint for my referrals."""
    viewset = ReferralViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    return viewset.my_referrals(request)

urlpatterns = [
    # Direct shortcuts for frontend compatibility
    path('stats/', stats_view, name='referral-stats'),
    path('my_referrals/', my_referrals_view, name='referral-my-referrals'),
    # Include router URLs
    path('', include(router.urls)),
]
