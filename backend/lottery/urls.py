"""
Root URL Configuration for 49FlashMoney platform.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="49FlashMoney API",
        default_version='v1',
        description="Real-money gaming platform API",
        contact=openapi.Contact(email="support@49flashmoney.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/users/', include('apps.users.urls')),
    path('api/wallet/', include('apps.wallet.urls')),
    path('api/transactions/', include('apps.transactions.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/lotteries/', include('apps.lotteries.urls')),
    path('api/games/', include('apps.games.urls')),
    path('api/slots/', include('apps.slots.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/referrals/', include('apps.referrals.urls')),
    path('api/promotions/', include('apps.promotions.urls')),
    path('api/vip/', include('apps.vip.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/common/', include('apps.common.urls')),
    path('api/providers/', include('apps.providers.urls')),

    # API Documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
