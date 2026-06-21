import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The built app is served by FastAPI at /app (see webapi/app.py), so assets resolve under /app/.
// In dev, /api is proxied to the live uvicorn back end so the same relative API client works in both.
export default defineConfig({
  plugins: [react()],
  base: "/app/",
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false },
});
