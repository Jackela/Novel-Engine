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
  },
});
