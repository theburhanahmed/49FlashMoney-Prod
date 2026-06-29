from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.analytics.views import AnalyticsViewSet

router = DefaultRouter()
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

urlpatterns = [
    path('admin/', include(router.urls)),
]

