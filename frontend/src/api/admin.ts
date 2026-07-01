/**
 * Admin API endpoints.
 */
import apiClient from './client';

// Types
export interface GameConfig {
  game_kind: string;
  default_config: Record<string, unknown>;
  active_rooms: number;
  total_rooms: number;
}

export interface EngineInfo {
  game_kind: string;
  module: string;
  has_default_config?: boolean;
  has_public_state?: boolean;
  has_get_winners?: boolean;
}

export interface GameConfigUpdateResponse {
  game_kind: string;
  config: Record<string, unknown>;
  message: string;
}

export interface RoundSummary {
  id: string;
  game_kind: string;
  status: string;
  entry_fee: string;
  player_count: number;
  players: Array<{
    user__username: string;
    user_id: string;
    result: string;
    payout: string;
  }>;
  config: Record<string, unknown>;
  has_state: boolean;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

export interface AuditLogEntry {
  id: number;
  user: string;
  user_id: string | null;
  action: string;
  description: string;
  resource_type: string | null;
  resource_id: string | null;
  changes: Record<string, unknown>;
  ip_address: string | null;
  timestamp: string;
}

export interface WithdrawalSummary {
  id: string;
  user: string;
  user_id: string;
  amount: string;
  status: string;
  bank_details: Record<string, unknown>;
  remarks: string;
  requested_at: string;
  processed_at: string | null;
}

export interface PaginatedResponse<T> {
  count: number;
  limit: number;
  offset: number;
  results: T[];
}

export interface RoundDetail extends RoundSummary {
  state: Record<string, unknown> | null;
  state_version: number | null;
  created_by: string;
}

export interface MaintenanceResponse {
  game_kind: string;
  enabled: boolean;
  reason: string;
  message: string;
  cancelled_rooms?: number;
}

export interface WithdrawalActionResponse {
  message: string;
  withdrawal_id: string;
  status: string;
}

// API functions
export const adminApi = {
  getGameConfig: (gameKind: string) =>
    apiClient.get<GameConfig>(`/games/admin/config/${gameKind}/`),

  updateGameConfig: (gameKind: string, config: Record<string, unknown>) =>
    apiClient.put<GameConfigUpdateResponse>(`/games/admin/config/${gameKind}/`, { config }),

  getEngines: () =>
    apiClient.get<{ engines: EngineInfo[] }>('/games/admin/engines/'),

  getRounds: (params?: { game_kind?: string; status?: string; user_id?: string; limit?: number; offset?: number }) =>
    apiClient.get<PaginatedResponse<RoundSummary>>('/games/admin/rounds/', { params }),

  getRoundDetail: (roomId: string) =>
    apiClient.get<RoundDetail>(`/games/admin/rounds/${roomId}/`),

  toggleMaintenance: (gameKind: string, enabled: boolean, reason?: string) =>
    apiClient.post<MaintenanceResponse>(`/games/admin/maintenance/${gameKind}/`, { enabled, reason }),

  getAuditLogs: (params?: { action?: string; user_id?: string; resource_type?: string; limit?: number; offset?: number }) =>
    apiClient.get<PaginatedResponse<AuditLogEntry>>('/games/admin/audit-logs/', { params }),

  getWithdrawals: (params?: { status?: string; limit?: number; offset?: number }) =>
    apiClient.get<PaginatedResponse<WithdrawalSummary>>('/games/admin/withdrawals/', { params }),

  approveWithdrawal: (withdrawalId: string, remarks?: string) =>
    apiClient.post<WithdrawalActionResponse>('/games/admin/withdrawals/approve/', { withdrawal_id: withdrawalId, remarks }),

  rejectWithdrawal: (withdrawalId: string, reason?: string) =>
    apiClient.post<WithdrawalActionResponse>('/games/admin/withdrawals/reject/', { withdrawal_id: withdrawalId, reason }),
};
