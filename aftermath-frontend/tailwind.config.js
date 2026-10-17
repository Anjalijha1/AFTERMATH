/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#F8FAFC',
        'ink-dark': '#0B0F17',
        panel: '#FFFFFF',
        'panel-dark': '#0F141E',
        line: '#E2E8F0',
        'line-dark': '#1E293B',
        accent: '#0B0F17',
        ok: '#059669',
        bad: '#E11D48',
        warn: '#D97706',
        neutral: '#64748B',
        cyber: {
          black: '#0A0D14',
          dark: '#0F141F',
          mint: '#A7F3D0',
          'mint-light': '#D1FAE5',
          'mint-pastel': '#BFF7E2',
          ice: '#BAE6FD',
          cyan: '#06B6D4',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'subtle': '0 4px 20px -2px rgba(15, 23, 42, 0.05)',
        'card': '0 10px 30px -4px rgba(15, 23, 42, 0.04), 0 4px 6px -2px rgba(15, 23, 42, 0.02)',
        'card-hover': '0 20px 40px -4px rgba(15, 23, 42, 0.08), 0 8px 16px -4px rgba(15, 23, 42, 0.04)',
        'glow-mint': '0 0 35px -5px rgba(167, 243, 208, 0.4)',
        'glow-cyan': '0 0 35px -5px rgba(186, 230, 253, 0.4)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      }
    },
  },
  plugins: [],
};
