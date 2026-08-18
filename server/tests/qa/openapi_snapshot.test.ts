import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";

const BASELINE_PATH = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../qa-baselines/openapi.current.json",
);

/**
 * Node twin of scripts/qa/check_openapi_snapshot.py rendering: the generated
 * document is serialized with recursively sorted keys so the committed
 * baseline is byte-stable across regenerations. Until TS-first-green (#252)
 * the baseline regenerates deliberately via `pnpm openapi:snapshot`; the
 * check below fails any route/schema change that did not refresh it.
 */
function renderStable(document: unknown): string {
  return `${JSON.stringify(sortKeys(document), null, 2)}\n`;
}

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(sortKeys);
  }
  if (value !== null && typeof value === "object") {
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      const entry = (value as Record<string, unknown>)[key];
      sorted[key] = sortKeys(entry);
    }
    return sorted;
  }
  return value;
}

async function renderCurrentDocument(): Promise<string> {
  const app = await buildApp({ logger: false });

  try {
    const response = await app.inject({ method: "GET", url: "/openapi.json" });
    if (response.statusCode !== 200) {
      throw new Error(`GET /openapi.json failed with ${response.statusCode}: ${response.body}`);
    }
    return renderStable(response.json());
  } finally {
    await app.close();
  }
}

describe("OpenAPI snapshot gate", () => {
  it("keeps the committed baseline in sync with the generated document", async () => {
    const current = await renderCurrentDocument();

    if (process.env.OPENAPI_SNAPSHOT_WRITE === "1") {
      mkdirSync(dirname(BASELINE_PATH), { recursive: true });
      writeFileSync(BASELINE_PATH, current, "utf8");
      console.info(`[openapi-snapshot] wrote snapshot: ${BASELINE_PATH}`);
      return;
    }

    if (!existsSync(BASELINE_PATH)) {
      throw new Error(
        `[openapi-snapshot] missing baseline: ${BASELINE_PATH}\n` +
          "[openapi-snapshot] run `pnpm --dir server openapi:snapshot` to generate it.",
      );
    }

    const baseline = readFileSync(BASELINE_PATH, "utf8");
    if (baseline !== current) {
      throw new Error(
        "[openapi-snapshot] drift detected: the generated OpenAPI document no longer matches " +
          `${BASELINE_PATH}\n` +
          "[openapi-snapshot] run `pnpm --dir server openapi:snapshot` to refresh the baseline.",
      );
    }
    expect(baseline).toBe(current);
  });
});
