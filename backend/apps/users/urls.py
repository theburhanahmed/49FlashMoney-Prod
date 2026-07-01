from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views import (
    register_view, login_view, UserViewSet,
    PasswordResetRequestView, PasswordResetView,
    ChangePasswordView, EmailVerificationView,
    ResendVerificationView, Setup2FAView,
    Verify2FASetupView, Disable2FAView
)
from apps.users.admin_views import AdminUserViewSet

# Root urlconf already provides 'api/users/' prefix, so register
# viewsets at '' (not 'users/') to avoid doubled path segments.
router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    # Put specific paths BEFORE router to avoid conflicts
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('verify-email/', EmailVerificationView.as_view(), name='email-verification'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('setup-2fa/', Setup2FAView.as_view(), name='setup-2fa'),
    path('verify-2fa-setup/', Verify2FASetupView.as_view(), name='verify-2fa-setup'),
    path('disable-2fa/', Disable2FAView.as_view(), name='disable-2fa'),
    # Router URLs come last
    path('', include(router.urls)),
]
