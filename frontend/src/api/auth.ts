/**
 * Auth API endpoints.
 */
import apiClient from './client';
import type { LoginRequest, LoginResponse, RegisterRequest, User } from '../types';

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/users/login/', data),

  register: (data: RegisterRequest) =>
    apiClient.post<{ message: string }>('/users/register/', data),

  getProfile: () =>
    apiClient.get<User>('/users/profile/'),

  changePassword: (data: { old_password: string; new_password: string }) =>
    apiClient.post<{ message: string }>('/users/change-password/', data),

  requestPasswordReset: (email: string) =>
    apiClient.post<{ message: string }>('/users/password-reset-request/', { email }),

  resetPassword: (data: { token: string; new_password: string }) =>
    apiClient.post<{ message: string }>('/users/password-reset/', data),

  verifyEmail: (token: string) =>
    apiClient.post<{ message: string }>('/users/verify-email/', { token }),
};
