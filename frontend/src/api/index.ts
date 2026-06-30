/**
 * API module barrel export.
 */
export { default as apiClient } from './client';
export { authApi } from './auth';
export { walletApi } from './wallet';
export { paymentsApi } from './payments';
export { gamesApi, createGameWebSocket } from './games';
