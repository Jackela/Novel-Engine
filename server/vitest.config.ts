import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
    // Pin the ambient environment: the API composition root falls back to
    // NODE_ENV for its profile, and production owner-gates the contract
    // surface (/openapi.json, DR-035). Tests opt into production explicitly
    // by passing `environment` instead of inheriting the invoking shell.
    env: { NODE_ENV: "test" },
    // Integration-heavy suites exercise production bcrypt and real SQLite.
    // Bound worker pressure and give those paths an explicit, finite budget.
    maxWorkers: 2,
    testTimeout: 10_000,
    // Thresholds are filled from a measured baseline and only apply when
    // coverage is collected (`test:coverage`). A plain `vitest run` does
    // not fail for lack of a coverage report.
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: ["src/**/*.ts"],
      // Frozen floor of the 2026-10-07 baseline (92.39 / 83.8 / 96.29 / 93.98).
      // A later drop fails `test:coverage`; raising the floor is a deliberate edit.
      thresholds: {
        statements: 92,
        branches: 83,
        functions: 96,
        lines: 93,
      },
    },
  },
});
