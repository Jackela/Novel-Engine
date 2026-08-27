import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, describe, expect, it } from "vitest";
import { createStudioServices } from "../../src/contexts/studio/application/studio_services.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { FsLegacyWorkspaceReader } from "../../src/contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { InvalidOperationError } from "../../src/shared/domain/exceptions.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import {
  openStudioDatabase,
  type StudioDatabase,
} from "../../src/shared/infrastructure/db/startup.js";
import { capturingFactory } from "../api/proposal_test_helpers.js";
import { directoryFingerprint, makeLegacyWorkspace } from "../legacy_workspace_fixtures.js";

const opened: StudioDatabase[] = [];

/**
 * The real service graph over a migrated SQLite file — the per-principal
 * scenarios live here because the HTTP surface is owner-only by contract.
 */
async function buildServices() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-import-"));
  const database = await openStudioDatabase(directory);
  opened.push(database);
  const auth = new AuthService({
    store: new DrizzleAuthStore(database.db),
    sessionSecret: "unit-test-session-secret",
  });
  const services = createStudioServices(
    new DrizzleStudioStore({ database: database.db, dataDirectory: directory }),
    {
      providerFactory: capturingFactory({}).factory,
      legacyWorkspaceReader: new FsLegacyWorkspaceReader(),
      artifactStore: new ExportStorePart(database.db),
      artifactFiles: new FilesystemExportArtifactGateway(directory),
    },
  );
  return { auth, services };
}

async function ownerPrincipal(auth: AuthService): Promise<Principal> {
  await auth.configureOwner("archivist", "correct horse battery");
  return (await auth.createOwnerSession("archivist", "correct horse battery")).principal;
}

function legacySource(): string {
  return makeLegacyWorkspace(join(tmpdir(), `legacy-${Date.now()}-${Math.random()}`), {
    title: "Scoped Story",
    premise: "Two principals, one workspace.",
    chapters: [
      { filename: "chapter-002.md", content: "# Second\n" },
      { filename: "chapter-001.md", content: "# First\n" },
    ],
  });
}

afterAll(() => {
  for (const database of opened) {
    database.close();
  }
});

describe("legacy import service", () => {
  it("returns the existing project when the same principal re-imports", async () => {
    const { auth, services } = await buildServices();
    const owner = await ownerPrincipal(auth);
    const source = legacySource();

    const first = services.imports.importLegacyWorkspace(owner, source);
    const second = services.imports.importLegacyWorkspace(owner, source);

    expect(second.id).toBe(first.id);
    expect(second.import_hash).toBe(first.import_hash);
    expect(services.projects.listProjects(owner)).toHaveLength(1);
  });

  it("titles chapters Chapter 1..N by filename order with no additional documents", async () => {
    const { auth, services } = await buildServices();
    const owner = await ownerPrincipal(auth);
    const source = legacySource();

    const project = services.imports.importLegacyWorkspace(owner, source);
    const detail = services.projects.projectDetail(owner, project.id as string);

    expect(
      (detail.payload.documents as Record<string, unknown>[]).map((document) => document.title),
    ).toEqual(["Chapter 1", "Chapter 2"]);
    const first = detail.documents[0];
    const second = detail.documents[1];
    expect(first?.currentRevision?.contentMarkdown).toBe("# First\n");
    expect(second?.currentRevision?.contentMarkdown).toBe("# Second\n");
    expect(JSON.parse(first?.currentRevision?.metadataJson ?? "{}")).toEqual({
      legacy_filename: "chapter-001.md",
    });
  });

  it("seeds one default volume holding the imported chapters", async () => {
    const { auth, services } = await buildServices();
    const owner = await ownerPrincipal(auth);
    const source = legacySource();

    const project = services.imports.importLegacyWorkspace(owner, source);
    const volumes = services.volumes.listVolumes(owner, project.id as string);
    expect(volumes).toHaveLength(1);
    const only = volumes[0] as Record<string, unknown>;
    expect(only).toMatchObject({ title: "Default Volume", position: 1 });

    // Every imported document is a chapter and every chapter lands in the
    // default volume — nothing stays unplaced.
    const detail = services.projects.projectDetail(owner, project.id as string);
    expect(detail.documents.length).toBeGreaterThan(0);
    for (const document of detail.documents) {
      expect(document.kind).toBe("chapter");
      expect(document.volumeId).toBe(only.id);
    }
  });

  it("rejects a directory without story.yaml", async () => {
    const { auth, services } = await buildServices();
    const owner = await ownerPrincipal(auth);
    const source = join(tmpdir(), `no-story-${Date.now()}-${Math.random()}`);

    expect(() => services.imports.importLegacyWorkspace(owner, source)).toThrowError(
      new InvalidOperationError("Legacy workspace must contain story.yaml."),
    );
  });

  it("leaves the source directory byte-identical", async () => {
    const { auth, services } = await buildServices();
    const owner = await ownerPrincipal(auth);
    const source = legacySource();
    const before = directoryFingerprint(source);

    services.imports.importLegacyWorkspace(owner, source);
    services.imports.importLegacyWorkspace(owner, source);

    expect(directoryFingerprint(source)).toBe(before);
  });
});
