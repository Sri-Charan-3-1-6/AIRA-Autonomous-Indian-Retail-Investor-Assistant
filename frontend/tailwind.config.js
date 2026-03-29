/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bgPrimary: "#020818",
        bgSecondary: "#0a1628",
        bgCard: "rgba(255,255,255,0.03)",
        neonBlue: "#00d4ff",
        neonGreen: "#00ff88",
        neonRed: "#ff4444",
        neonGold: "#ffd700",
        neonYellow: "#ffde59",
      },
      boxShadow: {
        "glow-blue": "0 0 24px rgba(0, 212, 255, 0.35)",
        "glow-green": "0 0 24px rgba(0, 255, 136, 0.35)",
        "glow-gold": "0 0 24px rgba(255, 215, 0, 0.35)",
      },
      animation: {
        "pulse-glow": "pulseGlow 2.4s ease-in-out infinite",
        float: "float 5s ease-in-out infinite",
        shimmer: "shimmer 2.4s linear infinite",
        counter: "counter 0.9s ease-out both",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-240% 0" },
          "100%": { backgroundPosition: "240% 0" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0px rgba(0,212,255,0.0)" },
          "50%": { boxShadow: "0 0 24px rgba(0,212,255,0.55)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" },
        },
        counter: {
          "0%": { opacity: "0", transform: "translateY(10px) scale(0.98)" },
          "100%": { opacity: "1", transform: "translateY(0px) scale(1)" },
        },
      },
    },
  },
  plugins: [],
}

