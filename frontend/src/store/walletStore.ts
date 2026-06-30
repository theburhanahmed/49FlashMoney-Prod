/**
 * Wallet state management using Zustand.
 */
import { create } from 'zustand';
import type { Wallet, LedgerEntry } from '../types';
import { walletApi } from '../api/wallet';

interface WalletState {
  wallet: Wallet | null;
  ledgerEntries: LedgerEntry[];
  ledgerCount: number;
  isLoading: boolean;
  error: string | null;
  fetchWallet: () => Promise<void>;
  fetchLedger: (params?: { limit?: number; offset?: number; type?: string }) => Promise<void>;
}

export const useWalletStore = create<WalletState>((set) => ({
  wallet: null,
  ledgerEntries: [],
  ledgerCount: 0,
  isLoading: false,
  error: null,

  fetchWallet: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await walletApi.getWallet();
      set({ wallet: response.data, isLoading: false });
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } }).response?.data?.error ||
        'Failed to load wallet';
      set({ error: message, isLoading: false });
    }
  },

  fetchLedger: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await walletApi.getLedgerHistory(params);
      set({
        ledgerEntries: response.data.results,
        ledgerCount: response.data.count,
        isLoading: false,
      });
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: string } } }).response?.data?.error ||
        'Failed to load ledger';
      set({ error: message, isLoading: false });
    }
  },
}));
