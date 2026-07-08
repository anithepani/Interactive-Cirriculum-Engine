import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--bg-canvas)",
        ink: "var(--ink)",
        "ink-soft": "var(--ink-soft)",
        lime: "var(--accent-lime)",
        coral: "var(--accent-coral)",
        hotpink: "var(--accent-hotpink)",
        blue: "var(--accent-blue)",
        orange: "var(--accent-orange)",
        purple: "var(--accent-purple)",
        surfaceDark: "var(--surface-dark)",
        surfaceBurgundy: "var(--surface-burgundy)",
      },
      borderRadius: {
        xl2: "var(--radius-xl)",
        lg2: "var(--radius-lg)",
        md2: "var(--radius-md)",
      },
      fontFamily: {
        display: ["var(--font-display)", "Space Grotesk", "sans-serif"],
        body: ["var(--font-body)", "Inter", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
      },
      maxWidth: {
        container: "1200px",
      },
      keyframes: {
        marquee: {
          "0%": { transform: "translateX(0%)" },
          "100%": { transform: "translateX(-50%)" },
        },
        marqueeReverse: {
          "0%": { transform: "translateX(-50%)" },
          "100%": { transform: "translateX(0%)" },
        },
        floatY: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
      animation: {
        marquee: "marquee 30s linear infinite",
        marqueeReverse: "marqueeReverse 40s linear infinite",
        floatY: "floatY 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
