import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { exportArtifactNames } from "../../src/contexts/studio/application/export_artifact_identity.js";
import {
  type ExportArtifactFormat,
  type ExportPageCursor,
  type ExportSource,
  exportPageLimit,
  type PreparedExportArtifact,
} from "../../src/contexts/studio/application/ports/export_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ProjectService } from "../../src/contexts/studio/application/project_service.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { buildProjectArtifactPageQuery } from "../../src/contexts/studio/infrastructure/export_page_queries.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import {
  openStudioDatabase,
  type StudioDatabase,
} from "../../src/shared/infrastructure/db/startup.js";

function monotonicClock(): () => Date {
  let milliseconds = Date.parse("2026-09-05T00:00:00.000Z");
  return () => new Date(++milliseconds);
}

async function openHarness(queryLogger?: { logQuery: (sql: string, params: unknown[]) => void }) {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-page-"));
  const studio: StudioDatabase = await openStudioDatabase(join(directory, "novel-engine.sqlite3"), {
    queryLogger,
  });
  const clock = monotonicClock();
  const store = new DrizzleStudioStore({ database: studio.db });
  const projects = new ProjectService(store, clock);
  const auth = new AuthService({
    store: new DrizzleAuthStore(studio.db),
    sessionSecret: "export-page-test-secret",
    now: clock,
  });
  await auth.configureOwner("export-page-owner", "long-test-password");
  const principal = (await auth.createOwnerSession("export-page-owner", "long-test-password"))
    .principal;
  return {
    cleanup: async () => {
      try {
        studio.close();
      } finally {
        await rm(directory, { recursive: true, force: true });
      }
    },
    clock,
    exportStore: new ExportStorePart(studio.db),
    principal,
    projects,
    scope: scopeForPrincipal(principal),
    studio,
    store,
  };
}

type Harness = Awaited<ReturnType<typeof openHarness>>;

function seedDocuments(harness: Harness, projectId: string, count: number): void {
  const volumeId = harness.store.findVolumes(harness.scope, projectId)[0]?.id ?? null;
  for (let index = 2; index <= count; index += 1) {
    harness.store.addDocument(harness.scope, projectId, {
      kind: "chapter",
      title: `Chapter ${index}`,
      contentMarkdown: `Chapter ${index} body`,
      metadataJson: "{}",
      position: index,
      volumeId,
      now: harness.clock(),
    });
  }
}

function newProject(harness: Harness, title: string): string {
  return (harness.projects.newProject(harness.principal, { title }) as unknown as { id: string })
    .id;
}

function publishArtifacts(
  harness: Harness,
  projectId: string,
  count: number,
  prefix: string,
): void {
  let source: ExportSource = harness.exportStore.readExportSource(
    harness.scope,
    projectId,
    harness.clock(),
  );
  for (let index = 1; index <= count; index += 1) {
    const id = `${prefix}-${String(index).padStart(3, "0")}`;
    const format: ExportArtifactFormat =
      index % 3 === 0 ? "epub" : index % 3 === 1 ? "markdown" : "docx";
    const input: PreparedExportArtifact = {
      source,
      id,
      format,
      relativePath: exportArtifactNames(projectId, id, format).relativePath,
      sizeBytes: index,
      checksumSha256: "a".repeat(64),
      createdAt: harness.clock(),
    };
    harness.exportStore.recordCompletedExportJob(harness.scope, input);
    // Re-read so each artifact lands on its own fresh snapshot position clock.
    source = harness.exportStore.readExportSource(harness.scope, projectId, harness.clock());
  }
}

