import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  
  // Performance optimizations
  build: {
    // Code splitting and chunk optimization
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks for better caching
          vendor: ['react', 'react-dom'],
          mui: ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
          utils: ['axios', 'framer-motion'],
        },
      },
    },
    // Optimize bundle size
    target: 'esnext',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
      },
    },
    // Source maps for debugging
    sourcemap: true,
    // Asset optimization
    assetsInlineLimit: 4096, // Inline assets smaller than 4kb
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