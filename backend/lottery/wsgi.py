"""
WSGI config for 49FlashMoney platform.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lottery.settings.development')

application = get_wsgi_application()
