import { cpSync } from "node:fs";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, describe, expect, it } from "vitest";
import {
  createStudioServices,
  type StudioPersistence,
} from "../../src/contexts/studio/application/studio_services.js";
import { DocumentStorePart } from "../../src/contexts/studio/infrastructure/document_store_part.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { FsLegacyWorkspaceReader } from "../../src/contexts/studio/infrastructure/fs_legacy_workspace_reader.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { LoreStorePart } from "../../src/contexts/studio/infrastructure/lore_store_part.js";
import { FilesystemProjectArtifactCleaner } from "../../src/contexts/studio/infrastructure/project_artifact_files.js";
import { ProjectStorePart } from "../../src/contexts/studio/infrastructure/project_store_part.js";
import { ProposalAcceptanceStorePart } from "../../src/contexts/studio/infrastructure/proposal_acceptance_store_part.js";
import { ProposalContextStorePart } from "../../src/contexts/studio/infrastructure/proposal_context_store_part.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import { VolumeStorePart } from "../../src/contexts/studio/infrastructure/volume_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import {
  openStudioDatabase,
  type StudioDatabase,
} from "../../src/shared/infrastructure/db/startup.js";
import { capturingFactory } from "../api/proposal_test_helpers.js";

const opened: StudioDatabase[] = [];

/** Repo-root location of the shipped demo workspace this suite imports. */
const DEMO_WORKSPACE = join(import.meta.dirname, "../../../examples/demo-workspace");

const DEMO_TITLE = "The Cartographer of Lost Hours";
const DEMO_PREMISE =
  "A mapmaker inherits an atlas that charts places erased from the world, and discovers someone is unwriting them faster than she can draw.";

/**
 * The shipped `examples/demo-workspace` backs the documented two-minute demo,
 * so its exact bytes must keep importing. Each test copies the committed
 * example into a hermetic temp directory — the source tree is never the
 * import target — and runs the same service graph as the legacy import suite.
 */
async function buildServicesWithDemoCopy(): Promise<{
  owner: Principal;
  services: ReturnType<typeof createStudioServices>;
  source: string;
}> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-demo-import-"));
  const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  opened.push(database);
  const source = join(directory, "demo-workspace");
  cpSync(DEMO_WORKSPACE, source, { recursive: true });
  const auth = new AuthService({
    store: new DrizzleAuthStore(database.db),
    sessionSecret: "unit-test-session-secret",
  });
  await auth.configureOwner("archivist", "correct horse battery");
  const owner = (await auth.createOwnerSession("archivist", "correct horse battery")).principal;
  const store: StudioPersistence = {
    projects: new ProjectStorePart(database.db),
    documents: new DocumentStorePart(database.db),
    volumes: new VolumeStorePart(database.db),
    lore: new LoreStorePart(database.db),
    jobs: new JobStorePart(database.db),
    reviewOutcomes: new ReviewStorePart(database.db),
    proposalContext: new ProposalContextStorePart(database.db),
    proposalAcceptance: new ProposalAcceptanceStorePart(database.db),
  };
  const services = createStudioServices(store, {
    providerFactory: capturingFactory({}).factory,
    legacyWorkspaceReader: new FsLegacyWorkspaceReader(),
    artifactStore: new ExportStorePart(database.db),
    artifactFiles: new FilesystemExportArtifactGateway(directory),
    projectArtifactCleaner: new FilesystemProjectArtifactCleaner(directory),
  });
  return { owner, services, source };
}

afterAll(() => {
  for (const database of opened) {
    database.close();
  }
});

describe("shipped demo workspace import", () => {
  it("imports the example with its title, premise, and four chapters in order", async () => {
    const { owner, services, source } = await buildServicesWithDemoCopy();

    const imported = await services.imports.importLegacyWorkspace(owner, source);

    expect(imported.created).toBe(true);
    expect(imported.title).toBe(DEMO_TITLE);
    expect(imported.description).toBe(DEMO_PREMISE);
    expect(imported.chapter_count).toBe(4);

    const detail = services.projects.projectShell(owner, imported.project_id);
    expect(detail.documents.map((document) => document.title)).toEqual([
      "Chapter 1",
      "Chapter 2",
      "Chapter 3",
      "Chapter 4",
    ]);
    const firstSummary = detail.documents[0];
    if (firstSummary === undefined) {
      throw new Error("Expected the first imported chapter summary.");
    }
    const first = services.documents.currentDocument(owner, imported.project_id, firstSummary.id);
    expect(first.content_markdown).toContain("# Chapter 1: The Inheritance of Coastlines");
  });

  it("re-imports the same demo copy into the existing project", async () => {
    const { owner, services, source } = await buildServicesWithDemoCopy();

    const first = await services.imports.importLegacyWorkspace(owner, source);
    const second = await services.imports.importLegacyWorkspace(owner, source);

    expect(first.created).toBe(true);
    expect(second.created).toBe(false);
    expect(second.project_id).toBe(first.project_id);
    expect(second.import_hash).toBe(first.import_hash);
    expect(second.chapter_count).toBe(4);
  });
});
