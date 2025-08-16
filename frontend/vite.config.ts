import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
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
    ]
  },
});