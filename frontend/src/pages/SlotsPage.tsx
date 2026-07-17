import React, { useEffect, useState, useCallback } from 'react';
import type { AxiosError } from 'axios';
import { slotsApi, type SlotsGame, type SpinResult, type SpinHistory } from '../api/slots';
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

  if (loading) {
    return (
      <CasinoLayout>
        <div className="flex items-center justify-center min-h-96">
          <div className="text-center">
            <div className="w-12 h-12 border-2 border-casino-neon border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-casino-muted">Loading slots...</p>
          </div>
        </div>
      </CasinoLayout>
    );
  }

  return (
    <CasinoLayout>
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          {selectedGame && (
            <button
              onClick={() => setSelectedGame(null)}
              className="text-casino-muted hover:text-casino-gold transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
          )}
          <div>
            <h1 className="font-display text-3xl font-bold text-white">
              {selectedGame ? selectedGame.name : 'Slots'}
            </h1>
            <p className="text-casino-muted text-sm mt-0.5">
              {selectedGame ? `Bet: ${selectedGame.min_bet} – ${selectedGame.max_bet} | RTP: ${selectedGame.rtp_percent}%` : 'Provably fair slot machines'}
            </p>
          </div>
        </div>

        {error && (
          <div className="bg-casino-red/10 border border-casino-red/30 rounded-xl px-4 py-3 text-casino-red text-sm">
            {error}
          </div>
        )}

        {!selectedGame ? (
          /* Game selection grid */
          <div>
            <h2 className="section-title mb-4">Choose a Slot</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {games.map((g) => (
                <button
                  key={g.id}
                  onClick={() => selectGame(g)}
                  className="casino-card p-5 text-left hover:border-casino-neon hover:shadow-neon hover:scale-[1.02] transition-all duration-200 group"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="text-4xl">🎰</div>
                    <span className="text-xs font-bold font-display px-2 py-0.5 rounded-full bg-casino-gold/20 text-casino-gold border border-casino-gold/30 uppercase tracking-wider">
                      RTP {g.rtp_percent}%
                    </span>
                  </div>
                  <h3 className="font-display font-bold text-lg text-white group-hover:text-casino-gold transition-colors mb-1">
                    {g.name}
                  </h3>
                  <p className="text-casino-muted text-sm mb-3 line-clamp-2">{g.description}</p>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-casino-muted">Bet range</span>
                    <span className="text-casino-gold font-bold">{g.min_bet} – {g.max_bet}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Game play area */
          <div className="space-y-5">
            {/* Reel display */}
            <div className="casino-card p-6">
              {lastSpin ? (
                <div className={`rounded-2xl p-8 text-center transition-all duration-500 ${lastSpin.won ? 'bg-casino-gold/10 border border-casino-gold/30' : 'bg-casino-red/5 border border-casino-red/20'}`}>
                  <div className="flex items-center justify-center gap-4 mb-4">
                    {lastSpin.symbols.map((s, i) => (
                      <div
                        key={i}
                        className={`w-16 h-16 rounded-2xl border-2 flex items-center justify-center text-3xl
                          ${lastSpin.won ? 'border-casino-gold bg-casino-gold/10' : 'border-casino-border bg-casino-card'}`}
                      >
                        {s}
                      </div>
                    ))}
                  </div>
                  <p className={`font-display font-bold text-2xl ${lastSpin.won ? 'text-casino-gold text-gold-glow' : 'text-casino-muted'}`}>
                    {lastSpin.won ? `You won ${lastSpin.payout}!` : 'No win this time'}
                  </p>
                  {lastSpin.won && (
                    <div className="mt-2 text-casino-green text-sm font-medium">+{lastSpin.payout} added to wallet</div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center gap-4 py-8">
                  {['🎰', '🎰', '🎰'].map((s, i) => (
                    <div key={i} className="w-16 h-16 rounded-2xl border-2 border-casino-border bg-casino-card flex items-center justify-center text-3xl">
                      {spinning ? <div className="w-6 h-6 border-2 border-casino-neon border-t-transparent rounded-full animate-spin" /> : s}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Controls */}
            <div className="casino-card p-5">
              <div className="flex flex-col sm:flex-row items-center gap-4">
                <div className="flex-1 w-full">
                  <label className="block text-casino-muted text-xs uppercase tracking-wider mb-2">Bet Amount</label>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setBetAmount(prev => Math.max(parseFloat(selectedGame.min_bet), parseFloat(prev) / 2).toFixed(2))}
                      className="casino-input w-10 h-10 flex items-center justify-center text-casino-gold font-bold hover:border-casino-gold transition-colors flex-shrink-0"
                    >
                      ½
                    </button>
                    <input
                      type="number"
                      value={betAmount}
                      onChange={(e) => setBetAmount(e.target.value)}
                      min={selectedGame.min_bet}
                      max={selectedGame.max_bet}
                      step="0.01"
                      className="casino-input flex-1"
                    />
                    <button
                      onClick={() => setBetAmount(prev => Math.min(parseFloat(selectedGame.max_bet), parseFloat(prev) * 2).toFixed(2))}
                      className="casino-input w-10 h-10 flex items-center justify-center text-casino-gold font-bold hover:border-casino-gold transition-colors flex-shrink-0"
                    >
                      2×
                    </button>
                  </div>
                </div>
                <GlowButton
                  variant="gold"
                  size="lg"
                  onClick={handleSpin}
                  disabled={spinning}
                  className="w-full sm:w-40 flex-shrink-0"
                >
                  {spinning ? (
                    <span className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-casino-bg border-t-transparent rounded-full animate-spin" />
                      Spinning...
                    </span>
                  ) : 'SPIN'}
                </GlowButton>
              </div>
            </div>

            {/* History */}
            {historyLoading ? (
              <div className="casino-card p-6 text-center">
                <div className="w-6 h-6 border-2 border-casino-neon border-t-transparent rounded-full animate-spin mx-auto" />
              </div>
            ) : history.length > 0 && (
              <div className="casino-card overflow-hidden">
                <div className="p-4 border-b border-casino-border">
                  <h3 className="section-title text-base">Recent Spins</h3>
                </div>
                <div className="divide-y divide-casino-border/30">
                  {history.slice(0, 10).map((h) => (
                    <div key={h.id} className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-3">
                        <span className="text-base">{h.symbols.join(' ')}</span>
                        <span className="text-casino-muted text-xs">
                          {new Date(h.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-sm">
                        <span className="text-casino-muted">Bet: {h.bet_amount}</span>
                        <span className={parseFloat(h.payout) > 0 ? 'text-casino-green font-bold' : 'text-casino-muted'}>
                          {parseFloat(h.payout) > 0 ? `+${h.payout}` : '0.00'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </CasinoLayout>
  );
};

export default SlotsPage;
