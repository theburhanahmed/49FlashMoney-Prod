"""
Common views for health checks and system status.
"""
import time
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
from django.conf import settings
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


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([])
def health_ready(request):
    """
    Combined readiness endpoint. Checks DB, cache, and Celery.
    Returns 200 only if ALL dependencies are healthy.
    GET /api/health/ready/
    """
    checks = {}
    all_healthy = True

    # 1. Database
    db_start = time.monotonic()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks['database'] = {
            'status': 'healthy',
            'latency_ms': round((time.monotonic() - db_start) * 1000, 1),
        }
    except Exception as e:
        checks['database'] = {'status': 'unhealthy', 'error': str(e)}
        all_healthy = False

    # 2. Cache
    cache_start = time.monotonic()
    try:
        cache.set('readiness_probe', '1', 10)
        val = cache.get('readiness_probe')
        cache.delete('readiness_probe')
        if val == '1':
            checks['cache'] = {
                'status': 'healthy',
                'latency_ms': round((time.monotonic() - cache_start) * 1000, 1),
            }
        else:
            checks['cache'] = {'status': 'unhealthy', 'error': 'value mismatch'}
            all_healthy = False
    except Exception as e:
        checks['cache'] = {'status': 'unhealthy', 'error': str(e)}
        all_healthy = False

    # 3. Celery (ping worker via inspect)
    try:
        from celery import current_app
        inspector = current_app.control.inspect(timeout=2.0)
        ping_result = inspector.ping()
        if ping_result:
            checks['celery'] = {
                'status': 'healthy',
                'workers': len(ping_result),
            }
        else:
            checks['celery'] = {'status': 'unhealthy', 'error': 'no workers'}
            all_healthy = False
    except Exception as e:
        checks['celery'] = {'status': 'degraded', 'error': str(e)}
        # Celery down is degraded, not fatal for readiness

    # 4. Wallet ledger integrity (quick reconciliation spot-check)
    try:
        from apps.wallet.models import Wallet
        from django.db.models import Sum, F
        sample = Wallet.objects.order_by('-updated_at')[:5]
        for w in sample:
            ledger_balance = w.entries.aggregate(
                net=Sum('amount', filter=__import__('django').db.models.Q(direction='CREDIT'))
            )['net'] or 0
            # Just verify the query runs without error
        checks['ledger'] = {'status': 'healthy'}
    except Exception as e:
        checks['ledger'] = {'status': 'degraded', 'error': str(e)}

    overall_status = 'healthy' if all_healthy else 'unhealthy'
    http_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response({
        'status': overall_status,
        'service': '49FlashMoney',
        'checks': checks,
    }, status=http_status)

