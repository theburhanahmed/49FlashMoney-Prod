"""
Safe throttling classes that handle cache failures gracefully.
"""
import logging
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)


class SafeAnonRateThrottle(AnonRateThrottle):
    """Custom throttle that handles cache failures gracefully"""
    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception as e:
            # If cache fails, log the error but allow the request through
            logger.warning(f'Throttle cache error: {e}. Allowing request.')
            return True


class SafeUserRateThrottle(UserRateThrottle):
    """Custom throttle that handles cache failures gracefully"""
    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception as e:
            # If cache fails, log the error but allow the request through
            logger.warning(f'Throttle cache error: {e}. Allowing request.')
            return True

