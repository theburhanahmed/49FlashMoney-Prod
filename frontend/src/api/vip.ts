import apiClient from './client';

export interface VIPTier {
  id: string;
  name: string;
  level: number;
  min_wagered?: string;
  cashback_percentage: string;
  withdrawal_limit_multiplier: string;
  benefits: Record<string, unknown>;
  member_count?: number;
}

export interface VIPStatus {
  tier: VIPTier;
  total_wagered: string;
  promoted_at: string | null;
  next_tier: {
    name: string;
    level: number;
    min_wagered: string;
    remaining: string;
  } | null;
}

export const vipApi = {
  getStatus: () =>
    apiClient.get<VIPStatus>('/vip/status/'),

  getTiers: () =>
    apiClient.get<VIPTier[]>('/vip/tiers/'),

  claimCashback: () =>
    apiClient.post<{ message: string; amount: string }>('/vip/cashback/'),
};
