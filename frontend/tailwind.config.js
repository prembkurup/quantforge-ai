/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        shell: "#0f172a",
        panel: "#111827",
        line: "#243244",
        accent: "#14b8a6",
        warn: "#f59e0b"
      }
    }
  },
  plugins: []
};
