import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/(marketing)/**/*.{js,ts,jsx,tsx}",
    "./components/landing/**/*.{js,ts,jsx,tsx}",
    "./components/ui/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