describe("export catalog keyset pages", () => {
  it("returns at most the newest 50 catalog summaries by default", async () => {
    const harness = await openHarness();
    try {
      const projectId = newProject(harness, "Default page");
      seedDocuments(harness, projectId, 3);
      publishArtifacts(harness, projectId, 120, "artifact");

      const page = harness.exportStore.listProjectArtifacts(harness.scope, projectId, {
        limit: exportPageLimit(50),
      });
      expect(page.artifacts).toHaveLength(50);
      expect(page.artifacts[0]?.id).toBe("artifact-120");
      expect(page.artifacts[49]?.id).toBe("artifact-071");
      expect(page.nextCursor).toEqual({
        createdAtMs: page.artifacts[49]?.createdAt.getTime(),
        id: "artifact-071",
      });
    } finally {
      await harness.cleanup();
    }
  });

  it("traverses every page newest first without gaps, duplicates, or a terminal cursor", async () => {
    const harness = await openHarness();
    try {
      const projectId = newProject(harness, "Full traversal");
      seedDocuments(harness, projectId, 3);
      publishArtifacts(harness, projectId, 205, "artifact");

      const seen: string[] = [];
      let cursor: ExportPageCursor | undefined;
      for (;;) {
        const page = harness.exportStore.listProjectArtifacts(harness.scope, projectId, {
          limit: exportPageLimit(100),
          ...(cursor === undefined ? {} : { cursor }),
        });
        seen.push(...page.artifacts.map((artifact) => artifact.id));
        if (page.nextCursor === null) break;
        cursor = page.nextCursor;
      }
      expect(seen).toHaveLength(205);
      expect(new Set(seen).size).toBe(205);
      expect(seen[0]).toBe("artifact-205");
      expect(seen.at(-1)).toBe("artifact-001");
    } finally {
      await harness.cleanup();
    }
  });

  it("keeps page traversal scoped to the requesting project", async () => {
    const harness = await openHarness();
    try {
      const first = newProject(harness, "Scoped first");
      const second = newProject(harness, "Scoped second");
      seedDocuments(harness, first, 2);
      seedDocuments(harness, second, 2);
      publishArtifacts(harness, first, 3, "first");
      publishArtifacts(harness, second, 1, "second");

      const page = harness.exportStore.listProjectArtifacts(harness.scope, first, {
        limit: exportPageLimit(10),
      });
      expect(page.artifacts.map((artifact) => artifact.id)).toEqual([
        "first-003",
        "first-002",
        "first-001",
      ]);
      expect(() =>
        harness.exportStore.findProjectArtifact(harness.scope, first, "second-001"),
      ).toThrow(NotFoundError);
    } finally {
      await harness.cleanup();
    }
  });

  it("uses the project keyset index without a temporary sort and reads limit + 1 rows", async () => {
    const harness = await openHarness();
    try {
      const projectId = newProject(harness, "Query plan");
      seedDocuments(harness, projectId, 2);
      publishArtifacts(harness, projectId, 3, "artifact");
      const page = harness.exportStore.listProjectArtifacts(harness.scope, projectId, {
        limit: exportPageLimit(2),
      });
      expect(page.artifacts).toHaveLength(2);
      expect(page.nextCursor).not.toBeNull();

      const query = harness.studio.db.transaction((tx) =>
        buildProjectArtifactPageQuery(tx, projectId, {
          limit: exportPageLimit(2),
          cursor: page.nextCursor ?? undefined,
        }).toSQL(),
      );
      const plan = harness.studio.raw
        .prepare(`EXPLAIN QUERY PLAN ${query.sql}`)
        .all(...query.params) as Array<{ detail: string }>;
      const details = plan.map((row) => row.detail).join("\n");
      expect(details).toContain("idx_exports_project_created_id");
      expect(details).not.toContain("USE TEMP B-TREE");
    } finally {
      await harness.cleanup();
    }
  });

  it("rejects out-of-range page limits at the port boundary", () => {
    for (const invalid of [0, -1, 101, 50.5, Number.NaN]) {
      expect(() => exportPageLimit(invalid)).toThrow(RangeError);
    }
    expect(exportPageLimit(1)).toBe(1);
    expect(exportPageLimit(100)).toBe(100);
  });

  it("writes a fresh snapshot with document-insert statements batched, not per document", async () => {
    const statements: { sql: string }[] = [];
    const harness = await openHarness({
      logQuery: (sql) => statements.push({ sql }),
    });
    try {
      const small = newProject(harness, "Small snapshot");
      seedDocuments(harness, small, 5);
      const large = newProject(harness, "Large snapshot");
      seedDocuments(harness, large, 60);

      const countSnapshotInserts = (): number =>
        statements.filter(
          (statement) =>
            statement.sql.trimStart().toLowerCase().startsWith("insert") &&
            statement.sql.includes("snapshot_documents"),
        ).length;

      statements.length = 0;
      const smallSource = harness.exportStore.readExportSource(
        harness.scope,
        small,
        harness.clock(),
      );
      harness.exportStore.recordCompletedExportJob(harness.scope, {
        source: smallSource,
        id: "small-artifact",
        format: "markdown",
        relativePath: exportArtifactNames(small, "small-artifact", "markdown").relativePath,
        sizeBytes: 1,
        checksumSha256: "a".repeat(64),
        createdAt: harness.clock(),
      });
      const smallInserts = countSnapshotInserts();

      statements.length = 0;
      const largeSource = harness.exportStore.readExportSource(
        harness.scope,
        large,
        harness.clock(),
      );
      harness.exportStore.recordCompletedExportJob(harness.scope, {
        source: largeSource,
        id: "large-artifact",
        format: "markdown",
        relativePath: exportArtifactNames(large, "large-artifact", "markdown").relativePath,
        sizeBytes: 1,
        checksumSha256: "a".repeat(64),
        createdAt: harness.clock(),
      });
      const largeInserts = countSnapshotInserts();

      expect(smallInserts).toBe(1);
      expect(largeInserts).toBe(1);
    } finally {
      await harness.cleanup();
    }
  });
});
