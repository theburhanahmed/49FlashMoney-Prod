/**
 * Core type definitions for 49FlashMoney frontend.
 */

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_admin: boolean;
  role: 'user' | 'admin' | 'moderator';
  wallet_balance: string;
  phone_number: string;
  date_of_birth: string | null;
  is_verified: boolean;
  email_verified: boolean;
  age_verified: boolean;
  is_2fa_enabled: boolean;
  profile: UserProfile | null;
  permissions: {
    is_user: boolean;
    is_moderator: boolean;
    is_super_admin: boolean;
  };
  created_at: string;
  updated_at: string;
}

export interface UserProfile {
  total_spent: string;
  total_won: string;
  total_tickets_bought: number;
  total_lotteries_participated: number;
  total_wins: number;
  avatar: string | null;
  bio: string;
}

export interface LoginRequest {
  username?: string;
  email?: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
  date_of_birth?: string;
}

// ─── Wallet ──────────────────────────────────────────────────────────────────

export interface Wallet {
  id: string;
  username: string;
  balance: string;
  reserved_balance: string;
  available_balance: string;
  currency: string;
  status: 'ACTIVE' | 'RESTRICTED' | 'FROZEN';
  created_at: string;
  updated_at: string;
}

export interface LedgerEntry {
  id: string;
  entry_type: LedgerEntryType;
  direction: 'CREDIT' | 'DEBIT';
  amount: string;
  balance_before: string;
  balance_after: string;
  currency: string;
  reference_type: string;
  reference_id: string;
  idempotency_key: string | null;
  description: string;
  metadata: Record<string, unknown>;
  actor: string;
  created_at: string;
}

export type LedgerEntryType =
  | 'DEPOSIT'
  | 'WITHDRAWAL'
  | 'BET'
  | 'WINNING'
  | 'BONUS'
  | 'REFUND'
  | 'REFERRAL_REWARD'
  | 'ADJUSTMENT'
  | 'REVERSAL'
  | 'RESERVATION'
  | 'RESERVATION_RELEASE';

export interface LedgerHistoryResponse {
  count: number;
  limit: number;
  offset: number;
  results: LedgerEntry[];
}

// ─── Payments ────────────────────────────────────────────────────────────────

export interface PaymentIntent {
  id: string;
  stripe_payment_intent_id: string;
  amount: string;
  currency: string;
  status: string;
  client_secret: string;
  created_at: string;
}

export interface RazorpayOrder {
  order_id: string;
  amount: string;
  currency: string;
}

export interface RazorpayConfig {
  key_id: string;
  currency: string;
  available: boolean;
}

// ─── Games ───────────────────────────────────────────────────────────────────

export type GameKind = 'SNAKES_LADDERS' | 'LUDO' | 'CARROM' | 'AVIATOR' | 'WINGO' | 'MINES' | 'SCRATCH_CARD';

export type GameRoomStatus = 'WAITING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';

export interface GameRoom {
  id: string;
  game_kind: GameKind;
  status: GameRoomStatus;
  entry_fee: string;
  min_players: number;
  max_players: number;
  created_by: string;
  players: GameRoomPlayer[];
  config: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

export interface GameRoomPlayer {
  id: string;
  user: {
    id: string;
    username: string;
  };
  position: number;
  result: 'WON' | 'LOST' | 'DRAW' | 'DISCONNECTED' | 'PENDING';
  payout: string;
}

export interface GameState {
  [key: string]: unknown;
}

// ─── Transactions ────────────────────────────────────────────────────────────

export interface Transaction {
  id: string;
  type: string;
  amount: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  description: string;
  reference_id: string;
  created_at: string;
  lottery_name?: string | null;
}

// ─── Notifications ───────────────────────────────────────────────────────────

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

// ─── API Response Wrappers ───────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  error?: string;
  detail?: string;
  [key: string]: unknown;
}

// ─── Game Engine Types ──────────────────────────────────────────────────────

export interface MinesGameState {
  phase: 'betting' | 'playing' | 'cashed_out' | 'exploded' | 'finished';
  grid_size: number;
  mine_count: number;
  revealed: number[];
  bet_amount: string;
  current_multiplier: string;
  payout: string | null;
  user_id: string;
  config: {
    grid_size: number;
    min_mines: number;
    max_mines: number;
    min_bet: string;
    max_bet: string;
    house_edge: string;
  };
}

export interface GameEngine {
  game_kind: string;
  module: string;
  has_default_config?: boolean;
  has_public_state?: boolean;
}

// ─── Payment Request Types ──────────────────────────────────────────────────

export interface DepositRequest {
  amount: number;
  payment_method_id?: string;
  save_payment_method?: boolean;
}

export interface WithdrawalRequest {
  amount: number;
  bank_details?: Record<string, string>;
}

// ─── Audit Types ────────────────────────────────────────────────────────────

export interface AuditLog {
  id: number;
  user: string;
  action: string;
  description: string;
  resource_type: string | null;
  resource_id: string | null;
  changes: Record<string, unknown>;
  timestamp: string;
}

// Scratch Card types
export interface ScratchCardState {
  phase: 'betting' | 'scratching' | 'finished';
  grid_size: number;
  cells: Array<{ value: string | null; revealed: boolean }>;
  revealed_indices: number[];
  bet_amount: string;
  total_prize: string;
  user_id: string;
}

// Slots types
export interface SlotsGameInfo {
  id: string;
  name: string;
  min_bet: string;
  max_bet: string;
  rtp_percent: string;
}

// VIP types
export interface VIPTierInfo {
  id: string;
  name: string;
  level: number;
  cashback_percentage: string;
  benefits: Record<string, unknown>;
}

// Promotion types
export interface PromotionInfo {
  id: string;
  name: string;
  promotion_type: string;
  bonus_percentage: string;
  max_bonus_amount: string;
}
