/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [
    react(),
    // nodePolyfills removed for debugging
  ],

  // Manual process polyfill via define
  // MIGRATION NOTE: Transitioning from REACT_APP_* to VITE_* (VITE_* takes precedence)
  /* define: {
    global: 'globalThis',
    'process': JSON.stringify({
      env: {
        NODE_ENV: process.env.NODE_ENV || 'development',
        // Backward compatibility: Keep REACT_APP_* for existing code
        REACT_APP_API_BASE_URL: process.env.VITE_API_BASE_URL || process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1',
        REACT_APP_API_TIMEOUT: process.env.VITE_API_TIMEOUT || process.env.REACT_APP_API_TIMEOUT || '10000',
        REACT_APP_API_URL: process.env.VITE_API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000',
        REACT_APP_DOCKER: process.env.VITE_DOCKER || process.env.REACT_APP_DOCKER || 'false',
      },
      platform: 'browser',
      version: '18.0.0',
      versions: { node: '18.0.0' },
      nextTick: (callback, ...args) => setTimeout(() => callback(...args), 0),
      cwd: () => '/',
      argv: [],
      stdout: { write: () => {} },
      stderr: { write: () => {} },
    }),
    'process.env': JSON.stringify({
      NODE_ENV: process.env.NODE_ENV || 'development',
      // Backward compatibility: Keep REACT_APP_* for existing code
      REACT_APP_API_BASE_URL: process.env.VITE_API_BASE_URL || process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1',
      REACT_APP_API_TIMEOUT: process.env.VITE_API_TIMEOUT || process.env.REACT_APP_API_TIMEOUT || '10000',
      REACT_APP_API_URL: process.env.VITE_API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000',
      REACT_APP_DOCKER: process.env.VITE_DOCKER || process.env.REACT_APP_DOCKER || 'false',
    }),
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
    'process.env.REACT_APP_API_BASE_URL': JSON.stringify(process.env.VITE_API_BASE_URL || process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1'),
    'process.env.REACT_APP_API_TIMEOUT': JSON.stringify(process.env.VITE_API_TIMEOUT || process.env.REACT_APP_API_TIMEOUT || '10000'),
    'process.env.REACT_APP_API_URL': JSON.stringify(process.env.VITE_API_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000'),
    'process.env.REACT_APP_DOCKER': JSON.stringify(process.env.VITE_DOCKER || process.env.REACT_APP_DOCKER || 'false'),
  }, */

  // Performance optimizations
  build: {
    // Code splitting and chunk optimization
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks for better caching
          vendor: ['react', 'react-dom'],
          mui: ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
          // Heavy libraries split for mobile optimization
          three: ['three', '@react-three/fiber', '@react-three/drei'],
          d3: ['d3'],
          animation: ['framer-motion'],
          utils: ['axios', 'socket.io-client', 'lodash-es'],
          query: ['react-query', '@reduxjs/toolkit', 'react-redux'],
        },
      },
    },
    outDir: 'dist',
    emptyOutDir: true,
    // terserOptions: {
    //   compress: {
    //     drop_console: true, // Remove console.log in production
    //     drop_debugger: true,
    //     dead_code: true,
    //     unused: true,
    //   },
    //   mangle: {
    //     safari10: true, // Fix Safari 10+ issues
    //   },
    // },
  },

  // Development server optimizations
  server: {
    port: 3000,
    host: '0.0.0.0', // Enable network access for WSL2/Docker
    strictPort: true, // Fail if port is already in use
    cors: true,
    // HMR optimization for WSL2 - use WebSocket protocol
    hmr: {
      protocol: 'ws',
      host: 'localhost',
      port: 3000,
      clientPort: 3000, // Prevent port mapping confusion
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
        target: process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
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
        target: process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // Proxy /health to backend
      '/health': {
        target: process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },

  // Dependency optimization
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      '@mui/material',
      '@mui/icons-material',
      'axios',
      'framer-motion'
    ],
  },

  // Path resolution
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@hooks': resolve(__dirname, 'src/hooks'),
      '@services': resolve(__dirname, 'src/services'),
      '@types': resolve(__dirname, 'src/types'),
      '@/styles': resolve(__dirname, 'src/styles'),
      '@mui/icons-material$': resolve(__dirname, 'src/mui-icons.ts'),
    },
  },

  // CSS optimization
  css: {
    devSourcemap: true,
    preprocessorOptions: {
      scss: {
        additionalData: `@import "@/styles/variables.scss";`,
      },
    },
  },

  // Preview configuration with SPA fallback
  preview: {
    port: 4173,
    host: true,
    proxy: {
      // Proxy /api/* to backend in preview mode
      // Use 127.0.0.1 explicitly for WSL2 compatibility
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/meta': {
        target: process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: process.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
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
        css: false, // Disable CSS processing for faster tests
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
            '**/*.test.tsx',
            '**/*.test.ts',
            '**/*.spec.ts',
            'dist/',
          ],
        },
        fileParallelism: false, // Disable parallelism to prevent hangs on limited resources
  
    pool: 'forks', // Use forks instead of threads for better isolation
    poolOptions: {
      forks: {
        singleFork: true, // Run tests sequentially in a single fork
      },
    },
    testTimeout: 10000,
    hookTimeout: 10000,
    reporters: ['verbose'],
    // Exclude e2e tests and integration tests from unit test runs
    exclude: ['node_modules', 'dist', '**/*.spec.ts', '**/*.spec.tsx', '**/tests/integration/**', 'tests/integration'],
  },

});
