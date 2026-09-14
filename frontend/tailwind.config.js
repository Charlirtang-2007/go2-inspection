/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        ink: {
          900: '#070b14',
          800: '#0d1220',
          700: '#141a2c',
          600: '#1c2438',
          500: '#273049'
        },
        neon: {
          cyan:   '#22d3ee',
          blue:   '#60a5fa',
          purple: '#a78bfa',
          green:  '#4ade80',
          amber:  '#fbbf24',
          red:    '#f87171'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace']
      },
      boxShadow: {
        'glow-cyan':  '0 0 24px rgba(34, 211, 238, 0.45)',
        'glow-blue':  '0 0 24px rgba(96, 165, 250, 0.45)',
        'glow-green': '0 0 24px rgba(74, 222, 128, 0.45)',
        'glow-red':   '0 0 24px rgba(248, 113, 113, 0.55)',
        'glow-soft':  '0 8px 32px rgba(0, 0, 0, 0.35)'
      },
      keyframes: {
        'tab-in': {
          '0%':   { opacity: '0', transform: 'translateY(10px) scale(0.985)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' }
        },
        'pulse-ring': {
          '0%':   { transform: 'scale(0.9)', opacity: '0.7' },
          '70%':  { transform: 'scale(1.6)', opacity: '0' },
          '100%': { transform: 'scale(1.6)', opacity: '0' }
        },
        'scan': {
          '0%':   { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(200%)' }
        },
        'glow-pulse': {
          '0%, 100%': { opacity: '0.55' },
          '50%':      { opacity: '1' }
        },
        'log-in': {
          '0%':   { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' }
        },
        'stripe': {
          '0%':   { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '32px 0' }
        },
        'float-slow': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-6px)' }
        }
      },
      animation: {
        'tab-in':      'tab-in 0.45s cubic-bezier(0.22, 1, 0.36, 1)',
        'pulse-ring':  'pulse-ring 1.8s ease-out infinite',
        'scan':        'scan 2.4s linear infinite',
        'glow-pulse':  'glow-pulse 2.2s ease-in-out infinite',
        'log-in':      'log-in 0.35s ease-out',
        'stripe':      'stripe 0.9s linear infinite',
        'float-slow':  'float-slow 4s ease-in-out infinite'
      }
    }
  },
  plugins: []
};