import apiClient from './client';

export interface GameMetrics {
  total_bets: string;
  total_payouts: string;
  ggr: string;
  ngr: string;
  rtp: string;
  bonuses_paid: string;
  game_breakdown: Record<string, { rooms: number; players: number }>;
  slots: {
    total_spins: number;
    total_wagered: string;
    total_paid: string;
    rtp: string;
  };
  period: { start_date: string; end_date: string };
}

export interface Period {
  start_date: string;
  end_date: string;
}

export interface FinancialMetrics {
  revenue: string;
  deposits: string;
  withdrawals: string;
  prizes_awarded: string;
  net_revenue: string;
  period: Period;
}

export interface UserMetrics {
  total_users: number;
  active_users: number;
  new_registrations: number;
  users_with_tickets: number;
  period: Period;
}

export interface LotteryMetrics {
  active_lotteries: number;
  completed_lotteries: number;
  tickets_sold: number;
  revenue: string;
  period: Period;
}

export interface DashboardMetrics {
  financial: FinancialMetrics;
  users: UserMetrics;
  lotteries: LotteryMetrics;
}

export interface ChartDataPoint {
  date: string;
  value: number;
}

export interface ChartMetrics {
  type: string;
  period: string;
  days: number;
  data: ChartDataPoint[];
}

export const analyticsApi = {
  getDashboard: (days?: number) =>
    apiClient.get<DashboardMetrics>('/analytics/admin/analytics/dashboard/', { params: { days } }),

  getFinancial: (startDate?: string, endDate?: string) =>
    apiClient.get<FinancialMetrics>('/analytics/admin/analytics/financial/', { params: { start_date: startDate, end_date: endDate } }),

  getGameMetrics: (startDate?: string, endDate?: string) =>
    apiClient.get<GameMetrics>('/analytics/admin/analytics/games/', { params: { start_date: startDate, end_date: endDate } }),

  getCharts: (type: string, period?: string, days?: number) =>
    apiClient.get<ChartMetrics>('/analytics/admin/analytics/charts/', { params: { type, period, days } }),
};
