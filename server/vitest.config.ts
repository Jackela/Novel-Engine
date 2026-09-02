import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
    // Integration-heavy suites exercise production bcrypt and real SQLite.
    // Bound worker pressure and give those paths an explicit, finite budget.
    maxWorkers: 2,
    testTimeout: 10_000,
  },
});
