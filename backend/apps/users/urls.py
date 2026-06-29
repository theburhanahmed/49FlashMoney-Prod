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

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    # Put specific paths BEFORE router to avoid conflicts
    path('users/register/', register_view, name='register'),
    path('users/login/', login_view, name='login'),
    path('users/password-reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('users/password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('users/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('users/verify-email/', EmailVerificationView.as_view(), name='email-verification'),
    path('users/resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('users/setup-2fa/', Setup2FAView.as_view(), name='setup-2fa'),
    path('users/verify-2fa-setup/', Verify2FASetupView.as_view(), name='verify-2fa-setup'),
    path('users/disable-2fa/', Disable2FAView.as_view(), name='disable-2fa'),
    # Router URLs come last
    path('', include(router.urls)),
]
