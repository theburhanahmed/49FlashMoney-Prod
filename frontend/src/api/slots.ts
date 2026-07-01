import apiClient from './client';

export interface SlotsGame {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  min_bet: string;
  max_bet: string;
  rtp_percent: string;
  paytable?: Record<string, number>;
}

export interface SpinResult {
  spin_id: string;
  symbols: string[];
  payout: string;
  bet_amount: string;
  won: boolean;
}

export interface SpinHistory {
  id: string;
  symbols: string[];
  bet_amount: string;
  payout: string;
  created_at: string;
}

export const slotsApi = {
  listGames: () =>
    apiClient.get<SlotsGame[]>('/slots/games/'),

  getGame: (gameId: string) =>
    apiClient.get<SlotsGame>(`/slots/games/${gameId}/`),

  spin: (gameId: string, betAmount: string) =>
    apiClient.post<SpinResult>(`/slots/games/${gameId}/spin/`, { bet_amount: betAmount }),

  getHistory: (gameId: string) =>
    apiClient.get<SpinHistory[]>(`/slots/games/${gameId}/history/`),
};
