import React, { useEffect, useState } from 'react';
import type { AxiosError } from 'axios';
import { vipApi, type VIPStatus, type VIPTier } from '../api/vip';
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
    try {
      const res = await vipApi.claimCashback();
      setCashbackMsg(res.data.message);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
      setCashbackMsg('Failed to claim cashback');
    }
  };

  if (loading) return <p style={{ padding: '24px' }}>Loading VIP info...</p>;

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>VIP Program</h1>

      {error && (
        <div style={{ padding: '12px', background: '#f8d7da', color: '#721c24', borderRadius: '4px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {vipStatus && (
        <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '8px', marginBottom: '24px' }}>
          <h2>Your Status: {vipStatus.tier.name}</h2>
          <p><strong>Total Wagered:</strong> {vipStatus.total_wagered}</p>
          <p><strong>Cashback Rate:</strong> {vipStatus.tier.cashback_percentage}%</p>
          {vipStatus.next_tier && (
            <p>
              <strong>Next Tier:</strong> {vipStatus.next_tier.name} –
              Wager {vipStatus.next_tier.remaining} more to unlock
            </p>
          )}
          <button
            onClick={handleCashback}
            style={{ padding: '8px 24px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginTop: '12px' }}
          >
            Claim Weekly Cashback
          </button>
          {cashbackMsg && <p style={{ marginTop: '8px', color: '#28a745' }}>{cashbackMsg}</p>}
        </div>
      )}

      <h2>VIP Tiers</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
            <th style={{ padding: '8px' }}>Tier</th>
            <th style={{ padding: '8px' }}>Level</th>
            <th style={{ padding: '8px' }}>Min Wagered</th>
            <th style={{ padding: '8px' }}>Cashback</th>
            <th style={{ padding: '8px' }}>Withdrawal Multiplier</th>
          </tr>
        </thead>
        <tbody>
          {tiers.map((t) => (
            <tr
              key={t.id}
              style={{
                borderBottom: '1px solid #eee',
                fontWeight: vipStatus?.tier.id === t.id ? 'bold' : 'normal',
                background: vipStatus?.tier.id === t.id ? '#e8f5e9' : 'transparent',
              }}
            >
              <td style={{ padding: '8px' }}>{t.name}</td>
              <td style={{ padding: '8px' }}>{t.level}</td>
              <td style={{ padding: '8px' }}>{t.min_wagered}</td>
              <td style={{ padding: '8px' }}>{t.cashback_percentage}%</td>
              <td style={{ padding: '8px' }}>{t.withdrawal_limit_multiplier}x</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default VIPPage;
