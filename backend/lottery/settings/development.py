"""
Development settings for 49FlashMoney.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['*']

# Use in-memory channel layer for development if Redis is not available
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL', default='redis://localhost:6379/1')],
        },
    },
}

# Email - console backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS - allow all in dev
CORS_ALLOW_ALL_ORIGINS = True

# Disable throttling in development
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000/min',
    'user': '2000/min',
}
