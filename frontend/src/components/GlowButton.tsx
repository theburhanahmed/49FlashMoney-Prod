import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface GlowButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'gold' | 'neon' | 'green' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
  fullWidth?: boolean;
}

const VARIANTS = {
  gold: 'btn-gold',
  neon: 'btn-neon',
  green: 'btn-green',
  ghost: 'btn-ghost',
  danger: 'bg-gradient-to-r from-casino-red to-casino-neon-pink text-white font-display font-bold tracking-wider uppercase rounded-xl transition-all duration-200 hover:shadow-pink hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed',
};

const SIZES = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-3 text-base',
  lg: 'px-8 py-4 text-lg',
};

function GlowButton({
  variant = 'gold',
  size = 'md',
  children,
  fullWidth = false,
  className = '',
  ...props
}: GlowButtonProps) {
  return (
    <button
      className={`
        ${VARIANTS[variant]}
        ${SIZES[size]}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `}
      {...props}
    >
      {children}
    </button>
  );
}

export default GlowButton;
