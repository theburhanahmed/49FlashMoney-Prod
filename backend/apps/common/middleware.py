"""
Middleware for audit logging and other common functionality.
"""
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware
from apps.users.models import AuditLog

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log admin actions and sensitive operations.
    """
    
    # Actions that should be logged
    ADMIN_ACTIONS = ['POST', 'PUT', 'PATCH', 'DELETE']
    SENSITIVE_ENDPOINTS = [
        '/api/admin/',
        '/api/users/',
        '/api/lotteries/',
        '/api/transactions/',
        '/api/referrals/',
    ]
    
    def process_request(self, request):
        """Store request info for later use in process_response."""
        request._audit_logged = False
    
    def process_response(self, request, response):
        """Log admin actions and sensitive operations."""
        # Skip if already logged or not a sensitive endpoint
        if getattr(request, '_audit_logged', False):
            return response
        
        # Only log admin actions on sensitive endpoints
        if (request.method in self.ADMIN_ACTIONS and 
            any(endpoint in request.path for endpoint in self.SENSITIVE_ENDPOINTS)):
            
            # Get user from request
            user = getattr(request, 'user', None)
            
            # Skip if user is not authenticated or not admin
            if not user or not user.is_authenticated:
                return response
            
            # Determine action type
            action_type = self._get_action_type(request.method, request.path)
            
            # Log the action
            try:
                AuditLog.objects.create(
                    user=user,
                    action=action_type,
                    description=f'{request.method} {request.path} - Status: {response.status_code}',
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )
            except Exception as e:
                logger.error(f'Error creating audit log: {str(e)}')
        
        return response
    
    def _get_action_type(self, method, path):
        """Determine audit log action type from method and path."""
        if '/withdrawals/' in path:
            return 'WITHDRAWAL'
        elif '/lotteries/' in path:
            if method == 'POST':
                return 'BUY_TICKET'
            elif method in ['PUT', 'PATCH']:
                return 'CHANGE_ROLE'  # Generic update
        elif '/users/' in path and method in ['PUT', 'PATCH', 'DELETE']:
            return 'TOGGLE_USER_STATUS'
        elif '/transactions/' in path and method == 'POST':
            return 'DEPOSIT'
        return 'CHANGE_ROLE'  # Default
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CsrfExemptApiMiddleware(CsrfViewMiddleware):
    """
    Middleware to exempt API endpoints from CSRF protection.
    REST APIs using JWT authentication don't need CSRF protection.
    Admin endpoints still use CSRF protection.
    """
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # Exempt all /api/ endpoints from CSRF protection (REST API with JWT)
        # But keep CSRF for /admin/ endpoints
        if request.path.startswith('/api/') and not request.path.startswith('/admin/'):
            return None
        # For other paths (including /admin/), use default CSRF protection
        return super().process_view(request, callback, callback_args, callback_kwargs)
