import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { nodePolyfills } from 'vite-plugin-node-polyfills';

export default defineConfig({
  plugins: [
    react(),
    nodePolyfills({
      // Disable process polyfilling by the plugin so we can handle it manually
      globals: {
        Buffer: true,
        global: true,
        process: false, // Let us handle process manually
      },
      protocolImports: true,
    })
  ],
  
  // Manual process polyfill via define
  define: {
    global: 'globalThis',
    'process': JSON.stringify({
      env: {
        NODE_ENV: process.env.NODE_ENV || 'development',
        REACT_APP_API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1',
        REACT_APP_API_TIMEOUT: process.env.REACT_APP_API_TIMEOUT || '10000',
        REACT_APP_API_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
        REACT_APP_DOCKER: process.env.REACT_APP_DOCKER || 'false',
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
      REACT_APP_API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1',
      REACT_APP_API_TIMEOUT: process.env.REACT_APP_API_TIMEOUT || '10000',
      REACT_APP_API_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
      REACT_APP_DOCKER: process.env.REACT_APP_DOCKER || 'false',
    }),
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
    'process.env.REACT_APP_API_BASE_URL': JSON.stringify(process.env.REACT_APP_API_BASE_URL || 'http://localhost:3000/v1'),
    'process.env.REACT_APP_API_TIMEOUT': JSON.stringify(process.env.REACT_APP_API_TIMEOUT || '10000'),
    'process.env.REACT_APP_API_URL': JSON.stringify(process.env.REACT_APP_API_URL || 'http://localhost:8000'),
    'process.env.REACT_APP_DOCKER': JSON.stringify(process.env.REACT_APP_DOCKER || 'false'),
  },
  
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
    // Optimize bundle size for mobile performance
    target: 'esnext',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
        dead_code: true,
        unused: true,
      },
      mangle: {
        safari10: true, // Fix Safari 10+ issues
      },
    },
    // Source maps for debugging
    sourcemap: true,
    // Asset optimization for mobile
    assetsInlineLimit: 2048, // Smaller inline limit for mobile performance
    // Chunk size warnings optimized for mobile
    chunkSizeWarningLimit: 800, // Warn for chunks > 800kb (mobile-friendly)
  },
  
  // Development server optimizations
  server: {
    port: 3000,
    host: true, // Enable network access
    cors: true,
    // HMR optimization
    hmr: {
      port: 3001,
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
  
  // Preview configuration
  preview: {
    port: 3000,
    host: true,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    testTimeout: 10000, // 10 second timeout for tests
    hookTimeout: 5000,  // 5 second timeout for hooks
    teardownTimeout: 5000, // 5 second timeout for teardown
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/*.e2e.spec.js',
      '**/*.spec.js',
      '**/e2e/**',
      '**/playwright/**',
      '**/tests/CharacterCreation.e2e.spec.js',
      '**/tests/CharacterSelection.spec.js', 
      '**/tests/FullIntegration.spec.js'
    ],
    include: [
      '**/*.test.tsx',
      '**/*.test.ts'
    ],
    reporters: ['verbose'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/**',
        'dist/**',
        '**/*.config.js',
        '**/test-setup.js',
        '**/setup.ts',
        '**/*.e2e.spec.js'
      ]
    },
    // Isolate tests to prevent WebSocket connection leaks
    isolate: true,
    // Pool options to prevent hanging
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: true,
        isolate: true
      }
    }
  },
});