import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    "from-sky-500/20",
    "to-sky-600/5",
    "from-orange-500/20",
    "to-orange-600/5",
    "from-blue-500/20",
    "to-blue-600/5",
    "from-violet-500/20",
    "to-violet-600/5",
    "from-amber-500/20",
    "to-amber-600/5",
    "from-emerald-500/20",
    "to-emerald-600/5",
    "from-teal-500/20",
    "to-teal-600/5",
    "from-cyan-500/20",
    "to-cyan-600/5",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
