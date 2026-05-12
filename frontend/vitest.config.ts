import { defineConfig } from 'vitest/config';
import path from 'node:path';

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
    css: true,
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    exclude: ['tests/e2e/**'],
    coverage: {
      reporter: ['text', 'html'],
      include: [
        'src/app/api.ts',
        'src/app/config.ts',
        'src/components/Button.tsx',
        'src/components/Panel.tsx',
        'src/components/StatusPill.tsx',
        'src/components/ui/badge.tsx',
        'src/components/ui/button.tsx',
        'src/components/ui/card.tsx',
        'src/features/auth/AuthProvider.tsx',
        'src/features/auth/useAuth.ts',
        'src/lib/utils.ts',
        'src/shared/storage.ts',
      ],
      thresholds: {
        statements: 80,
        branches: 65,
        functions: 80,
        lines: 80,
      },
    },
  },
});
