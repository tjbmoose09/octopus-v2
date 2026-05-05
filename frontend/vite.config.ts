// This TS config is intentionally a mirror of `vite.config.js` — the live
// source of truth. It exists only because an earlier scaffold step created
// it; Vite prefers `.ts` over `.js` when both are present, so keeping them
// aligned prevents config drift. Edit `vite.config.js`; this file will be
// kept in sync.

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        timeout: 300000,
        proxyTimeout: 300000,
      },
      "/ws": { target: "ws://localhost:8080", ws: true },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    target: "es2022",
  },
});
