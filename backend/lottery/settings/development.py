"""
Development settings for 49FlashMoney.

Designed for local manual testing with the smallest practical setup:
  - SQLite (default, no PostgreSQL needed)
  - In-memory cache (no Redis needed)
  - In-memory channel layer (no Redis needed)
  - Celery tasks run synchronously in-process (no broker needed)
  - Console email backend (no SMTP needed)

If you *do* have Redis running locally, set REDIS_URL in .env and this
file will detect it and use Redis for cache/channels/celery instead.
"""
import os
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['*']

# ---------------------------------------------------------------------------
# Detect whether Redis is available
# ---------------------------------------------------------------------------
_redis_url = env('REDIS_URL', default='')
_use_redis = bool(_redis_url)

# ---------------------------------------------------------------------------
# Cache: in-memory by default, Redis if REDIS_URL is set
# ---------------------------------------------------------------------------
if _use_redis:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': _redis_url,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'dev-cache',
        }
    }

# ---------------------------------------------------------------------------
# Channel layer: in-memory by default, Redis if REDIS_URL is set
# ---------------------------------------------------------------------------
if _use_redis:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [_redis_url],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ---------------------------------------------------------------------------
# Celery: eager mode (synchronous, in-process) when no broker is available
# ---------------------------------------------------------------------------
if _use_redis:
    CELERY_BROKER_URL = _redis_url
    CELERY_RESULT_BACKEND = _redis_url
else:
    # Execute tasks immediately in the calling process -- no worker needed
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'

# ---------------------------------------------------------------------------
# Email - console backend for development
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ---------------------------------------------------------------------------
# CORS - allow all in dev
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True

# ---------------------------------------------------------------------------
# Relax throttling in development
# ---------------------------------------------------------------------------
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000/min',
    'user': '2000/min',
}
