import path from "node:path";
import { defineConfig } from "vitest/config";

// Pin the suite's mode before Vite evaluates anything. Vite derives `mode` (and
// with it module resolution — a production mode refuses `node:` builtins that
// these tests legitimately import) from NODE_ENV when the config loads, and
// React reads it at module load too. `test.env` cannot fix either half because
// both are decided before it applies, so an ambient NODE_ENV=production would
// otherwise change what the suite compiles and runs.
process.env.NODE_ENV = "test";

export default defineConfig({
  define: {
    __PRODUCT_IDENTITY__: JSON.stringify({ name: "Test Engine", version: "test" }),
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "src"),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./tests/setup.ts",
    css: true,
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: {
      reporter: ["text", "html"],
      include: ["src/**/*.ts", "src/**/*.tsx"],
      exclude: ["src/main.tsx", "src/vite-env.d.ts"],
    },
  },
});
