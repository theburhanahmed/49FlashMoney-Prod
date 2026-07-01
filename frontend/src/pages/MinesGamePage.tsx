import React, { useState, useCallback } from 'react';
import type { MinesGameState } from '../types';

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

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Mines</h1>

      {error && <div style={{ color: 'red', marginBottom: '16px' }}>{error}</div>}

      {!gameState || gameState.phase === 'finished' ? (
        <div style={{ marginBottom: '24px' }}>
          <h2>Place Your Bet</h2>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '16px' }}>
            <label>
              Bet Amount:
              <input
                type="number"
                value={betAmount}
                onChange={(e) => setBetAmount(e.target.value)}
                min="1"
                max="500"
                step="0.01"
                style={{ marginLeft: '8px', padding: '8px', width: '120px' }}
              />
            </label>
            <label>
              Mines:
              <input
                type="number"
                value={mineCount}
                onChange={(e) => setMineCount(parseInt(e.target.value))}
                min="1"
                max="24"
                style={{ marginLeft: '8px', padding: '8px', width: '80px' }}
              />
            </label>
            <button
              onClick={handleStartGame}
              disabled={loading}
              style={{ padding: '8px 24px', background: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              {loading ? 'Starting...' : 'Start Game'}
            </button>
          </div>
          {gameState?.phase === 'finished' && gameState.payout && (
            <div style={{ padding: '16px', background: '#d4edda', borderRadius: '8px', marginTop: '16px' }}>
              <strong>You won {gameState.payout}!</strong>
            </div>
          )}
        </div>
      ) : (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div>
              <strong>Bet:</strong> {gameState.bet_amount} |
              <strong> Multiplier:</strong> {gameState.current_multiplier}x |
              <strong> Revealed:</strong> {gameState.revealed.length}
            </div>
            <button
              onClick={handleCashOut}
              disabled={gameState.revealed.length === 0}
              style={{ padding: '8px 24px', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Cash Out ({(parseFloat(gameState.bet_amount) * parseFloat(gameState.current_multiplier)).toFixed(2)})
            </button>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
              gap: '4px',
              maxWidth: '400px',
            }}
          >
            {Array.from({ length: gridSize }, (_, i) => {
              const isRevealed = gameState.revealed.includes(i);
              return (
                <button
                  key={i}
                  onClick={() => handleRevealTile(i)}
                  disabled={isRevealed}
                  style={{
                    width: '100%',
                    aspectRatio: '1',
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                    background: isRevealed ? '#d4edda' : '#f8f9fa',
                    cursor: isRevealed ? 'default' : 'pointer',
                    fontSize: '18px',
                  }}
                >
                  {isRevealed ? '\u{1F48E}' : '?'}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default MinesGamePage;
