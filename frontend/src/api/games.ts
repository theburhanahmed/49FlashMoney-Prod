/**
 * Games API endpoints.
 */
import apiClient from './client';
import type { GameRoom, GameKind } from '../types';

export const gamesApi = {
  listRooms: <T = GameRoom[]>(params?: { game_kind?: GameKind; status?: string }) =>
    apiClient.get<T>('/games/rooms/', { params }),

  getRoom: (roomId: string) =>
    apiClient.get<GameRoom>(`/games/rooms/${roomId}/`),

  createRoom: (data: { game_kind: GameKind; entry_fee: number; config?: Record<string, unknown> }) =>
    apiClient.post<GameRoom>('/games/rooms/', data),

  joinRoom: (roomId: string) =>
    apiClient.post<GameRoom>(`/games/rooms/${roomId}/join/`),

  leaveRoom: (roomId: string) =>
    apiClient.post<GameRoom>(`/games/rooms/${roomId}/leave/`),

  startGame: (roomId: string) =>
    apiClient.post<GameRoom>(`/games/rooms/${roomId}/start/`),
};

/**
 * WebSocket connection for game rooms.
 */
export function createGameWebSocket(roomId: string, token: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const url = `${protocol}//${host}/ws/game/${roomId}/?token=${token}`;
  return new WebSocket(url);
}
