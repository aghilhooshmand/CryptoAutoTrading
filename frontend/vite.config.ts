import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/market": "http://127.0.0.1:8000",
      "/simulation": "http://127.0.0.1:8000",
      "/backtest": "http://127.0.0.1:8000",
      "/strategies": "http://127.0.0.1:8000",
      "/comparisons": "http://127.0.0.1:8000",
    },
  },
});
