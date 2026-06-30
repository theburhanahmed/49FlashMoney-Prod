/**
 * Wallet API endpoints.
 */
import apiClient from './client';
import type { Wallet, LedgerHistoryResponse } from '../types';

export const walletApi = {
  getWallet: () =>
    apiClient.get<Wallet>('/wallet/'),

  getLedgerHistory: (params?: { limit?: number; offset?: number; type?: string }) =>
    apiClient.get<LedgerHistoryResponse>('/wallet/ledger/', { params }),

  reconcile: () =>
    apiClient.get<{
      user_id: string;
      derived_balance: string;
      cached_balance: string;
      match: boolean;
      difference: string;
    }>('/wallet/reconcile/'),
};
