import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { SnapshotArtifactService } from "../../src/contexts/studio/application/export_artifact_service.js";
import { JobHistoryService } from "../../src/contexts/studio/application/job_history_service.js";
import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import type { JobRecord } from "../../src/contexts/studio/application/ports/job_records.js";
import type { ProjectScope } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ProposalGenerationPipeline } from "../../src/contexts/studio/application/proposal_pipeline.js";
import { ReviewService } from "../../src/contexts/studio/application/review_service.js";
import type { StudioPersistence } from "../../src/contexts/studio/application/studio_services.js";
import { NotFoundError } from "../../src/contexts/studio/domain/exceptions.js";
import { DocumentStorePart } from "../../src/contexts/studio/infrastructure/document_store_part.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { LoreStorePart } from "../../src/contexts/studio/infrastructure/lore_store_part.js";
import { ProjectStorePart } from "../../src/contexts/studio/infrastructure/project_store_part.js";
import { ProposalAcceptanceStorePart } from "../../src/contexts/studio/infrastructure/proposal_acceptance_store_part.js";
import { ProposalContextStorePart } from "../../src/contexts/studio/infrastructure/proposal_context_store_part.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import { VolumeStorePart } from "../../src/contexts/studio/infrastructure/volume_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];

afterEach(async () => {
  await Promise.all(
    directories.splice(0).map((directory) => rm(directory, { recursive: true, force: true })),
  );
});

function history(store: StudioPersistence, exportStore: ExportStorePart): JobHistoryService {
  const providerFactory = () => {
    throw new Error("unexpected provider request");
  };
  const inFlight = new InFlightOperationGuard();
  return new JobHistoryService(
    store.jobs,
    store.reviewOutcomes,
    new ReviewService(store.reviewOutcomes, { providerFactory }),
    new SnapshotArtifactService(exportStore, {
      async writeSnapshotArtifact() {
        throw new Error("unexpected artifact write");
      },
      async readArtifactBytes() {
        throw new Error("unexpected artifact read");
      },
    }),
    {
      inFlight,
      proposals: new ProposalGenerationPipeline(
        store.proposalContext,
        store.jobs,
        providerFactory,
        inFlight,
      ),
    },
  );
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-job-summary-service-"));
  directories.push(directory);
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const store: StudioPersistence = {
    projects: new ProjectStorePart(studio.db),
    documents: new DocumentStorePart(studio.db),
    volumes: new VolumeStorePart(studio.db),
    lore: new LoreStorePart(studio.db),
    jobs: new JobStorePart(studio.db),
    reviewOutcomes: new ReviewStorePart(studio.db),
    proposalContext: new ProposalContextStorePart(studio.db),
    proposalAcceptance: new ProposalAcceptanceStorePart(studio.db),
  };
  const auth = new AuthService({
    store: new DrizzleAuthStore(studio.db),
    sessionSecret: "job-summary-service-secret",
  });
  await auth.configureOwner("job-summary-owner", "long-test-password");
  const principal = (await auth.createOwnerSession("job-summary-owner", "long-test-password"))
    .principal;
  return { principal, studio, store };
}

describe("JobHistoryService summary/detail reads", () => {
  it("normalizes only known scoped misses to the stable Job detail not-found error", async () => {
    const { principal, studio, store } = await openHarness();
    try {
      expect(() =>
        history(store, new ExportStorePart(studio.db)).findProjectJob(
          principal,
          "missing-project",
          "missing-job",
        ),
      ).toThrowError(expect.objectContaining({ name: "NotFoundError", message: "Job not found." }));
    } finally {
      studio.close();
    }
  });

  it("rethrows an unexpected store failure unchanged", async () => {
    const { principal, studio, store } = await openHarness();
    const failure = new Error("unexpected database failure");
    class UnexpectedFindJobsPart extends JobStorePart {
      override findJob(_scope: ProjectScope, _projectId: string, _jobId: string): JobRecord {
        throw failure;
      }
    }
    try {
      const exploding: StudioPersistence = {
        ...store,
        jobs: new UnexpectedFindJobsPart(studio.db),
      };
      expect(() =>
        history(exploding, new ExportStorePart(studio.db)).findProjectJob(
          principal,
          "project",
          "job",
        ),
      ).toThrow(failure);
      expect(failure).not.toBeInstanceOf(NotFoundError);
    } finally {
      studio.close();
    }
  });
});
