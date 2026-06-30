/**
 * Payments API endpoints.
 */
import apiClient from './client';
import type { PaymentIntent, RazorpayOrder, RazorpayConfig } from '../types';

export const paymentsApi = {
  // Stripe
  createPaymentIntent: (data: { amount: number; payment_method_id?: string }) =>
    apiClient.post<PaymentIntent>('/payments/create-intent/', data),

  confirmPaymentIntent: (data: { payment_intent_id: string; payment_method_id?: string }) =>
    apiClient.post<PaymentIntent>('/payments/confirm-intent/', data),

  getStripeConfig: () =>
    apiClient.get<{ public_key: string; currency: string }>('/payments/config/'),

  // Razorpay
  getRazorpayConfig: () =>
    apiClient.get<RazorpayConfig>('/payments/razorpay/config/'),

  createRazorpayOrder: (data: { amount: number; currency?: string }) =>
    apiClient.post<RazorpayOrder>('/payments/razorpay/create-order/', data),

  verifyRazorpayPayment: (data: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }) =>
    apiClient.post<{ message: string; order_id: string }>('/payments/razorpay/verify/', data),

  // Payment methods
  listPaymentMethods: () =>
    apiClient.get<{ payment_methods: Array<{ id: string; type: string; card: { last4: string; brand: string } | null }> }>('/payments/methods/'),
};
