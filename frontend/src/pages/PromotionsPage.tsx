import React, { useEffect, useState } from 'react';
import type { AxiosError } from 'axios';
import { promotionsApi, type Promotion, type PromotionClaim } from '../api/promotions';
import type { ApiError } from '../types';

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
    try {
      await promotionsApi.claim(promo.id);
      setClaimMsg(`Successfully claimed "${promo.name}"`);
      setPromotions((prev) => prev.filter((p) => p.id !== promo.id));
      promotionsApi.myClaims()
        .then((r) => setClaims(r.data))
        .catch((err: unknown) => setError(getErrorMessage(err)));
    } catch (err: unknown) {
      setError(getErrorMessage(err));
      setClaimMsg('Failed to claim promotion');
    }
  };

  if (loading) return <p style={{ padding: '24px' }}>Loading promotions...</p>;

  return (
    <div style={{ padding: '24px', maxWidth: '900px', margin: '0 auto' }}>
      <h1>Promotions</h1>

      {error && (
        <div style={{ padding: '12px', background: '#f8d7da', color: '#721c24', borderRadius: '4px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {claimMsg && (
        <div style={{ padding: '12px', background: '#d4edda', borderRadius: '4px', marginBottom: '16px' }}>
          {claimMsg}
        </div>
      )}

      <h2>Available Promotions</h2>
      {promotions.length === 0 ? (
        <p>No promotions available right now.</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px', marginBottom: '32px' }}>
          {promotions.map((p) => (
            <div key={p.id} style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 8px' }}>{p.name}</h3>
              <p style={{ margin: '0 0 8px', fontSize: '14px', color: '#666' }}>{p.description}</p>
              <p style={{ margin: '0 0 4px', fontSize: '13px' }}>
                Type: {p.promotion_type} | Bonus: {p.bonus_percentage}% (max {p.max_bonus_amount})
              </p>
              <p style={{ margin: '0 0 12px', fontSize: '13px' }}>
                Min deposit: {p.min_deposit} | Wagering: {p.wagering_requirement}x
              </p>
              <button
                onClick={() => handleClaim(p)}
                style={{ padding: '8px 20px', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
              >
                Claim
              </button>
            </div>
          ))}
        </div>
      )}

      {claims.length > 0 && (
        <div>
          <h2>My Claims</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                <th style={{ padding: '8px' }}>Promotion</th>
                <th style={{ padding: '8px' }}>Bonus</th>
                <th style={{ padding: '8px' }}>Status</th>
                <th style={{ padding: '8px' }}>Claimed</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((c) => (
                <tr key={c.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '8px' }}>{c.promotion.name}</td>
                  <td style={{ padding: '8px' }}>{c.bonus_amount}</td>
                  <td style={{ padding: '8px' }}>{c.status}</td>
                  <td style={{ padding: '8px', fontSize: '12px' }}>{new Date(c.claimed_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default PromotionsPage;
