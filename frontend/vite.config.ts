/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

const devPort = Number(process.env.VITE_DEV_PORT || process.env.PORT || 3000);
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],

  // Build configuration
  build: {
    rollupOptions: {
      output: {
        // Function-based manualChunks for better module resolution handling
        manualChunks(id) {
          // Vendor chunks for better caching
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) {
            return 'vendor';
          }
          if (id.includes('node_modules/@tanstack/react-router/')) {
            return 'router';
          }
          if (id.includes('node_modules/@tanstack/react-query/')) {
            return 'query';
          }
          if (id.includes('node_modules/@xyflow/')) {
            return 'xyflow';
          }
          // Code-split heavy dependencies to reduce initial bundle size
          if (id.includes('node_modules/@tiptap/')) {
            return 'tiptap';
          }
          if (id.includes('node_modules/@dnd-kit/')) {
            return 'dnd';
          }
          if (id.includes('node_modules/recharts/')) {
            return 'recharts';
          }
          // Split chat dependencies (highlight.js, markdown-it, react-window)
          if (id.includes('node_modules/highlight.js/') || id.includes('node_modules/markdown-it/')) {
            return 'vendor-markdown';
          }
          if (id.includes('node_modules/react-window/')) {
            return 'vendor-react-window';
          }
          return undefined;
        },
      },
    },
    outDir: 'dist',
    emptyOutDir: true,
  },

  // Development server optimizations
  server: {
    port: devPort,
    host: '0.0.0.0', // Enable network access for WSL2/Docker
    strictPort: true, // Fail if port is already in use
    cors: true,
    // HMR optimization for WSL2 - use WebSocket protocol
    hmr: {
      protocol: 'ws',
      host: 'localhost',
      port: devPort,
      clientPort: devPort, // Prevent port mapping confusion
    },
    // WSL2 file watching fix - use polling with faster interval
    watch: {
      usePolling: true,
      interval: 100, // Faster polling for better responsiveness
    },
    proxy: {
      // Proxy /api/* to backend without versioning
      // Use 127.0.0.1 explicitly for WSL2 compatibility (avoid IPv6 resolution issues)
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,

        // SSE-specific configuration for event streaming
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // Preserve SSE headers for event stream endpoint
            if (req.url?.includes('/events/stream')) {
              proxyReq.setHeader('Accept', 'text/event-stream');
              proxyReq.setHeader('Cache-Control', 'no-cache');
              proxyReq.setHeader('Connection', 'keep-alive');
            }
          });
        },
      },
      // Proxy /meta/* to backend
      '/meta': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      // Proxy /health to backend
      '/health': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },

  // Dependency optimization
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      '@tanstack/react-query',
      '@tanstack/react-router',
    ],
  },

  // Path resolution
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@/app': resolve(__dirname, 'src/app'),
      '@/features': resolve(__dirname, 'src/features'),
      '@/shared': resolve(__dirname, 'src/shared'),
      '@/styles': resolve(__dirname, 'src/styles'),
    },
  },

  // CSS configuration
  css: {
    devSourcemap: true,
  },

  // Preview configuration with SPA fallback
  preview: {
    port: 4173,
    host: true,
    proxy: {
      // Proxy /api/* to backend in preview mode
      // Use 127.0.0.1 explicitly for WSL2 compatibility
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      '/meta': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      '/health': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  // App type for SPA history fallback support
  appType: 'spa',

  // Vitest Configuration
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    isolate: true,
    css: false, // Disable CSS processing for faster tests
    include: [
      'src/__tests__/**/*.test.{ts,tsx}',
      'src/pages/__tests__/**/*.test.{ts,tsx}',
      'src/shared/**/__tests__/**/*.test.{ts,tsx}',
      'src/features/**/__tests__/**/*.test.{ts,tsx}',
    ],
    exclude: [
      'node_modules',
      'dist',
      'src/test/**',
      'tests/**',
      '**/*.spec.ts',
      '**/*.spec.tsx',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
      exclude: [
        'node_modules/',
        'src/test/setup.ts',
        'dist/',
      ],
    },
    fileParallelism: false, // Disable parallelism to prevent hangs on limited resources
    pool: 'forks', // Use forks instead of threads for better isolation
    singleFork: true, // Run tests sequentially in a single fork
    testTimeout: 10000,
    hookTimeout: 10000,
    reporters: ['verbose'],
  },

});
