import React, { useEffect, useState, useCallback } from 'react';
import type { AxiosError } from 'axios';
import { slotsApi, type SlotsGame, type SpinResult, type SpinHistory } from '../api/slots';
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

const SlotsPage: React.FC = () => {
  const [games, setGames] = useState<SlotsGame[]>([]);
  const [selectedGame, setSelectedGame] = useState<SlotsGame | null>(null);
  const [betAmount, setBetAmount] = useState('1.00');
  const [lastSpin, setLastSpin] = useState<SpinResult | null>(null);
  const [history, setHistory] = useState<SpinHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [spinning, setSpinning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    slotsApi.listGames()
      .then((res) => {
        if (mounted) setGames(res.data);
      })
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

  const selectGame = useCallback((game: SlotsGame) => {
    setSelectedGame(game);
    setBetAmount(game.min_bet);
    setLastSpin(null);
    setHistory([]);
    setError(null);
    setHistoryLoading(true);
    slotsApi.getHistory(game.id)
      .then((res) => setHistory(res.data))
      .catch((err: unknown) => setError(getErrorMessage(err)))
      .finally(() => setHistoryLoading(false));
  }, []);

  const handleSpin = useCallback(async () => {
    if (!selectedGame) return;
    setSpinning(true);
    setError(null);
    try {
      const res = await slotsApi.spin(selectedGame.id, betAmount);
      setLastSpin(res.data);
      slotsApi.getHistory(selectedGame.id)
        .then((r) => setHistory(r.data))
        .catch((err: unknown) => setError(getErrorMessage(err)));
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setSpinning(false);
    }
  }, [selectedGame, betAmount]);

  if (loading) return <p style={{ padding: '24px' }}>Loading slots...</p>;

  return (
    <div style={{ padding: '24px', maxWidth: '900px', margin: '0 auto' }}>
      <h1>Slots</h1>

      {error && (
        <div style={{ padding: '12px', background: '#f8d7da', color: '#721c24', borderRadius: '4px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {!selectedGame ? (
        <div>
          <h2>Choose a Game</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px' }}>
            {games.map((g) => (
              <div
                key={g.id}
                onClick={() => selectGame(g)}
                style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '16px', cursor: 'pointer' }}
              >
                <h3 style={{ margin: '0 0 8px' }}>{g.name}</h3>
                <p style={{ margin: '0', fontSize: '14px', color: '#666' }}>{g.description}</p>
                <p style={{ margin: '8px 0 0', fontSize: '13px' }}>
                  Bet: {g.min_bet} – {g.max_bet} | RTP: {g.rtp_percent}%
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div>
          <button onClick={() => setSelectedGame(null)} style={{ marginBottom: '16px', cursor: 'pointer' }}>
            &larr; Back to Games
          </button>
          <h2>{selectedGame.name}</h2>

          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '24px' }}>
            <label>
              Bet:
              <input
                type="number"
                value={betAmount}
                onChange={(e) => setBetAmount(e.target.value)}
                min={selectedGame.min_bet}
                max={selectedGame.max_bet}
                step="0.01"
                style={{ marginLeft: '8px', padding: '8px', width: '120px' }}
              />
            </label>
            <button
              onClick={handleSpin}
              disabled={spinning}
              style={{ padding: '12px 32px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '16px' }}
            >
              {spinning ? 'Spinning...' : 'SPIN'}
            </button>
          </div>

          {lastSpin && (
            <div style={{
              padding: '24px',
              background: lastSpin.won ? '#d4edda' : '#f8d7da',
              borderRadius: '8px',
              marginBottom: '24px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: '48px', marginBottom: '12px' }}>
                {lastSpin.symbols.map((s, i) => (
                  <span key={i} style={{ margin: '0 8px' }}>{s}</span>
                ))}
              </div>
              <p style={{ fontSize: '18px', fontWeight: 'bold' }}>
                {lastSpin.won ? `You won ${lastSpin.payout}!` : 'No win this time'}
              </p>
            </div>
          )}

          {historyLoading && <p>Loading spin history...</p>}

          {history.length > 0 && (
            <div>
              <h3>Recent Spins</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Symbols</th>
                    <th style={{ padding: '8px' }}>Bet</th>
                    <th style={{ padding: '8px' }}>Payout</th>
                    <th style={{ padding: '8px' }}>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {history.slice(0, 10).map((h) => (
                    <tr key={h.id} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '8px' }}>{h.symbols.join(' | ')}</td>
                      <td style={{ padding: '8px' }}>{h.bet_amount}</td>
                      <td style={{ padding: '8px', color: parseFloat(h.payout) > 0 ? 'green' : 'inherit' }}>{h.payout}</td>
                      <td style={{ padding: '8px', fontSize: '12px' }}>{new Date(h.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SlotsPage;
