from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import GameRoom
from .serializers import (
    GameRoomListSerializer,
    GameRoomDetailSerializer,
    CreateRoomSerializer,
)
from .services import create_room, join_room, leave_room, start_game, end_game


class GameRoomViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = GameRoom.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return GameRoomListSerializer
        return GameRoomDetailSerializer

    def get_queryset(self):
        qs = GameRoom.objects.all().select_related('created_by').prefetch_related('players__user')
        if self.action == 'list':
            game_kind = self.request.query_params.get('game_kind')
            room_status = self.request.query_params.get('status', 'WAITING')
            if game_kind:
                qs = qs.filter(game_kind=game_kind)
            if room_status:
                qs = qs.filter(status=room_status)
        return qs.order_by('-created_at')

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = GameRoomListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        ser = CreateRoomSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            room = create_room(
                request.user,
                ser.validated_data['game_kind'],
                ser.validated_data['entry_fee'],
                ser.validated_data.get('config', {}),
            )
            serializer = GameRoomDetailSerializer(room)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        room = self.get_object()
        serializer = GameRoomDetailSerializer(room)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        room = self.get_object()
        try:
            join_room(request.user, str(room.id))
            room.refresh_from_db()
            serializer = GameRoomDetailSerializer(room)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        try:
            room = leave_room(request.user, str(pk))
            if room is None:
                return Response({'status': 'room_deleted'})
            serializer = GameRoomDetailSerializer(room)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        room = self.get_object()
        try:
            start_game(str(room.id), started_by_user=request.user)
            room.refresh_from_db()
            serializer = GameRoomDetailSerializer(room)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
