import React, { useEffect, useState } from 'react';
import type { AxiosError } from 'axios';
import { vipApi, type VIPStatus, type VIPTier } from '../api/vip';
import type { ApiError } from '../types';
import CasinoLayout from '../components/CasinoLayout';
import GlowButton from '../components/GlowButton';

const getErrorMessage = (err: unknown): string => {
  if (err && typeof err === 'object' && 'response' in err) {
    const axiosErr = err as AxiosError<ApiError>;
    const data = axiosErr.response?.data;
    if (data && typeof data === 'object') {
      return data.error || data.detail || 'An unexpected error occurred.';
    }
  }
  if (err instanceof Error) return err.message;
  return 'An unexpected error occurred.';
};

const TIER_ICONS = ['🥉', '🥈', '🥇', '💎', '👑'];
const TIER_GRADIENTS = [
  'from-amber-700 to-amber-500',
  'from-slate-400 to-slate-300',
  'from-yellow-500 to-yellow-300',
  'from-cyan-400 to-cyan-200',
  'from-purple-500 to-casino-gold',
];

const VIPPage: React.FC = () => {
  const [vipStatus, setVIPStatus] = useState<VIPStatus | null>(null);
  const [tiers, setTiers] = useState<VIPTier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cashbackMsg, setCashbackMsg] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setError(null);
    Promise.all([
      vipApi.getStatus().then((r) => {
        if (mounted) setVIPStatus(r.data);
      }),
      vipApi.getTiers().then((r) => {
        if (mounted) setTiers(r.data);
      }),
    ])
      .catch((err: unknown) => {
        if (mounted) setError(getErrorMessage(err));
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleCashback = async () => {
    setError(null);
    setCashbackMsg(null);
    try {
      const res = await vipApi.claimCashback();
      setCashbackMsg(res.data.message);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    }
  };

  if (loading) {
    return (
      <CasinoLayout>
        <div className="flex items-center justify-center min-h-96">
          <div className="text-center">
            <div className="w-12 h-12 border-2 border-casino-neon border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-casino-muted">Loading VIP info...</p>
          </div>
        </div>
      </CasinoLayout>
    );
  }

  const currentTierIndex = vipStatus ? tiers.findIndex((t) => t.id === vipStatus.tier.id) : -1;
  const progress = vipStatus && vipStatus.next_tier
    ? 100 - (parseFloat(vipStatus.next_tier.remaining) / (parseFloat(vipStatus.next_tier.min_wagered) - parseFloat(vipStatus.tier.min_wagered ?? '0'))) * 100
    : vipStatus ? 100 : 0;

  return (
    <CasinoLayout>
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="text-4xl">👑</div>
          <div>
            <h1 className="font-display text-3xl font-bold text-white">VIP Club</h1>
            <p className="text-casino-muted text-sm">Exclusive rewards for loyal players</p>
          </div>
        </div>

        {error && (
          <div className="bg-casino-red/10 border border-casino-red/30 rounded-xl px-4 py-3 text-casino-red text-sm">
            {error}
          </div>
        )}

        {cashbackMsg && (
          <div className="bg-casino-green/10 border border-casino-green/30 rounded-xl px-4 py-3 text-casino-green text-sm">
            {cashbackMsg}
          </div>
        )}

        {/* Current Status */}
        {vipStatus && (
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#2a1060] via-casino-card to-[#0e0620] border border-casino-neon/30 p-6">
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
              <div className="absolute -right-10 -top-10 w-48 h-48 rounded-full bg-casino-gold/10 blur-3xl" />
            </div>
            <div className="relative">
              <div className="flex items-center gap-4 mb-5">
                <div className="text-5xl">
                  {TIER_ICONS[currentTierIndex] ?? '⭐'}
                </div>
                <div>
                  <p className="text-casino-muted text-xs uppercase tracking-wider">Current Tier</p>
                  <h2 className="font-display text-2xl font-bold text-casino-gold text-gold-glow">
                    {vipStatus.tier.name}
                  </h2>
                  <p className="text-casino-muted text-sm">
                    Total Wagered: <span className="text-white font-bold">{vipStatus.total_wagered}</span>
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-5">
                <div className="bg-casino-bg/50 rounded-xl p-3">
                  <p className="text-casino-muted text-xs uppercase tracking-wider mb-1">Cashback Rate</p>
                  <p className="font-display text-2xl font-bold text-casino-green">
                    {vipStatus.tier.cashback_percentage}%
                  </p>
                </div>
                <div className="bg-casino-bg/50 rounded-xl p-3">
                  <p className="text-casino-muted text-xs uppercase tracking-wider mb-1">Withdrawal Limit</p>
                  <p className="font-display text-2xl font-bold text-casino-neon">
                    {vipStatus.tier.withdrawal_limit_multiplier}x
                  </p>
                </div>
              </div>

              {/* Progress to next tier */}
              {vipStatus.next_tier && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-casino-muted text-xs uppercase tracking-wider">Progress to {vipStatus.next_tier.name}</span>
                    <span className="text-casino-gold text-xs font-bold">{vipStatus.next_tier.remaining} to go</span>
                  </div>
                  <div className="h-2 bg-casino-bg rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gold-gradient rounded-full transition-all duration-500"
                      style={{ width: `${Math.max(5, Math.min(100, progress))}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="mt-5">
                <GlowButton variant="gold" onClick={handleCashback}>
                  Claim Weekly Cashback
                </GlowButton>
              </div>
            </div>
          </div>
        )}

        {/* VIP Tiers */}
        <div>
          <h2 className="section-title mb-4">All VIP Tiers</h2>
          <div className="space-y-3">
            {tiers.map((t, i) => {
              const isCurrent = vipStatus?.tier.id === t.id;
              return (
                <div
                  key={t.id}
                  className={`casino-card p-4 transition-all duration-200 ${
                    isCurrent ? 'border-casino-gold border-glow-gold' : 'hover:border-casino-border/80'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${TIER_GRADIENTS[i] ?? 'from-casino-neon to-casino-violet'} flex items-center justify-center text-xl`}>
                      {TIER_ICONS[i] ?? '⭐'}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-display font-bold text-white">{t.name}</h3>
                        {isCurrent && (
                          <span className="text-xs font-bold font-display px-2 py-0.5 rounded-full bg-casino-gold/20 text-casino-gold border border-casino-gold/30 uppercase">
                            Current
                          </span>
                        )}
                      </div>
                      <p className="text-casino-muted text-xs mt-0.5">Min wagered: {t.min_wagered}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-casino-green font-display font-bold">{t.cashback_percentage}%</p>
                      <p className="text-casino-muted text-xs">cashback</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </CasinoLayout>
  );
};

export default VIPPage;
