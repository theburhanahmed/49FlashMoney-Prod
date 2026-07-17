import React, { useEffect, useState } from 'react';
import type { AxiosError } from 'axios';
import { promotionsApi, type Promotion, type PromotionClaim } from '../api/promotions';
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

const PROMO_TYPE_ICONS: Record<string, string> = {
  DEPOSIT: '💳',
  WELCOME: '🎉',
  RELOAD: '🔄',
  CASHBACK: '💰',
  FREE_SPIN: '🎰',
};

function PromoCard({ promo, onClaim }: { promo: Promotion; onClaim: (p: Promotion) => void }) {
  const icon = PROMO_TYPE_ICONS[promo.promotion_type] ?? '🎁';
  return (
    <div className="casino-card p-5 hover:border-casino-neon/50 hover:shadow-neon transition-all duration-200 flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div className="text-4xl">{icon}</div>
        <span className="text-xs font-bold font-display px-2 py-0.5 rounded-full bg-casino-gold/20 text-casino-gold border border-casino-gold/30 uppercase tracking-wider">
          {promo.promotion_type}
        </span>
      </div>
      <div>
        <h3 className="font-display font-bold text-lg text-white">{promo.name}</h3>
        <p className="text-casino-muted text-sm mt-1 leading-relaxed">{promo.description}</p>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-casino-bg rounded-lg p-2">
          <p className="text-casino-muted uppercase tracking-wider">Bonus</p>
          <p className="font-display font-bold text-casino-green">{promo.bonus_percentage}% up to {promo.max_bonus_amount}</p>
        </div>
        <div className="bg-casino-bg rounded-lg p-2">
          <p className="text-casino-muted uppercase tracking-wider">Min Deposit</p>
          <p className="font-display font-bold text-white">{promo.min_deposit}</p>
        </div>
        <div className="bg-casino-bg rounded-lg p-2 col-span-2">
          <p className="text-casino-muted uppercase tracking-wider">Wagering Requirement</p>
          <p className="font-display font-bold text-casino-neon">{promo.wagering_requirement}x</p>
        </div>
      </div>
      <GlowButton variant="neon" fullWidth onClick={() => onClaim(promo)}>
        Claim Bonus
      </GlowButton>
    </div>
  );
}

function ClaimStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    PENDING: 'bg-casino-gold/20 text-casino-gold border-casino-gold/30',
    ACTIVE: 'bg-casino-green/20 text-casino-green border-casino-green/30',
    COMPLETED: 'bg-casino-muted/20 text-casino-muted border-casino-muted/30',
    EXPIRED: 'bg-casino-red/20 text-casino-red border-casino-red/30',
  };
  return (
    <span className={`text-xs font-bold font-display px-2 py-0.5 rounded-full border uppercase tracking-wider ${colors[status] ?? colors.PENDING}`}>
      {status}
    </span>
  );
}

const PromotionsPage: React.FC = () => {
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [claims, setClaims] = useState<PromotionClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [claimMsg, setClaimMsg] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setError(null);
    Promise.all([
      promotionsApi.list().then((r) => {
        if (mounted) setPromotions(r.data);
      }),
      promotionsApi.myClaims().then((r) => {
        if (mounted) setClaims(r.data);
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

  const handleClaim = async (promo: Promotion) => {
    setError(null);
    setClaimMsg(null);
    try {
      await promotionsApi.claim(promo.id);
      setClaimMsg(`Successfully claimed "${promo.name}"!`);
      setPromotions((prev) => prev.filter((p) => p.id !== promo.id));
      promotionsApi.myClaims()
        .then((r) => setClaims(r.data))
        .catch((err: unknown) => setError(getErrorMessage(err)));
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
            <p className="text-casino-muted">Loading promotions...</p>
          </div>
        </div>
      </CasinoLayout>
    );
  }

  return (
    <CasinoLayout>
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-8">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="text-4xl">🎁</div>
          <div>
            <h1 className="font-display text-3xl font-bold text-white">Promotions</h1>
            <p className="text-casino-muted text-sm">Exclusive bonuses and offers</p>
          </div>
        </div>

        {error && (
          <div className="bg-casino-red/10 border border-casino-red/30 rounded-xl px-4 py-3 text-casino-red text-sm">
            {error}
          </div>
        )}

        {claimMsg && (
          <div className="bg-casino-green/10 border border-casino-green/30 rounded-xl px-4 py-3 text-casino-green text-sm flex items-center gap-2">
            <span>🎉</span>
            {claimMsg}
          </div>
        )}

        {/* Available Promos */}
        <div>
          <h2 className="section-title mb-4">Available Offers</h2>
          {promotions.length === 0 ? (
            <div className="casino-card p-8 text-center">
              <div className="text-4xl mb-3">📭</div>
              <p className="text-casino-muted">No active promotions right now.</p>
              <p className="text-casino-muted text-xs mt-1">Check back soon for new offers!</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {promotions.map((p) => (
                <PromoCard key={p.id} promo={p} onClaim={handleClaim} />
              ))}
            </div>
          )}
        </div>

        {/* My Claims History */}
        {claims.length > 0 && (
          <div>
            <h2 className="section-title mb-4">My Claims</h2>
            <div className="casino-card overflow-hidden">
              <div className="divide-y divide-casino-border/30">
                {claims.map((c) => (
                  <div key={c.id} className="flex items-center justify-between px-4 py-3">
                    <div>
                      <p className="text-white font-medium text-sm">{c.promotion.name}</p>
                      <p className="text-casino-muted text-xs mt-0.5">
                        {new Date(c.claimed_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-casino-gold font-bold text-sm">{c.bonus_amount}</span>
                      <ClaimStatusBadge status={c.status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </CasinoLayout>
  );
};

export default PromotionsPage;
