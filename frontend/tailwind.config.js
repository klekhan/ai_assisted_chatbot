/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#0A0A0F",
        surface: "#131318",
        elevated: "#1C1C24",
        border: "#262631",
        muted: "#8A8A98",
        ink: "#EDEDF2",
        accent: {
          DEFAULT: "#E8A33D",
          soft: "#F2C572",
          dim: "#4A3A1E",
        },
        info: "#5B8DEF",
        danger: "#E8583D",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(232, 163, 61, 0.15), 0 8px 24px rgba(232, 163, 61, 0.08)",
      },
      keyframes: {
        pulse_soft: {
          "0%, 100%": { opacity: 0.4 },
          "50%": { opacity: 1 },
        },
      },
      animation: {
        pulse_soft: "pulse_soft 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
