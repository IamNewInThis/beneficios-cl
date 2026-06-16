import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#191c1f",
        mute: "#505a63",
        stone: "#8d969e",
        faint: "#c9c9cd",
        "surface-soft": "#f4f4f4",
        "surface-elevated": "#16181a",
        "on-dark-mute": "rgba(255,255,255,0.72)",
        "hairline-light": "#e2e2e7",
        "hairline-dark": "rgba(255,255,255,0.12)",
        cobalt: "#494fdf",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-inter)", "system-ui", "sans-serif"],
        body: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "20px",
      },
    },
  },
  plugins: [],
};

export default config;
