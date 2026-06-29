"""
Common views for health checks and system status.
"""
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([])  # No throttling so platform health checks (e.g. Render) don't get 429
def health_check(request):
    """
    Basic health check endpoint.
    GET /api/health/
    """
    return Response({
        'status': 'healthy',
        'service': 'lottery-system'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([])
def health_db(request):
    """
    Database health check endpoint.
    GET /api/health/db/
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return Response({
            'status': 'healthy',
            'database': 'connected'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([])
def health_cache(request):
    """
    Cache health check endpoint.
    GET /api/health/cache/
    """
    try:
        test_key = 'health_check_test'
        cache.set(test_key, 'test_value', 10)
        value = cache.get(test_key)
        cache.delete(test_key)
        
        if value == 'test_value':
            return Response({
                'status': 'healthy',
                'cache': 'connected'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'unhealthy',
                'cache': 'not_working'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'cache': 'error',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

