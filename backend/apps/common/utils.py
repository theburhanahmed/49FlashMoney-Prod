"""
Utility functions for the lottery system.
"""
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
import pytz

logger = logging.getLogger(__name__)


def get_timezone_aware_datetime(dt, tz_name='UTC'):
    """
    Convert datetime to timezone-aware datetime.
    
    Args:
        dt: datetime object (naive or aware)
        tz_name: timezone name (default: UTC)
    
    Returns:
        timezone-aware datetime
    """
    if dt is None:
        return None
    
    tz = pytz.timezone(tz_name)
    
    if timezone.is_aware(dt):
        return dt.astimezone(tz)
    else:
        return tz.localize(dt)


def get_current_time_in_timezone(tz_name='UTC'):
    """
    Get current time in specified timezone.
    
    Args:
        tz_name: timezone name (default: UTC)
    
    Returns:
        timezone-aware datetime
    """
    tz = pytz.timezone(tz_name)
    return timezone.now().astimezone(tz)


def is_datetime_in_range(dt, start_dt, end_dt):
    """
    Check if datetime is within range.
    
    Args:
        dt: datetime to check
        start_dt: start datetime
        end_dt: end datetime
    
    Returns:
        True if dt is within range, False otherwise
    """
    if dt is None or start_dt is None or end_dt is None:
        return False
    
    return start_dt <= dt <= end_dt


def format_currency(amount, currency='USD'):
    """
    Format amount as currency.
    
    Args:
        amount: decimal amount
        currency: currency code (default: USD)
    
    Returns:
        formatted currency string
    """
    if currency == 'USD':
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"


def log_info(message, extra=None):
    """Log info message with optional extra context."""
    if extra:
        logger.info(message, extra=extra)
    else:
        logger.info(message)


def log_error(message, exception=None, extra=None):
    """Log error message with optional exception and extra context."""
    if exception:
        logger.error(f"{message}: {str(exception)}", exc_info=True, extra=extra)
    else:
        logger.error(message, extra=extra)


def log_warning(message, extra=None):
    """Log warning message with optional extra context."""
    if extra:
        logger.warning(message, extra=extra)
    else:
        logger.warning(message)


def generate_unique_code(prefix='', length=12):
    """
    Generate a unique code.
    
    Args:
        prefix: prefix for the code
        length: length of random part
    
    Returns:
        unique code string
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{random_part}"


def get_client_ip(request):
    """
    Get client IP address from request.
    
    Args:
        request: Django request object
    
    Returns:
        IP address string
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def calculate_percentage(part, total):
    """
    Calculate percentage.
    
    Args:
        part: part value
        total: total value
    
    Returns:
        percentage (0-100)
    """
    if total == 0:
        return 0
    return (part / total) * 100

