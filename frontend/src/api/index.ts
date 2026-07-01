/**
 * API module barrel export.
 */
export { default as apiClient } from './client';
export { authApi } from './auth';
export { walletApi } from './wallet';
export { paymentsApi } from './payments';
export { gamesApi, createGameWebSocket } from './games';
export { adminApi } from './admin';
export { slotsApi } from './slots';
export { vipApi } from './vip';
export { promotionsApi } from './promotions';
export { analyticsApi } from './analytics';
