import Database from "better-sqlite3";

import type { HealthProbe, HealthReport } from "../../application/ports/health.js";

const DATABASE_UNHEALTHY = "database health check failed";

/** Readiness probe over the exact SQLite handle used by application requests. */
export function sqliteHealthProbe(raw: Database.Database): HealthProbe {
  return async () => {
    if (!raw.open) return unhealthyReport();
    try {
      raw.prepare("SELECT 1").get();
      return {
        components: [{ name: "database", status: "healthy", message: "SQLite ready" }],
      };
    } catch (error) {
      if (error instanceof Database.SqliteError) return unhealthyReport();
      throw error;
    }
  };
}

function unhealthyReport(): HealthReport {
  return {
    components: [{ name: "database", status: "unhealthy", error: DATABASE_UNHEALTHY }],
  };
}
