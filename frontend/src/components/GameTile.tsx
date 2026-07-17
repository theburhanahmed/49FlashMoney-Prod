import type { ReactNode } from 'react';

interface GameTileProps {
  name: string;
  description?: string;
  icon: ReactNode;
  badge?: string;
  badgeColor?: 'gold' | 'neon' | 'green' | 'pink';
  onClick?: () => void;
  disabled?: boolean;
  gradient?: string;
}

const BADGE_COLORS = {
  gold: 'bg-casino-gold text-casino-bg',
  neon: 'bg-casino-neon text-white',
  green: 'bg-casino-green text-casino-bg',
  pink: 'bg-casino-neon-pink text-white',
};

function GameTile({
  name,
  description,
  icon,
  badge,
  badgeColor = 'gold',
  onClick,
  disabled = false,
  gradient,
}: GameTileProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        relative overflow-hidden rounded-2xl border border-casino-border
        transition-all duration-300 text-left group
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-casino-neon hover:shadow-neon hover:scale-[1.02] active:scale-[0.98]'}
        ${gradient ?? 'bg-card-gradient'}
        shadow-card
      `}
    >
      {/* Shimmer overlay on hover */}
      {!disabled && (
        <div className="absolute inset-0 bg-gradient-to-tr from-white/0 via-white/5 to-white/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
      )}

      <div className="p-4 flex flex-col gap-3">
        {/* Icon area */}
        <div className="flex items-start justify-between">
          <div className="text-4xl leading-none">{icon}</div>
          {badge && (
            <span className={`text-xs font-bold font-display px-2 py-0.5 rounded-full uppercase tracking-wider ${BADGE_COLORS[badgeColor]}`}>
              {badge}
            </span>
          )}
        </div>

        {/* Info */}
        <div>
          <h3 className="font-display font-bold text-lg text-white leading-tight group-hover:text-casino-gold transition-colors">
            {name}
          </h3>
          {description && (
            <p className="text-casino-muted text-xs mt-1 leading-relaxed line-clamp-2">{description}</p>
          )}
        </div>

        {/* Play indicator */}
        {!disabled && (
          <div className="flex items-center gap-1 text-casino-neon text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
            </svg>
            Play Now
          </div>
        )}
      </div>
    </button>
  );
}

export default GameTile;
