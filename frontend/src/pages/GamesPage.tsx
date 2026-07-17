import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gamesApi } from '../api/games';
import type { GameKind } from '../types';
import { AxiosError } from 'axios';
import CasinoLayout from '../components/CasinoLayout';
import GlowButton from '../components/GlowButton';

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

const GAME_KINDS: { value: GameKind; label: string; icon: string; description: string; path?: string }[] = [
  { value: 'SNAKES_LADDERS', label: 'Snakes & Ladders', icon: '🐍', description: 'Classic board game with a twist' },
  { value: 'LUDO', label: 'Ludo', icon: '🎲', description: 'Race to the finish in real-money rooms' },
  { value: 'CARROM', label: 'Carrom', icon: '🎯', description: 'Flick and pocket for big wins' },
  { value: 'AVIATOR', label: 'Aviator', icon: '✈️', description: 'Cash out before the plane flies away' },
  { value: 'WINGO', label: 'Wingo', icon: '🎡', description: 'Predict color or number to win' },
  { value: 'MINES', label: 'Mines', icon: '💣', description: 'Reveal gems, avoid mines', path: '/games/mines' },
  { value: 'SCRATCH_CARD', label: 'Scratch Card', icon: '🎟️', description: 'Instant win scratch cards', path: '/games/scratch-card' },
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

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    WAITING: 'bg-casino-gold/20 text-casino-gold border-casino-gold/30',
    IN_PROGRESS: 'bg-casino-green/20 text-casino-green border-casino-green/30',
    COMPLETED: 'bg-casino-muted/20 text-casino-muted border-casino-muted/30',
  };
  return (
    <span className={`text-xs font-bold font-display px-2 py-0.5 rounded-full border uppercase tracking-wider ${colors[status] ?? colors.COMPLETED}`}>
      {status.replace('_', ' ')}
    </span>
  );
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
  const [activeRoom, setActiveRoom] = useState<RoomDetail | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const navigate = useNavigate();

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

  // Room detail view
  if (activeRoom) {
    const kindData = GAME_KINDS.find((g) => g.value === activeRoom.game_kind);
    const kindLabel = kindData?.label ?? activeRoom.game_kind;
    const kindIcon = kindData?.icon ?? '🎮';
    return (
      <CasinoLayout>
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
          <button
            onClick={() => { setActiveRoom(null); setError(null); setSuccess(null); }}
            className="flex items-center gap-2 text-casino-muted hover:text-casino-gold transition-colors text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Rooms
          </button>

          {error && (
            <div className="bg-casino-red/10 border border-casino-red/30 rounded-xl px-4 py-3 text-casino-red text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="bg-casino-green/10 border border-casino-green/30 rounded-xl px-4 py-3 text-casino-green text-sm">
              {success}
            </div>
          )}

          {/* Room header */}
          <div className="casino-card p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="text-5xl">{kindIcon}</div>
              <div>
                <h1 className="font-display text-3xl font-bold text-white">{kindLabel}</h1>
                <div className="flex items-center gap-3 mt-1">
                  <StatusBadge status={activeRoom.status} />
                  <span className="text-casino-muted text-sm">by {activeRoom.created_by_username}</span>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-casino-border">
              <div className="text-center">
                <p className="text-casino-muted text-xs uppercase tracking-wider">Entry Fee</p>
                <p className="font-display text-xl font-bold text-casino-gold">{activeRoom.entry_fee}</p>
              </div>
              <div className="text-center">
                <p className="text-casino-muted text-xs uppercase tracking-wider">Players</p>
                <p className="font-display text-xl font-bold text-white">
                  {activeRoom.players.length}/{activeRoom.max_players}
                </p>
              </div>
              <div className="text-center">
                <p className="text-casino-muted text-xs uppercase tracking-wider">Min Required</p>
                <p className="font-display text-xl font-bold text-white">{activeRoom.min_players}</p>
              </div>
            </div>
          </div>

          {/* Players list */}
          <div className="casino-card p-6">
            <h3 className="section-title mb-4">Players</h3>
            {activeRoom.players.length === 0 ? (
              <p className="text-casino-muted text-sm">No players yet. Be the first to join!</p>
            ) : (
              <div className="space-y-2">
                {activeRoom.players.map((p, i) => (
                  <div key={p.id} className="flex items-center justify-between p-3 bg-casino-bg rounded-xl border border-casino-border">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-neon-gradient flex items-center justify-center text-white text-sm font-bold">
                        {i + 1}
                      </div>
                      <span className="font-medium text-white">{p.username}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {p.result && <span className="text-casino-muted text-sm">{p.result}</span>}
                      {p.payout !== '0.00' && (
                        <span className="text-casino-gold font-bold text-sm">+{p.payout}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Actions */}
          {activeRoom.status === 'WAITING' && (
            <div className="flex gap-3">
              <GlowButton
                variant="green"
                onClick={handleStart}
                disabled={actionLoading || activeRoom.players.length < activeRoom.min_players}
              >
                {actionLoading ? 'Starting...' : `Start Game (need ${activeRoom.min_players}+)`}
              </GlowButton>
              <GlowButton variant="danger" onClick={handleLeave} disabled={actionLoading}>
                Leave Room
              </GlowButton>
            </div>
          )}

          {activeRoom.status === 'IN_PROGRESS' && (
            <div className="casino-card p-6 border-casino-green/30 bg-casino-green/5">
              <p className="text-casino-green font-display font-bold text-lg mb-3">Game In Progress!</p>
              {activeRoom.state != null && (
                <pre className="text-casino-muted text-xs overflow-auto bg-casino-bg rounded-lg p-3 max-h-60">
                  {JSON.stringify(activeRoom.state, null, 2)}
                </pre>
              )}
            </div>
          )}

          {activeRoom.status === 'COMPLETED' && (
            <div className="casino-card p-6 border-casino-gold/30 bg-casino-gold/5">
              <p className="text-casino-gold font-display font-bold text-lg mb-3">Game Completed!</p>
              <div className="space-y-2">
                {activeRoom.players.map((p) => (
                  <div key={p.id} className="flex items-center justify-between">
                    <span className="text-white">{p.username}</span>
                    <span className={p.payout !== '0.00' ? 'text-casino-green font-bold' : 'text-casino-muted'}>
                      {p.result} {p.payout !== '0.00' && `• Won ${p.payout}`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CasinoLayout>
    );
  }

  return (
    <CasinoLayout>
      <div className="max-w-7xl mx-auto px-4 py-6 space-y-8">
        {/* Page header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold text-white">Games</h1>
            <p className="text-casino-muted text-sm mt-1">Choose a game or join an existing room</p>
          </div>
          <GlowButton variant="gold" size="sm" onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? 'Cancel' : '+ Create Room'}
          </GlowButton>
        </div>

        {error && (
          <div className="bg-casino-red/10 border border-casino-red/30 rounded-xl px-4 py-3 text-casino-red text-sm">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-casino-green/10 border border-casino-green/30 rounded-xl px-4 py-3 text-casino-green text-sm">
            {success}
          </div>
        )}

        {/* Create Room Form */}
        {showCreate && (
          <div className="casino-card p-6">
            <h2 className="section-title mb-5">Create New Room</h2>
            <form onSubmit={handleCreate} className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1">
                <label className="block text-casino-muted text-xs uppercase tracking-wider mb-2">Game Type</label>
                <select
                  value={newGameKind}
                  onChange={(e) => setNewGameKind(e.target.value as GameKind)}
                  className="casino-input"
                >
                  {GAME_KINDS.map((g) => (
                    <option key={g.value} value={g.value}>{g.icon} {g.label}</option>
                  ))}
                </select>
              </div>
              <div className="w-36">
                <label className="block text-casino-muted text-xs uppercase tracking-wider mb-2">Entry Fee</label>
                <input
                  type="number"
                  value={newEntryFee}
                  onChange={(e) => setNewEntryFee(e.target.value)}
                  min="1"
                  step="1"
                  className="casino-input"
                />
              </div>
              <div className="flex items-end">
                <GlowButton type="submit" variant="neon" disabled={creating}>
                  {creating ? 'Creating...' : 'Create'}
                </GlowButton>
              </div>
            </form>
          </div>
        )}

        {/* Game Categories */}
        <div>
          <h2 className="section-title mb-4">All Games</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {GAME_KINDS.map((game) => (
              <button
                key={game.value}
                onClick={() => game.path ? navigate(game.path) : undefined}
                className={`casino-card p-4 text-left transition-all duration-200 hover:border-casino-neon hover:shadow-neon hover:scale-[1.02] active:scale-[0.98] group ${!game.path ? 'opacity-70' : ''}`}
              >
                <div className="text-3xl mb-2 group-hover:scale-110 transition-transform">{game.icon}</div>
                <h3 className="font-display font-bold text-white group-hover:text-casino-gold transition-colors text-sm">{game.label}</h3>
                <p className="text-casino-muted text-xs mt-1 leading-relaxed">{game.description}</p>
                {!game.path && (
                  <span className="text-xs text-casino-neon mt-2 block">Use room list ↓</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Live Rooms */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">Open Rooms</h2>
            <button
              onClick={loadRooms}
              className="text-casino-muted hover:text-casino-gold text-sm transition-colors flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
          </div>

          {isLoading ? (
            <div className="casino-card p-8 text-center">
              <div className="w-8 h-8 border-2 border-casino-neon border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-casino-muted text-sm">Loading rooms...</p>
            </div>
          ) : rooms.length === 0 ? (
            <div className="casino-card p-8 text-center">
              <div className="text-4xl mb-3">🎮</div>
              <p className="text-casino-muted text-sm">No open rooms right now.</p>
              <p className="text-casino-muted text-xs mt-1">Create one to get started!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {rooms.map((room) => {
                const gameData = GAME_KINDS.find((g) => g.value === room.game_kind);
                return (
                  <div key={room.id} className="casino-card p-4 flex items-center justify-between hover:border-casino-gold/50 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className="text-3xl">{gameData?.icon ?? '🎮'}</div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-display font-bold text-white">{gameData?.label ?? room.game_kind}</h3>
                          <StatusBadge status={room.status} />
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-casino-muted text-xs">
                          <span>by {room.created_by_username}</span>
                          <span>•</span>
                          <span className="text-casino-gold font-bold">Entry: {room.entry_fee}</span>
                          <span>•</span>
                          <span>{room.player_count}/{room.max_players} players</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <GlowButton variant="ghost" size="sm" onClick={() => handleViewRoom(room.id)}>
                        View
                      </GlowButton>
                      <GlowButton variant="gold" size="sm" onClick={() => handleJoin(room.id)} disabled={actionLoading}>
                        Join
                      </GlowButton>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </CasinoLayout>
  );
}

export default GamesPage;
