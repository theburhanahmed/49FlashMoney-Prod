"""
Tests for health check and readiness endpoints.
"""
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'health-tests',
        }
    },
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {},
    },
)
class HealthCheckTestCase(TestCase):
    """Tests for /api/health/ endpoints."""

    def setUp(self):
        self.client = APIClient()

    def test_basic_health(self):
        resp = self.client.get('/api/health/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'healthy')

    def test_db_health(self):
        resp = self.client.get('/api/health/db/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['database'], 'connected')

    def test_cache_health(self):
        resp = self.client.get('/api/health/cache/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['cache'], 'connected')

    def test_readiness_endpoint(self):
        resp = self.client.get('/api/health/ready/')
        # DB and cache should be healthy in test environment
        self.assertIn(resp.status_code, [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ])
        self.assertIn('checks', resp.data)
        self.assertIn('database', resp.data['checks'])
        self.assertIn('cache', resp.data['checks'])
        # DB should definitely be healthy
        self.assertEqual(resp.data['checks']['database']['status'], 'healthy')
        self.assertIn('latency_ms', resp.data['checks']['database'])

    def test_health_no_throttle(self):
        """Health endpoints should not be throttled."""
        for _ in range(20):
            resp = self.client.get('/api/health/')
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_health_no_auth_required(self):
        """Health endpoints are public."""
        resp = self.client.get('/api/health/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.get('/api/health/ready/')
        self.assertIn(resp.status_code, [200, 503])
