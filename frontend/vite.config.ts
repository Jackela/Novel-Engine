import fs from "node:fs";
import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiProxyTimeoutMs = 5 * 60 * 1000;
const serverManifest = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, "..", "server", "package.json"), "utf8"),
) as { version: string };
const projectVersion = serverManifest.version ?? "0.0.0";

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(projectVersion),
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: (process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000").replace(/\/+$/, ""),
        changeOrigin: true,
        timeout: apiProxyTimeoutMs,
        proxyTimeout: apiProxyTimeoutMs,
      },
    },
  },
  preview: {
    port: 4173,
  },
});
