from django.urls import path
from .consumers import GameRoomConsumer

websocket_urlpatterns = [
    path('ws/games/<str:room_id>/', GameRoomConsumer.as_asgi()),
]
