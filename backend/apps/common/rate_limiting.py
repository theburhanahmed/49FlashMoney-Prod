"""
Rate limiting utilities and decorators.
"""
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from apps.common.utils import get_client_ip
import time


def rate_limit(key_func, rate='5/m', method='GET', block=True):
    """
    Rate limiting decorator.
    
    Args:
        key_func: Function to generate cache key (receives request)
        rate: Rate limit string (e.g., '5/m' for 5 per minute)
        method: HTTP method to limit
        block: Whether to block request if limit exceeded
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.method != method:
                return func(request, *args, **kwargs)
            
            # Parse rate limit
            num, period = rate.split('/')
            num = int(num)
            period_map = {
                's': 1,
                'm': 60,
                'h': 3600,
                'd': 86400,
            }
            period_seconds = period_map.get(period.lower(), 60)
            
            # Generate cache key
            key = key_func(request)
            cache_key = f"rate_limit:{key}"
            
            # Check current count
            count = cache.get(cache_key, 0)
            
            if count >= num:
                if block:
                    return JsonResponse({
                        'error': 'Rate limit exceeded. Please try again later.'
                    }, status=429)
                else:
                    # Log but don't block
                    pass
            
            # Increment count
            cache.set(cache_key, count + 1, period_seconds)
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def get_ip_key(request):
    """Generate rate limit key from IP address."""
    return get_client_ip(request)


def get_user_key(request):
    """Generate rate limit key from user ID."""
    if request.user.is_authenticated:
        return f"user:{request.user.id}"
    return get_client_ip(request)


def get_user_ip_key(request):
    """Generate rate limit key from user ID and IP."""
    if request.user.is_authenticated:
        return f"user_ip:{request.user.id}:{get_client_ip(request)}"
    return get_client_ip(request)

