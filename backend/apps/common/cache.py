"""
Cache utilities for the lottery system
"""
from django.core.cache import cache
from functools import wraps
import hashlib
import json


def cache_key_generator(*args, **kwargs):
    """
    Generate a cache key from function arguments
    """
    key_parts = []
    for arg in args:
        if hasattr(arg, 'id'):
            key_parts.append(str(arg.id))
        else:
            key_parts.append(str(arg))
    
    for k, v in sorted(kwargs.items()):
        if hasattr(v, 'id'):
            key_parts.append(f"{k}:{v.id}")
        else:
            key_parts.append(f"{k}:{v}")
    
    key_string = "_".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached_view(timeout=300, key_prefix=''):
    """
    Decorator to cache view responses
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}_{func.__name__}_{cache_key_generator(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """
    Invalidate all cache keys matching a pattern
    Note: This requires Redis with keys() support or a custom cache backend
    """
    try:
        # This is a simplified version - in production, use a more efficient method
        # For Redis, you might use SCAN or maintain a list of keys
        pass
    except Exception:
        pass


def get_or_set_cache(key, callable_func, timeout=300):
    """
    Get value from cache or set it using a callable
    """
    value = cache.get(key)
    if value is None:
        value = callable_func()
        cache.set(key, value, timeout)
    return value


# Cache key generators for common patterns
class CacheKeys:
    """Common cache key patterns"""
    
    @staticmethod
    def lottery_list(filters=None):
        filter_str = json.dumps(filters or {}, sort_keys=True)
        return f"lottery:list:{hashlib.md5(filter_str.encode()).hexdigest()}"
    
    @staticmethod
    def lottery_detail(lottery_id):
        return f"lottery:detail:{lottery_id}"
    
    @staticmethod
    def user_dashboard(user_id):
        return f"user:dashboard:{user_id}"
    
    @staticmethod
    def user_stats(user_id):
        return f"user:stats:{user_id}"
    
    @staticmethod
    def referral_stats(user_id):
        return f"referral:stats:{user_id}"
    
    @staticmethod
    def referral_program_settings():
        return "referral:program:settings"
    
    @staticmethod
    def analytics_summary(date_range=None):
        range_str = json.dumps(date_range or {}, sort_keys=True)
        return f"analytics:summary:{hashlib.md5(range_str.encode()).hexdigest()}"

