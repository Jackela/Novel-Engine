import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import fs from 'node:fs';

const apiProxyTimeoutMs = 5 * 60 * 1000;
const projectToml = fs.readFileSync(path.resolve(__dirname, '..', 'pyproject.toml'), 'utf8');
const projectVersion =
  projectToml.match(/^\s*version\s*=\s*"([^"]+)"/m)?.[1] ?? '0.0.0';

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(projectVersion),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: (process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000').replace(/\/+$/, ''),
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
