import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { gamesApi } from '../api/games';
import type { GameKind } from '../types';
import { AxiosError } from 'axios';

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

interface RoomDetail {
  id: string;
  game_kind: GameKind;
  status: string;
  entry_fee: string;
  min_players: number;
  max_players: number;
  created_by: string;
  created_by_username: string;
  config: Record<string, unknown>;
  players: { id: string; user_id: string; username: string; position: number; result: string; payout: string; joined_at: string }[];
  state: unknown;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
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

function getErrorMessage(err: unknown): string {
  if (err instanceof AxiosError && err.response?.data) {
    const data = err.response.data;
    if (typeof data === 'string') return data;
    if (data.error) return data.error;
    if (data.detail) return data.detail;
    return JSON.stringify(data);
  }
  return err instanceof Error ? err.message : 'Unknown error';
}

function GamesPage() {
  const [rooms, setRooms] = useState<RoomListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [newGameKind, setNewGameKind] = useState<GameKind>('SNAKES_LADDERS');
  const [newEntryFee, setNewEntryFee] = useState('10');
  const [creating, setCreating] = useState(false);

  // Room detail view
  const [activeRoom, setActiveRoom] = useState<RoomDetail | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadRooms();
  }, []);

  const loadRooms = async () => {
    setIsLoading(true);
    try {
      const response = await gamesApi.listRooms({ status: 'WAITING' });
      setRooms(response.data as RoomListItem[]);
    } catch {
      setError('Failed to load game rooms');
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoin = async (roomId: string) => {
    setError(null);
    setSuccess(null);
    setActionLoading(true);
    try {
      const response = await gamesApi.joinRoom(roomId);
      setActiveRoom(response.data as unknown as RoomDetail);
      setSuccess('Joined room successfully!');
    } catch (err) {
      setError(`Failed to join: ${getErrorMessage(err)}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleLeave = async () => {
    if (!activeRoom) return;
    setError(null);
    setActionLoading(true);
    try {
      await gamesApi.leaveRoom(activeRoom.id);
      setActiveRoom(null);
      setSuccess('Left room');
      await loadRooms();
    } catch (err) {
      setError(`Failed to leave: ${getErrorMessage(err)}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = async () => {
    if (!activeRoom) return;
    setError(null);
    setActionLoading(true);
    try {
      const response = await gamesApi.startGame(activeRoom.id);
      setActiveRoom(response.data as unknown as RoomDetail);
      setSuccess('Game started!');
    } catch (err) {
      setError(`Failed to start: ${getErrorMessage(err)}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleViewRoom = async (roomId: string) => {
    setError(null);
    try {
      const response = await gamesApi.getRoom(roomId);
      setActiveRoom(response.data as unknown as RoomDetail);
    } catch (err) {
      setError(`Failed to load room: ${getErrorMessage(err)}`);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const response = await gamesApi.createRoom({ game_kind: newGameKind, entry_fee: Number(newEntryFee) });
      setShowCreate(false);
      setActiveRoom(response.data as unknown as RoomDetail);
      setSuccess('Room created! Waiting for players...');
      await loadRooms();
    } catch (err) {
      setError(`Failed to create room: ${getErrorMessage(err)}`);
    } finally {
      setCreating(false);
    }
  };

  // If viewing a room detail
  if (activeRoom) {
    const kindLabel = GAME_KINDS.find((g) => g.value === activeRoom.game_kind)?.label ?? activeRoom.game_kind;
    return (
      <div style={{ maxWidth: 700, margin: '40px auto', padding: 24 }}>
        <button onClick={() => { setActiveRoom(null); setError(null); setSuccess(null); }} style={{ marginBottom: 16, padding: '6px 12px' }}>
          &larr; Back to Rooms
        </button>

        {error && <div style={{ color: 'red', marginBottom: 12, padding: 8, background: '#fee' }}>{error}</div>}
        {success && <div style={{ color: 'green', marginBottom: 12, padding: 8, background: '#efe' }}>{success}</div>}

        <h1>{kindLabel}</h1>
        <p><strong>Status:</strong> {activeRoom.status} | <strong>Entry Fee:</strong> {activeRoom.entry_fee} | <strong>Created by:</strong> {activeRoom.created_by_username}</p>

        <h3>Players ({activeRoom.players.length}/{activeRoom.max_players})</h3>
        {activeRoom.players.length === 0 ? (
          <p>No players yet</p>
        ) : (
          <ul>
            {activeRoom.players.map((p) => (
              <li key={p.id}>
                <strong>{p.username}</strong> - {p.result}
                {p.payout !== '0.00' && ` (payout: ${p.payout})`}
              </li>
            ))}
          </ul>
        )}

        {activeRoom.status === 'WAITING' && (
          <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
            <button
              onClick={handleStart}
              disabled={actionLoading || activeRoom.players.length < activeRoom.min_players}
              style={{ padding: '10px 20px', background: '#28a745', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}
            >
              {actionLoading ? 'Starting...' : `Start Game (need ${activeRoom.min_players}+ players)`}
            </button>
            <button
              onClick={handleLeave}
              disabled={actionLoading}
              style={{ padding: '10px 20px', background: '#dc3545', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}
            >
              Leave Room
            </button>
          </div>
        )}

        {activeRoom.status === 'IN_PROGRESS' && (
          <div style={{ marginTop: 16, padding: 16, background: '#fff3cd', borderRadius: 8 }}>
            <strong>Game in progress!</strong>
            {activeRoom.state != null && <pre style={{ fontSize: 12, overflow: 'auto' }}>{JSON.stringify(activeRoom.state, null, 2)}</pre>}
          </div>
        )}

        {activeRoom.status === 'COMPLETED' && (
          <div style={{ marginTop: 16, padding: 16, background: '#d4edda', borderRadius: 8 }}>
            <strong>Game completed!</strong>
            <p>Results:</p>
            <ul>
              {activeRoom.players.map((p) => (
                <li key={p.id}>{p.username}: {p.result} {p.payout !== '0.00' && `- Won ${p.payout}`}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: '40px auto', padding: 24 }}>
      <nav style={{ marginBottom: 20, display: 'flex', gap: 16 }}>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/wallet">Wallet</Link>
        <Link to="/games">Games</Link>
        <Link to="/games/mines">Mines</Link>
        <Link to="/slots">Slots</Link>
        <Link to="/games/scratch-card">Scratch Card</Link>
      </nav>

      <h1>Games</h1>
      {error && <div style={{ color: 'red', marginBottom: 12, padding: 8, background: '#fee' }}>{error}</div>}
      {success && <div style={{ color: 'green', marginBottom: 12, padding: 8, background: '#efe' }}>{success}</div>}

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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong>{GAME_KINDS.find((g) => g.value === room.game_kind)?.label ?? room.game_kind}</strong>
                  <span style={{ marginLeft: 12, color: '#666' }}>
                    Entry: {room.entry_fee}
                  </span>
                  <span style={{ marginLeft: 12, color: '#999' }}>
                    {room.player_count}/{room.max_players} players
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={() => handleViewRoom(room.id)}
                    style={{ padding: '6px 12px' }}
                  >
                    View
                  </button>
                  <button
                    onClick={() => handleJoin(room.id)}
                    disabled={actionLoading}
                    style={{ padding: '6px 12px', background: '#007bff', color: 'white', border: 'none', borderRadius: 4 }}
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
