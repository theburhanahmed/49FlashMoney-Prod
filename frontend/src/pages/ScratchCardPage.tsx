import React, { useState, useCallback } from 'react';
import type { ScratchCardState } from '../types';
import CasinoLayout from '../components/CasinoLayout';
import GlowButton from '../components/GlowButton';

const ScratchCardPage: React.FC = () => {
  const [gameState, setGameState] = useState<ScratchCardState | null>(null);
  const [betAmount, setBetAmount] = useState('5.00');
  const [loading, setLoading] = useState(false);

  const gridSize = gameState?.grid_size ?? 9;
  const gridCols = Math.round(Math.sqrt(gridSize));

  const handleStart = useCallback(async () => {
    setLoading(true);
    try {
      setGameState({
        phase: 'scratching',
        grid_size: 9,
        cells: Array.from({ length: 9 }, () => ({ value: null, revealed: false })),
        revealed_indices: [],
        bet_amount: betAmount,
        total_prize: '0.00',
        user_id: '',
      });
    } finally {
      setLoading(false);
    }
  }, [betAmount]);

  const handleScratch = useCallback((index: number) => {
    if (!gameState || gameState.phase !== 'scratching') return;
    if (gameState.cells[index].revealed) return;

    setGameState((prev) => {
      if (!prev) return prev;
      const newCells = [...prev.cells];
      const prizes = ['2x', '5x', '10x', 'blank', 'bust'];
      const randomPrize = prizes[Math.floor(Math.random() * prizes.length)];
      newCells[index] = { value: randomPrize, revealed: true };
      const newRevealed = [...prev.revealed_indices, index];
      const isBust = randomPrize === 'bust';
      let newPrize = parseFloat(prev.total_prize);
      if (!isBust && randomPrize !== 'blank') {
        const mult = parseFloat(randomPrize.replace('x', ''));
        newPrize += parseFloat(prev.bet_amount) * mult;
      }
      return {
        ...prev,
        cells: newCells,
        revealed_indices: newRevealed,
        total_prize: newPrize.toFixed(2),
        phase: isBust ? 'finished' : prev.phase,
      };
    });
  }, [gameState]);

  const handleCollect = useCallback(() => {
    if (!gameState || gameState.phase !== 'scratching') return;
    setGameState((prev) => prev ? { ...prev, phase: 'finished' } : prev);
  }, [gameState]);

  function getCellStyle(cell: { value: string | null; revealed: boolean }) {
    if (!cell.revealed) return 'border-casino-border bg-card-gradient hover:border-casino-gold hover:shadow-gold cursor-pointer';
    if (cell.value === 'bust') return 'border-casino-red/50 bg-casino-red/10 cursor-default';
    if (cell.value === 'blank') return 'border-casino-border bg-casino-bg cursor-default';
    return 'border-casino-gold/50 bg-casino-gold/10 cursor-default';
  }

  function getCellContent(cell: { value: string | null; revealed: boolean }) {
    if (!cell.revealed) return <span className="text-casino-muted text-2xl font-bold">?</span>;
    if (cell.value === 'bust') return <span className="text-2xl">💥</span>;
    if (cell.value === 'blank') return <span className="text-casino-muted text-lg font-bold">—</span>;
    return <span className="font-display font-bold text-casino-gold text-xl">{cell.value}</span>;
  }

  const wonAmount = gameState ? parseFloat(gameState.total_prize) : 0;
  const isBust = gameState?.phase === 'finished' && wonAmount === 0 && gameState.revealed_indices.length > 0;

  return (
    <CasinoLayout>
      <div className="max-w-lg mx-auto px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="text-4xl">🎟️</div>
          <div>
            <h1 className="font-display text-3xl font-bold text-white">Scratch Card</h1>
            <p className="text-casino-muted text-sm">Scratch and reveal instant prizes</p>
          </div>
        </div>

        {/* Result banner */}
        {gameState?.phase === 'finished' && (
          <div className={`casino-card p-6 text-center ${wonAmount > 0 ? 'border-casino-gold/40 bg-casino-gold/5' : 'border-casino-red/30 bg-casino-red/5'}`}>
            <div className="text-4xl mb-2">{wonAmount > 0 ? '🏆' : isBust ? '💥' : '😔'}</div>
            <p className={`font-display text-2xl font-bold ${wonAmount > 0 ? 'text-casino-gold text-gold-glow' : 'text-casino-red'}`}>
              {wonAmount > 0 ? `You won ${gameState.total_prize}!` : 'Better luck next time!'}
            </p>
          </div>
        )}

        {!gameState || gameState.phase === 'finished' ? (
          /* Buy card form */
          <div className="casino-card p-6 space-y-5">
            <h2 className="section-title">Get Your Card</h2>

            <div>
              <label className="block text-casino-muted text-xs uppercase tracking-wider mb-2">Card Price</label>
              <div className="grid grid-cols-4 gap-2 mb-3">
                {['5', '10', '25', '50'].map((amt) => (
                  <button
                    key={amt}
                    onClick={() => setBetAmount(amt + '.00')}
                    className={`py-2 rounded-lg text-sm font-display font-bold border transition-all ${
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
                max="100"
                step="0.01"
                placeholder="Custom amount"
                className="casino-input"
              />
            </div>

            <GlowButton variant="gold" fullWidth size="lg" onClick={handleStart} disabled={loading}>
              {loading ? 'Getting Card...' : `Buy Card — ${betAmount}`}
            </GlowButton>
          </div>
        ) : (
          /* Active scratch card */
          <div className="space-y-4">
            {/* Stats */}
            <div className="casino-card p-4">
              <div className="flex items-center justify-between">
                <div className="text-center">
                  <p className="text-casino-muted text-xs uppercase tracking-wider">Card Cost</p>
                  <p className="font-display font-bold text-white">{gameState.bet_amount}</p>
                </div>
                <div className="text-center">
                  <p className="text-casino-muted text-xs uppercase tracking-wider">Prize So Far</p>
                  <p className={`font-display font-bold text-lg ${wonAmount > 0 ? 'text-casino-gold' : 'text-white'}`}>
                    {gameState.total_prize}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-casino-muted text-xs uppercase tracking-wider">Scratched</p>
                  <p className="font-display font-bold text-white">
                    {gameState.revealed_indices.length}/{gridSize}
                  </p>
                </div>
              </div>
            </div>

            {/* Collect button */}
            {gameState.phase === 'scratching' && gameState.revealed_indices.length > 0 && (
              <GlowButton variant="green" fullWidth onClick={handleCollect}>
                Collect {gameState.total_prize}
              </GlowButton>
            )}

            {/* Grid */}
            <div
              className="grid gap-3"
              style={{ gridTemplateColumns: `repeat(${gridCols}, 1fr)` }}
            >
              {gameState.cells.map((cell, i) => (
                <button
                  key={i}
                  onClick={() => handleScratch(i)}
                  disabled={cell.revealed}
                  className={`
                    aspect-square rounded-2xl border-2 flex items-center justify-center
                    transition-all duration-200 hover:scale-105 active:scale-95
                    ${getCellStyle(cell)}
                  `}
                >
                  {getCellContent(cell)}
                </button>
              ))}
            </div>

            {/* Hint */}
            {gameState.revealed_indices.length === 0 && (
              <p className="text-center text-casino-muted text-sm">
                Tap any square to reveal your prize!
              </p>
            )}
          </div>
        )}
      </div>
    </CasinoLayout>
  );
};

export default ScratchCardPage;
