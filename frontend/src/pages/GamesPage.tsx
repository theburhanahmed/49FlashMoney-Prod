import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { gamesApi } from '../api/games';
import type { GameKind } from '../types';

interface RoomListItem {
  id: string;
  game_kind: GameKind;
  status: string;
  entry_fee: string;
  min_players: number;
  max_players: number;
  created_by_username: string;
  player_count: number;
  created_at: string;
}

const GAME_KINDS: { value: GameKind; label: string }[] = [
  { value: 'SNAKES_LADDERS', label: 'Snakes & Ladders' },
  { value: 'LUDO', label: 'Ludo' },
  { value: 'CARROM', label: 'Carrom' },
  { value: 'AVIATOR', label: 'Aviator' },
  { value: 'WINGO', label: 'Wingo' },
  { value: 'MINES', label: 'Mines' },
  { value: 'SCRATCH_CARD', label: 'Scratch Card' },
];

function GamesPage() {
  const [rooms, setRooms] = useState<RoomListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [newGameKind, setNewGameKind] = useState<GameKind>('SNAKES_LADDERS');
  const [newEntryFee, setNewEntryFee] = useState('10');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadRooms();
  }, []);

  const loadRooms = async () => {
    setIsLoading(true);
    try {
      const response = await gamesApi.listRooms<RoomListItem[]>({ status: 'WAITING' });
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

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await gamesApi.createRoom({ game_kind: newGameKind, entry_fee: Number(newEntryFee) });
      setShowCreate(false);
      await loadRooms();
    } catch {
      setError('Failed to create room');
    } finally {
      setCreating(false);
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

      <div style={{ marginBottom: 20 }}>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{ padding: '8px 16px', fontWeight: 'bold' }}
        >
          {showCreate ? 'Cancel' : 'Create Room'}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} style={{ border: '1px solid #ddd', padding: 16, borderRadius: 8, marginBottom: 20 }}>
          <h3 style={{ marginTop: 0 }}>Create a Game Room</h3>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 4 }}>Game Type</label>
            <select
              value={newGameKind}
              onChange={(e) => setNewGameKind(e.target.value as GameKind)}
              style={{ padding: '6px 10px', width: '100%' }}
            >
              {GAME_KINDS.map((gk) => (
                <option key={gk.value} value={gk.value}>{gk.label}</option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: 'block', marginBottom: 4 }}>Entry Fee</label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={newEntryFee}
              onChange={(e) => setNewEntryFee(e.target.value)}
              style={{ padding: '6px 10px', width: '100%' }}
              required
            />
          </div>
          <button type="submit" disabled={creating} style={{ padding: '8px 16px' }}>
            {creating ? 'Creating...' : 'Create'}
          </button>
        </form>
      )}

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
                  <strong>{GAME_KINDS.find((g) => g.value === room.game_kind)?.label ?? room.game_kind}</strong>
                  <span style={{ marginLeft: 12, color: '#666' }}>
                    Entry: {room.entry_fee}
                  </span>
                </div>
                <div>
                  <span>
                    {room.player_count}/{room.max_players} players
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
