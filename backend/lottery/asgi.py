"""
ASGI config for 49FlashMoney platform.
Supports HTTP and WebSocket protocols via Django Channels.
"""
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lottery.settings.development')

# Initialize Django ASGI application early to ensure apps are loaded
django_asgi_app = get_asgi_application()

from apps.games.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
