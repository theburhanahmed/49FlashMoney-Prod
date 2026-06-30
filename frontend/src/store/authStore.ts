/**
 * Auth state management using Zustand.
 */
import { create } from 'zustand';
import type { User } from '../types';
import { authApi } from '../api/auth';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (data: {
    username: string;
    email: string;
    password: string;
    password_confirm: string;
  }) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),
  isLoading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.login({ username, password });
      const { token, user } = response.data;
      localStorage.setItem('token', token);
      set({ user, token, isAuthenticated: true, isLoading: false });
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { non_field_errors?: string[]; error?: string } } })
          .response?.data?.non_field_errors?.[0] ||
        (err as { response?: { data?: { error?: string } } }).response?.data?.error ||
        'Login failed';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.register(data);
      set({ isLoading: false });
    } catch (err: unknown) {
      const respData = (err as { response?: { data?: Record<string, string[]> } }).response?.data;
      const message = respData
        ? Object.values(respData).flat().join(' ')
        : 'Registration failed';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadUser: async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      set({ isAuthenticated: false });
      return;
    }
    try {
      const response = await authApi.getProfile();
      set({ user: response.data, isAuthenticated: true });
    } catch {
      localStorage.removeItem('token');
      set({ user: null, token: null, isAuthenticated: false });
    }
  },

  clearError: () => set({ error: null }),
}));
