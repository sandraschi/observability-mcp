import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backend = "http://127.0.0.1:12007";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    allowedHosts: ["goliath"],
    port: 12008,
    strictPort: true,
    host: "127.0.0.1",
    proxy: {
      "/api": { target: backend, changeOrigin: true },
      "/health": { target: backend, changeOrigin: true },
      "/mcp": { target: backend, changeOrigin: true },
      "/docs": { target: backend, changeOrigin: true },
      "/openapi.json": { target: backend, changeOrigin: true },
    },
  },
  preview: {
    port: 12008,
    host: "127.0.0.1",
    strictPort: true,
    proxy: {
      "/api": { target: backend, changeOrigin: true },
      "/health": { target: backend, changeOrigin: true },
      "/mcp": { target: backend, changeOrigin: true },
      "/docs": { target: backend, changeOrigin: true },
      "/openapi.json": { target: backend, changeOrigin: true },
    },
  },
});
