import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { textProviderFactory } from "../../src/contexts/ai/infrastructure/providers/text_provider_factory.js";
import { DocumentService } from "../../src/contexts/studio/application/document_service.js";
import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import type { StudioStore } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ProjectService } from "../../src/contexts/studio/application/project_service.js";
import { AiProposalService } from "../../src/contexts/studio/application/proposal_service.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { jobs, usageEvents } from "../../src/shared/infrastructure/db/schema.js";
import {
  openStudioDatabase,
  type StudioDatabase,
} from "../../src/shared/infrastructure/db/startup.js";

interface ServiceHarness {
  proposals: AiProposalService;
  projects: ProjectService;
  principal: Principal;
  db: StudioDatabase["db"];
  cleanup: () => Promise<void>;
}

/**
 * Direct-service harness for the abort path: `app.inject` buffers the whole
 * response, so a mid-stream disconnect can only be exercised against the
 * service generator itself.
 */
async function openProposalStreamHarness(): Promise<ServiceHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-proposal-stream-"));
  const studio = await openStudioDatabase(directory);
  const now = (): Date => new Date();
  const store: StudioStore = new DrizzleStudioStore({
    database: studio.db,
    dataDirectory: directory,
  });
  const documents = new DocumentService(store, now);
  const auth = new AuthService({
    store: new DrizzleAuthStore(studio.db),
    sessionSecret: "proposal-stream-test-secret",
    now,
  });
  await auth.configureOwner("streamer", "long-test-password");
  return {
    proposals: new AiProposalService(
      store,
      documents,
      textProviderFactory({}, {}),
      new InFlightOperationGuard(),
      now,
    ),
    projects: new ProjectService(store, now),
    principal: (await auth.createOwnerSession("streamer", "long-test-password")).principal,
    db: studio.db,
    cleanup: async () => {
      studio.close();
      await rm(directory, { recursive: true, force: true });
    },
  };
}

/** Frames of a fully drained proposal stream. */
async function collectStream(
  stream: AsyncGenerator<ProposalStreamFrame, void, void>,
): Promise<ProposalStreamFrame[]> {
  const frames: ProposalStreamFrame[] = [];
  for await (const frame of stream) {
    frames.push(frame);
  }
  return frames;
}

describe("proposal stream service (#308 abort semantics)", () => {
  it("aborts with nothing persisted and releases the in-flight guard", async () => {
    const harness = await openProposalStreamHarness();
    try {
      const project = harness.projects.newProject(harness.principal, {
        title: "Aborted stream",
      }) as { id: string; documents: Array<{ id: string }> };
      const document = project.documents[0];
      if (document === undefined) throw new Error("fixture must seed a document");

      const controller = new AbortController();
      const stream = harness.proposals.draftProposalStream(
        harness.principal,
        project.id,
        document.id,
        { operation: "continue", instruction: "", provider: "mock" },
        () => {},
        controller.signal,
      );
      const first = await stream.next();
      if (first.done || first.value.type !== "delta") {
        throw new Error("expected the stream to start with a delta");
      }
      controller.abort();
      const second = await stream.next();
      expect(second.done).toBe(true);
      expect(harness.db.select().from(jobs).all()).toHaveLength(0);
      expect(harness.db.select().from(usageEvents).all()).toHaveLength(0);

      // The in-flight guard was released: a fresh stream lands its job.
      const retried = await collectStream(
        harness.proposals.draftProposalStream(
          harness.principal,
          project.id,
          document.id,
          { operation: "continue", instruction: "", provider: "mock" },
          () => {},
        ),
      );
      expect(retried.at(-1)?.type).toBe("done");
      expect(harness.db.select().from(jobs).all()).toHaveLength(1);
      expect(harness.db.select().from(usageEvents).all()).toHaveLength(1);
    } finally {
      await harness.cleanup();
    }
  });
});
