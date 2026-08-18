import { defineConfig } from "drizzle-kit";

/**
 * Schema evolution is generate-only: `pnpm --dir server db:generate` writes
 * migration files under ./drizzle from src/shared/infrastructure/db/schema.ts.
 * Direct schema pushes to a database are banned by the migration-channel gate
 * (scripts/qa/check_migration_channel.mjs); migrations are the single
 * deployment source of truth and run programmatically at startup.
 */
export default defineConfig({
  dialect: "sqlite",
  schema: "./src/shared/infrastructure/db/schema.ts",
  out: "./drizzle",
});
