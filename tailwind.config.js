/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        tactical: {
          bg: '#070A0F',
          card: '#0B111A',
          surface: '#111A26',
          border: '#1E2C3D',
          borderLight: '#2A3E54',
          cyan: '#00F2FF',
          sky: '#38BDF8',
          amber: '#F59E0B',
          emerald: '#10B981',
          red: '#EF4444',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        tech: ['Rajdhani', 'Orbitron', 'Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
