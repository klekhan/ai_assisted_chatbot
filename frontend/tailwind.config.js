/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#F7F6F1",
        surface: "#FFFFFF",
        elevated: "#F1EFE8",
        border: "#E5E2D9",
        muted: "#7C8087",
        ink: "#1A2438",
        navy: {
          DEFAULT: "#16305C",
          soft: "#2A4A82",
        },
        accent: {
          DEFAULT: "#F2761F",
          soft: "#F79A56",
          dim: "#FCE6D3",
        },
        info: "#2A6FDB",
        danger: "#E2472B",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(26, 36, 56, 0.04), 0 8px 24px rgba(26, 36, 56, 0.05)",
        glow: "0 0 0 1px rgba(242, 118, 31, 0.15), 0 8px 24px rgba(242, 118, 31, 0.10)",
      },
      keyframes: {
        pulse_soft: {
          "0%, 100%": { opacity: 0.35 },
          "50%": { opacity: 1 },
        },
        orb_float: {
          "0%, 100%": { transform: "scale(1) translateY(0px)", opacity: 0.28 },
          "50%": { transform: "scale(1.08) translateY(-16px)", opacity: 0.38 },
        },
      },
      animation: {
        pulse_soft: "pulse_soft 1.4s ease-in-out infinite",
        orb_float: "orb_float 7s ease-in-out infinite",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
