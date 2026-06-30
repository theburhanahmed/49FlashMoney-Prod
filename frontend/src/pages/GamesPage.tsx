import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { gamesApi } from '../api/games';
import type { GameRoom } from '../types';

function GamesPage() {
  const [rooms, setRooms] = useState<GameRoom[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRooms();
  }, []);

  const loadRooms = async () => {
    setIsLoading(true);
    try {
      const response = await gamesApi.listRooms({ status: 'WAITING' });
      setRooms(response.data);
    } catch {
      setError('Failed to load game rooms');
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoin = async (roomId: string) => {
    try {
      await gamesApi.joinRoom(roomId);
      await loadRooms();
    } catch {
      setError('Failed to join room');
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', padding: 24 }}>
      <nav style={{ marginBottom: 20, display: 'flex', gap: 16 }}>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/wallet">Wallet</Link>
        <Link to="/games">Games</Link>
      </nav>

      <h1>Games</h1>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}

      <h2>Available Rooms</h2>
      {isLoading ? (
        <p>Loading...</p>
      ) : rooms.length === 0 ? (
        <p>No rooms available. Create one!</p>
      ) : (
        <div style={{ display: 'grid', gap: 12 }}>
          {rooms.map((room) => (
            <div
              key={room.id}
              style={{ border: '1px solid #ddd', padding: 16, borderRadius: 8 }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div>
                  <strong>{room.game_kind}</strong>
                  <span style={{ marginLeft: 12, color: '#666' }}>
                    Entry: {room.entry_fee}
                  </span>
                </div>
                <div>
                  <span>
                    {room.players.length}/{room.max_players} players
                  </span>
                  <button
                    onClick={() => handleJoin(room.id)}
                    style={{ marginLeft: 12, padding: '6px 12px' }}
                  >
                    Join
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default GamesPage;
