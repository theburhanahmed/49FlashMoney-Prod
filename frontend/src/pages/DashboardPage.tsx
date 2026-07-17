import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useWalletStore } from '../store/walletStore';
import CasinoLayout from '../components/CasinoLayout';
import GameTile from '../components/GameTile';
import GlowButton from '../components/GlowButton';

const FEATURED_GAMES = [
  {
    name: 'Mines',
    description: 'Reveal gems, avoid mines. The more you risk, the higher the reward.',
    icon: '💣',
    badge: 'Hot',
    badgeColor: 'pink' as const,
    path: '/games/mines',
  },
  {
    name: 'Slots',
    description: 'Spin to win with provably fair RNG slot machines.',
    icon: '🎰',
    badge: 'Popular',
    badgeColor: 'gold' as const,
    path: '/slots',
  },
  {
    name: 'Scratch Card',
    description: 'Instant win scratch cards with big multipliers.',
    icon: '🎟️',
    badge: 'Instant',
    badgeColor: 'green' as const,
    path: '/games/scratch-card',
  },
  {
    name: 'Aviator',
    description: 'Watch the multiplier fly — cash out before it crashes!',
    icon: '✈️',
    badge: 'Live',
    badgeColor: 'neon' as const,
    path: '/games',
  },
  {
    name: 'Wingo',
    description: 'Predict the winning color or number and multiply your bet.',
    icon: '🎡',
    badge: null,
    badgeColor: 'gold' as const,
    path: '/games',
  },
  {
    name: 'Ludo',
    description: 'Classic board game with real-money rooms.',
    icon: '🎲',
    badge: null,
    badgeColor: 'gold' as const,
    path: '/games',
  },
];

function DashboardPage() {
  const { user } = useAuthStore();
  const { wallet, fetchWallet } = useWalletStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchWallet();
  }, [fetchWallet]);

  return (
    <CasinoLayout>
      <div className="max-w-7xl mx-auto px-4 py-6 space-y-8">
        {/* Welcome Banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-casino-card via-[#1d0840] to-casino-card border border-casino-border p-6">
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute -right-20 -top-20 w-64 h-64 rounded-full bg-casino-gold/10 blur-3xl" />
            <div className="absolute -left-10 -bottom-10 w-48 h-48 rounded-full bg-casino-neon/10 blur-3xl" />
          </div>
          <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <p className="text-casino-muted text-sm font-medium uppercase tracking-wider mb-1">Welcome back</p>
              <h1 className="font-display text-3xl font-bold text-white">
                {user?.username ?? 'Player'}
                <span className="text-casino-gold text-gold-glow ml-2">!</span>
              </h1>
              <p className="text-casino-muted text-sm mt-2">Ready to play? Your luck awaits.</p>
            </div>
            <div className="flex gap-3">
              <GlowButton variant="gold" size="sm" onClick={() => navigate('/wallet')}>
                Deposit
              </GlowButton>
              <GlowButton variant="ghost" size="sm" onClick={() => navigate('/games')}>
                All Games
              </GlowButton>
            </div>
          </div>
        </div>

        {/* Wallet Stats */}
        {wallet && (
          <div>
            <h2 className="section-title mb-4">Your Wallet</h2>
            <div className="grid grid-cols-3 gap-3">
              <div className="casino-card p-4 text-center">
                <p className="text-casino-muted text-xs uppercase tracking-wider mb-1">Balance</p>
                <p className="font-display text-xl font-bold text-casino-gold">
                  {wallet.currency} {parseFloat(wallet.balance).toFixed(2)}
                </p>
              </div>
              <div className="casino-card p-4 text-center">
                <p className="text-casino-muted text-xs uppercase tracking-wider mb-1">Available</p>
                <p className="font-display text-xl font-bold text-casino-green">
                  {parseFloat(wallet.available_balance).toFixed(2)}
                </p>
              </div>
              <div className="casino-card p-4 text-center">
                <p className="text-casino-muted text-xs uppercase tracking-wider mb-1">Reserved</p>
                <p className="font-display text-xl font-bold text-casino-neon">
                  {parseFloat(wallet.reserved_balance).toFixed(2)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div>
          <h2 className="section-title mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Deposit', icon: '💳', path: '/wallet', variant: 'gold' as const },
              { label: 'Withdraw', icon: '🏦', path: '/wallet', variant: 'ghost' as const },
              { label: 'Promotions', icon: '🎁', path: '/promotions', variant: 'neon' as const },
              { label: 'VIP Club', icon: '👑', path: '/vip', variant: 'ghost' as const },
            ].map((action) => (
              <button
                key={action.label}
                onClick={() => navigate(action.path)}
                className="casino-card p-4 flex flex-col items-center gap-2 hover:border-casino-gold hover:shadow-gold transition-all duration-200 group"
              >
                <span className="text-2xl group-hover:scale-110 transition-transform">{action.icon}</span>
                <span className="font-display font-semibold text-sm text-casino-text group-hover:text-casino-gold transition-colors">
                  {action.label}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Featured Games */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">Featured Games</h2>
            <button
              onClick={() => navigate('/games')}
              className="text-casino-neon hover:text-casino-violet-light text-sm font-medium transition-colors"
            >
              View All →
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {FEATURED_GAMES.map((game) => (
              <GameTile
                key={game.name}
                name={game.name}
                description={game.description}
                icon={game.icon}
                badge={game.badge ?? undefined}
                badgeColor={game.badgeColor}
                onClick={() => navigate(game.path)}
              />
            ))}
          </div>
        </div>

        {/* Promo Banner */}
        <div
          className="relative overflow-hidden rounded-2xl cursor-pointer group"
          onClick={() => navigate('/promotions')}
        >
          <div className="absolute inset-0 bg-pink-gradient opacity-20 group-hover:opacity-30 transition-opacity" />
          <div className="relative border border-casino-neon-pink/30 rounded-2xl p-6 flex items-center justify-between">
            <div>
              <p className="text-casino-neon-pink font-display font-bold text-lg">Weekly Bonus</p>
              <p className="text-casino-muted text-sm mt-1">Claim your weekly cashback and deposit bonuses</p>
            </div>
            <div className="text-4xl group-hover:scale-110 transition-transform">🎁</div>
          </div>
        </div>
      </div>
    </CasinoLayout>
  );
}

export default DashboardPage;
