import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

const apiProxyTimeoutMs = 5 * 60 * 1000;

export default defineConfig({
  plugins: [react()],
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
