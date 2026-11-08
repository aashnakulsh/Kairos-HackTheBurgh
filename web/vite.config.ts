import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Same-origin /api in the browser; dev forwards it to the local fixture API (README).
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
