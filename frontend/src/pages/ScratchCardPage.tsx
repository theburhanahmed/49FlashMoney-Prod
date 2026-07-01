import React, { useState, useCallback } from 'react';
import type { ScratchCardState } from '../types';

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

  return (
    <div style={{ padding: '24px', maxWidth: '600px', margin: '0 auto' }}>
      <h1>Scratch Card</h1>

      {!gameState || gameState.phase === 'finished' ? (
        <div>
          {gameState?.phase === 'finished' && (
            <div style={{
              padding: '16px',
              background: parseFloat(gameState.total_prize) > 0 ? '#d4edda' : '#f8d7da',
              borderRadius: '8px',
              marginBottom: '16px',
              textAlign: 'center',
            }}>
              <strong>
                {parseFloat(gameState.total_prize) > 0
                  ? `You won ${gameState.total_prize}!`
                  : 'Better luck next time!'}
              </strong>
            </div>
          )}
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <label>
              Bet:
              <input
                type="number"
                value={betAmount}
                onChange={(e) => setBetAmount(e.target.value)}
                min="1"
                max="100"
                step="0.01"
                style={{ marginLeft: '8px', padding: '8px', width: '120px' }}
              />
            </label>
            <button
              onClick={handleStart}
              disabled={loading}
              style={{ padding: '8px 24px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              {loading ? 'Starting...' : 'Buy Card'}
            </button>
          </div>
        </div>
      ) : (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div>
              <strong>Bet:</strong> {gameState.bet_amount} |
              <strong> Prize:</strong> {gameState.total_prize} |
              <strong> Scratched:</strong> {gameState.revealed_indices.length}/{gridSize}
            </div>
            <button
              onClick={handleCollect}
              disabled={gameState.revealed_indices.length === 0}
              style={{ padding: '8px 24px', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Collect ({gameState.total_prize})
            </button>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
            gap: '8px',
            maxWidth: '300px',
            margin: '0 auto',
          }}>
            {gameState.cells.map((cell, i) => (
              <button
                key={i}
                onClick={() => handleScratch(i)}
                disabled={cell.revealed}
                style={{
                  width: '100%',
                  aspectRatio: '1',
                  border: '2px solid #ccc',
                  borderRadius: '8px',
                  background: cell.revealed
                    ? cell.value === 'bust' ? '#f8d7da'
                    : cell.value === 'blank' ? '#e9ecef'
                    : '#d4edda'
                    : 'linear-gradient(135deg, #c0c0c0, #d4d4d4)',
                  cursor: cell.revealed ? 'default' : 'pointer',
                  fontSize: '16px',
                  fontWeight: 'bold',
                }}
              >
                {cell.revealed ? (cell.value === 'bust' ? 'X' : cell.value === 'blank' ? '-' : cell.value) : '?'}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ScratchCardPage;
