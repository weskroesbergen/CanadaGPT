/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Canada Dark Theme - Subtle Neutrals
        bg: {
          primary: '#1E293B',      // Dark slate
          secondary: '#334155',    // Lighter slate
          elevated: '#475569',     // Card backgrounds
          overlay: '#0F172A',      // Modals, overlays
        },
        accent: {
          red: '#DC2626',          // Muted Canadian red
          'red-hover': '#B91C1C',  // Hover state
          'red-light': '#FCA5A5',  // Subtle highlights
        },
        text: {
          primary: '#F1F5F9',      // Off-white (main text)
          secondary: '#CBD5E1',    // Muted gray (descriptions)
          tertiary: '#94A3B8',     // Disabled/metadata
        },
        border: {
          subtle: '#334155',       // Default borders
          emphasis: '#475569',     // Emphasized borders
        },
        // Semantic colors
        success: {
          DEFAULT: '#10B981',
          light: '#A7F3D0',
        },
        warning: {
          DEFAULT: '#F59E0B',
          light: '#FDE68A',
        },
        error: {
          DEFAULT: '#EF4444',
          light: '#FCA5A5',
        },
        info: {
          DEFAULT: '#3B82F6',
          light: '#BFDBFE',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        display: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Courier New', 'monospace'],
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1rem' }],      // 12px
        sm: ['0.875rem', { lineHeight: '1.25rem' }],  // 14px
        base: ['1rem', { lineHeight: '1.5rem' }],     // 16px
        lg: ['1.125rem', { lineHeight: '1.75rem' }],  // 18px
        xl: ['1.25rem', { lineHeight: '1.75rem' }],   // 20px
        '2xl': ['1.5rem', { lineHeight: '2rem' }],    // 24px
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],   // 36px
        '5xl': ['3rem', { lineHeight: '1' }],           // 48px
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '112': '28rem',
        '128': '32rem',
      },
      borderRadius: {
        'sm': '0.25rem',  // 4px
        DEFAULT: '0.5rem', // 8px
        'lg': '0.75rem',  // 12px
        'xl': '1rem',     // 16px
      },
      boxShadow: {
        'sm': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        'lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        'xl': '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
        'none': 'none',
      },
      // Animation
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-in-up': {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-in-up': 'slide-in-up 0.3s ease-out',
      },
    },
  },
  plugins: [],
}
