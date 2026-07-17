/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        casino: {
          bg: '#07000f',
          surface: '#110820',
          card: '#1a0f2e',
          border: '#2d1b4e',
          gold: '#f5c518',
          'gold-light': '#ffd94a',
          'gold-dark': '#c9a000',
          neon: '#b44fff',
          'neon-pink': '#ff2d78',
          violet: '#7c3aed',
          'violet-light': '#a855f7',
          green: '#00e676',
          'green-dark': '#00b84a',
          red: '#ff3d5a',
          blue: '#00c2ff',
          text: '#e2d9f3',
          muted: '#7c6fa0',
        },
      },
      fontFamily: {
        display: ['Rajdhani', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      backgroundImage: {
        'casino-gradient': 'linear-gradient(135deg, #07000f 0%, #110820 50%, #1a0033 100%)',
        'gold-gradient': 'linear-gradient(135deg, #f5c518 0%, #ffd94a 50%, #c9a000 100%)',
        'neon-gradient': 'linear-gradient(135deg, #b44fff 0%, #7c3aed 100%)',
        'card-gradient': 'linear-gradient(135deg, #1a0f2e 0%, #0e0620 100%)',
        'green-gradient': 'linear-gradient(135deg, #00e676 0%, #00b84a 100%)',
        'pink-gradient': 'linear-gradient(135deg, #ff2d78 0%, #b44fff 100%)',
      },
      boxShadow: {
        'gold': '0 0 20px rgba(245, 197, 24, 0.4)',
        'gold-lg': '0 0 40px rgba(245, 197, 24, 0.6)',
        'neon': '0 0 20px rgba(180, 79, 255, 0.5)',
        'neon-lg': '0 0 40px rgba(180, 79, 255, 0.7)',
        'green': '0 0 20px rgba(0, 230, 118, 0.4)',
        'pink': '0 0 20px rgba(255, 45, 120, 0.4)',
        'card': '0 8px 32px rgba(0, 0, 0, 0.5)',
        'card-hover': '0 12px 48px rgba(0, 0, 0, 0.7)',
      },
      animation: {
        'pulse-gold': 'pulse-gold 2s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        'pulse-gold': {
          '0%, 100%': { boxShadow: '0 0 10px rgba(245, 197, 24, 0.3)' },
          '50%': { boxShadow: '0 0 30px rgba(245, 197, 24, 0.8)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        glow: {
          '0%, 100%': { opacity: '0.8' },
          '50%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
