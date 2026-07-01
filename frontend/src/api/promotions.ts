import apiClient from './client';

export interface Promotion {
  id: string;
  name: string;
  description?: string;
  promotion_type: string;
  status: string;
  bonus_percentage: string;
  max_bonus_amount: string;
  min_deposit: string;
  wagering_requirement: string;
  start_date: string;
  end_date: string;
}

export interface PromotionClaim {
  id: string;
  promotion_id: string;
  promotion: Promotion;
  bonus_amount: string;
  deposit_amount: string | null;
  wagering_remaining: string;
  status: string;
  claimed_at: string;
}

export const promotionsApi = {
  list: () =>
    apiClient.get<Promotion[]>('/promotions/'),

  claim: (promotionId: string, depositAmount?: number) =>
    apiClient.post<PromotionClaim>(`/promotions/${promotionId}/claim/`, { deposit_amount: depositAmount }),

  myClaims: () =>
    apiClient.get<PromotionClaim[]>('/promotions/my-claims/'),
};
