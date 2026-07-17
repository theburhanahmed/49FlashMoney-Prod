import React, { useState, useCallback } from 'react';
import type { MinesGameState } from '../types';
import CasinoLayout from '../components/CasinoLayout';
import GlowButton from '../components/GlowButton';

const MinesGamePage: React.FC = () => {
  const [gameState, setGameState] = useState<MinesGameState | null>(null);
  const [betAmount, setBetAmount] = useState('10.00');
  const [mineCount, setMineCount] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const gridSize = gameState?.grid_size ?? 25;
  const gridCols = Math.round(Math.sqrt(gridSize));

  const handleStartGame = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // This would connect to the game WebSocket/API
      // For now, show a placeholder state
      setGameState({
        phase: 'playing',
        grid_size: 25,
        mine_count: mineCount,
        revealed: [],
        bet_amount: betAmount,
        current_multiplier: '1.00',
        payout: null,
        user_id: '',
        config: {
          grid_size: 25,
          min_mines: 1,
          max_mines: 24,
          min_bet: '1.00',
          max_bet: '500.00',
          house_edge: '0.02',
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start game');
    } finally {
      setLoading(false);
    }
  }, [betAmount, mineCount]);

  const handleRevealTile = useCallback((tileIndex: number) => {
    if (!gameState || gameState.phase !== 'playing') return;
    if (gameState.revealed.includes(tileIndex)) return;

    // In production this would send an action to the WebSocket
    setGameState((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        revealed: [...prev.revealed, tileIndex],
        current_multiplier: (parseFloat(prev.current_multiplier) * 1.15).toFixed(2),
      };
    });
  }, [gameState]);

  const handleCashOut = useCallback(() => {
    if (!gameState || gameState.phase !== 'playing') return;
    if (gameState.revealed.length === 0) return;

    const payout = (parseFloat(gameState.bet_amount) * parseFloat(gameState.current_multiplier)).toFixed(2);
    setGameState((prev) => prev ? { ...prev, phase: 'finished', payout } : prev);
  }, [gameState]);

  const currentPayout = gameState
    ? (parseFloat(gameState.bet_amount) * parseFloat(gameState.current_multiplier)).toFixed(2)
    : '0.00';

  return (
    <CasinoLayout>
      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="text-4xl">💣</div>
          <div>
            <h1 className="font-display text-3xl font-bold text-white">Mines</h1>
            <p className="text-casino-muted text-sm">Reveal gems. Avoid mines. Multiply your bet.</p>
          </div>
        </div>

        {error && (
          <div className="bg-casino-red/10 border border-casino-red/30 rounded-xl px-4 py-3 text-casino-red text-sm">
            {error}
          </div>
        )}

        {!gameState || gameState.phase === 'finished' ? (
          /* Bet placement */
          <div className="space-y-4">
            {gameState?.phase === 'finished' && gameState.payout && (
              <div className="casino-card p-6 text-center border-casino-gold/30 bg-casino-gold/5">
                <div className="text-4xl mb-2">💎</div>
                <p className="font-display text-2xl font-bold text-casino-gold text-gold-glow">
                  You won {gameState.payout}!
                </p>
                <p className="text-casino-muted text-sm mt-1">
                  Multiplier: {gameState.current_multiplier}x
                </p>
              </div>
            )}

            <div className="casino-card p-6 space-y-5">
              <h2 className="section-title">Place Your Bet</h2>

              <div>
                <label className="block text-casino-muted text-xs uppercase tracking-wider mb-2">Bet Amount</label>
                <div className="flex items-center gap-2">
                  {['5', '10', '25', '50'].map((amt) => (
                    <button
                      key={amt}
                      onClick={() => setBetAmount(amt + '.00')}
                      className={`px-3 py-2 rounded-lg text-sm font-display font-bold transition-all border ${
                        betAmount === amt + '.00'
                          ? 'bg-casino-gold text-casino-bg border-casino-gold'
                          : 'border-casino-border text-casino-muted hover:border-casino-gold hover:text-casino-gold'
                      }`}
                    >
                      {amt}
                    </button>
                  ))}
                </div>
                <input
                  type="number"
                  value={betAmount}
                  onChange={(e) => setBetAmount(e.target.value)}
                  min="1"
                  max="500"
                  step="0.01"
                  placeholder="Custom amount"
                  className="casino-input mt-2"
                />
              </div>

              <div>
                <label className="block text-casino-muted text-xs uppercase tracking-wider mb-2">
                  Number of Mines: <span className="text-casino-red font-bold">{mineCount}</span>
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    value={mineCount}
                    onChange={(e) => setMineCount(parseInt(e.target.value))}
                    min="1"
                    max="24"
                    className="flex-1 accent-casino-neon"
                  />
                  <input
                    type="number"
                    value={mineCount}
                    onChange={(e) => setMineCount(parseInt(e.target.value))}
                    min="1"
                    max="24"
                    className="casino-input w-16 text-center"
                  />
                </div>
                <p className="text-casino-muted text-xs mt-1">
                  More mines = higher risk & higher reward
                </p>
              </div>

              <GlowButton
                variant="gold"
                fullWidth
                onClick={handleStartGame}
                disabled={loading}
                size="lg"
              >
                {loading ? 'Starting...' : `Start Game — Bet ${betAmount}`}
              </GlowButton>
            </div>
          </div>
        ) : (
          /* Active game */
          <div className="space-y-4">
            {/* Live stats bar */}
            <div className="casino-card p-4">
              <div className="flex items-center justify-between gap-4">
                <div className="text-center">
                  <p className="text-casino-muted text-xs uppercase tracking-wider">Bet</p>
                  <p className="font-display text-lg font-bold text-white">{gameState.bet_amount}</p>
                </div>
                <div className="text-center">
                  <p className="text-casino-muted text-xs uppercase tracking-wider">Multiplier</p>
                  <p className="font-display text-lg font-bold text-casino-neon text-neon-glow">
                    {gameState.current_multiplier}x
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-casino-muted text-xs uppercase tracking-wider">Gems Found</p>
                  <p className="font-display text-lg font-bold text-casino-green">
                    {gameState.revealed.length}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-casino-muted text-xs uppercase tracking-wider">Mines</p>
                  <p className="font-display text-lg font-bold text-casino-red">
                    {mineCount}
                  </p>
                </div>
              </div>
            </div>

            {/* Cash out button */}
            <GlowButton
              variant="green"
              fullWidth
              size="lg"
              onClick={handleCashOut}
              disabled={gameState.revealed.length === 0}
            >
              Cash Out — Win {currentPayout}
            </GlowButton>

            {/* Mine grid */}
            <div
              className="grid gap-2"
              style={{ gridTemplateColumns: `repeat(${gridCols}, 1fr)` }}
            >
              {Array.from({ length: gridSize }, (_, i) => {
                const isRevealed = gameState.revealed.includes(i);
                return (
                  <button
                    key={i}
                    onClick={() => handleRevealTile(i)}
                    disabled={isRevealed}
                    className={`
                      aspect-square rounded-xl border-2 flex items-center justify-center text-lg
                      font-bold transition-all duration-150
                      ${isRevealed
                        ? 'border-casino-green/50 bg-casino-green/10 text-casino-green cursor-default scale-95'
                        : 'border-casino-border bg-casino-card hover:border-casino-neon hover:shadow-neon hover:scale-105 active:scale-95 cursor-pointer'}
                    `}
                  >
                    {isRevealed ? '💎' : '?'}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </CasinoLayout>
  );
};

export default MinesGamePage;
