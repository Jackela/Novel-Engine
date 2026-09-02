import { EventEmitter } from "node:events";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { textProviderFactory } from "../../src/contexts/ai/infrastructure/providers/text_provider_factory.js";
import { InFlightOperationGuard } from "../../src/contexts/studio/application/operation_in_flight.js";
import type { StudioStore } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ProjectService } from "../../src/contexts/studio/application/project_service.js";
import { AiProposalService } from "../../src/contexts/studio/application/proposal_service.js";
import type { ProposalStreamFrame } from "../../src/contexts/studio/application/proposal_streaming.js";
import { documentRevisions } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import {
  ProposalStreamDrainTimeoutError,
  writeProposalStreamResponse,
} from "../../src/contexts/studio/interface/http/proposal_stream_response.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { DATABASE_FILENAME } from "../../src/shared/infrastructure/db/backup.js";
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

class BackpressureResponse extends EventEmitter {
  readonly chunks: string[] = [];
  destroyed = false;
  writableFinished = false;

  constructor(private readonly backpressureOn: (chunk: string) => boolean) {
    super();
  }

  writeHead(): this {
    return this;
  }

  write(chunk: string): boolean {
    this.chunks.push(chunk);
    return !this.backpressureOn(chunk);
  }

  end(): this {
    this.writableFinished = true;
    return this;
  }

  destroy(): this {
    this.destroyed = true;
    return this;
  }
}

// Direct-service harness for abort paths that `app.inject` cannot expose
// because it buffers the complete response.
async function openProposalStreamHarness(
  providerFactory: TextGenerationProviderFactory = textProviderFactory({}, {}),
): Promise<ServiceHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-proposal-stream-"));
  const studio = await openStudioDatabase(join(directory, DATABASE_FILENAME));
  const now = (): Date => new Date();
  const store: StudioStore = new DrizzleStudioStore({
    database: studio.db,
  });
  const inFlight = new InFlightOperationGuard();
  const auth = new AuthService({
    store: new DrizzleAuthStore(studio.db),
    sessionSecret: "proposal-stream-test-secret",
    now,
  });
  await auth.configureOwner("streamer", "long-test-password");
  return {
    proposals: new AiProposalService(store, providerFactory, inFlight, now),
    projects: new ProjectService(store, now, { inFlight }),
    principal: (await auth.createOwnerSession("streamer", "long-test-password")).principal,
    db: studio.db,
    cleanup: async () => {
      studio.close();
      await rm(directory, { recursive: true, force: true });
    },
  };
}

// Collect every frame from a normally drained proposal stream.
async function collectStream(
  stream: AsyncGenerator<ProposalStreamFrame, void, void>,
): Promise<ProposalStreamFrame[]> {
  const frames: ProposalStreamFrame[] = [];
  for await (const frame of stream) {
    frames.push(frame);
  }
  return frames;
}

async function timeOutProposalResponse(
  harness: ServiceHarness,
  title: string,
  backpressureOn: (chunk: string) => boolean,
): Promise<{ response: BackpressureResponse; revisionsBefore: number }> {
  const project = harness.projects.newProject(harness.principal, { title }) as {
    id: string;
    documents: Array<{ id: string }>;
  };
  const document = project.documents[0];
  if (document === undefined) throw new Error("fixture must seed a document");
  const revisionsBefore = harness.db.select().from(documentRevisions).all().length;
  const disconnect = new AbortController();
  const response = new BackpressureResponse(backpressureOn);
  const frames = harness.proposals.draftProposalStream(
    harness.principal,
    project.id,
    document.id,
    { operation: "continue", instruction: "", provider: "mock" },
    () => {},
    disconnect.signal,
  );
  await expect(
    writeProposalStreamResponse({
      response,
      socket: new EventEmitter(),
      frames,
      disconnect,
      hijack: () => {},
      drainTimeoutMs: 5,
    }),
  ).rejects.toBeInstanceOf(ProposalStreamDrainTimeoutError);
  return { response, revisionsBefore };
}

const failingStreamProviderFactory: TextGenerationProviderFactory = () => ({
  generateStructured: async () => {
    throw new Error("the synchronous path must not run");
  },
  async *generateStructuredStreaming() {
    yield "A partial proposal reached the client before the provider failed. ".repeat(8);
    throw new TextGenerationProviderError("provider stream failed");
  },
});

describe("proposal stream service (#308 abort semantics)", () => {
  it("releases project ownership when a partially consumed stream is returned", async () => {
    const harness = await openProposalStreamHarness();
    try {
      const project = harness.projects.newProject(harness.principal, {
        title: "Returned stream",
      }) as { id: string; documents: Array<{ id: string }> };
      const document = project.documents[0];
      if (document === undefined) throw new Error("fixture must seed a document");
      const stream = harness.proposals.draftProposalStream(
        harness.principal,
        project.id,
        document.id,
        { operation: "continue", instruction: "", provider: "mock" },
        () => {},
      );
      expect((await stream.next()).done).toBe(false);

      await expect(harness.projects.removeProject(harness.principal, project.id)).rejects.toThrow(
        /continue operation is already running/i,
      );
      await stream.return();
      await expect(
        harness.projects.removeProject(harness.principal, project.id),
      ).resolves.toBeUndefined();
    } finally {
      await harness.cleanup();
    }
  });

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

  it("keeps a programming failure visible when provider cleanup aborts the request", async () => {
    const controller = new AbortController();
    const programmingError = new RangeError("stream extractor defect");
    const providerFactory: TextGenerationProviderFactory = () => ({
      generateStructured: async () => {
        throw new Error("the synchronous path must not run");
      },
      async *generateStructuredStreaming() {
        try {
          yield await Promise.reject<string>(programmingError);
        } finally {
          controller.abort();
        }
      },
    });
    const harness = await openProposalStreamHarness(providerFactory);
    try {
      const project = harness.projects.newProject(harness.principal, {
        title: "Programming failure",
      }) as { id: string; documents: Array<{ id: string }> };
      const document = project.documents[0];
      if (document === undefined) throw new Error("fixture must seed a document");
      const stream = harness.proposals.draftProposalStream(
        harness.principal,
        project.id,
        document.id,
        { operation: "continue", instruction: "", provider: "mock" },
        () => {},
        controller.signal,
      );

      await expect(stream.next()).rejects.toBe(programmingError);
      expect(harness.db.select().from(jobs).all()).toHaveLength(0);
      expect(harness.db.select().from(usageEvents).all()).toHaveLength(0);
      await expect(
        harness.projects.removeProject(harness.principal, project.id),
      ).resolves.toBeUndefined();
    } finally {
      await harness.cleanup();
    }
  });

  it("persists nothing when downstream drain times out before a terminal frame", async () => {
    const harness = await openProposalStreamHarness();
    try {
      const { response, revisionsBefore } = await timeOutProposalResponse(
        harness,
        "Pre-terminal backpressure timeout",
        () => true,
      );

      expect(response.destroyed).toBe(true);
      expect(response.writableFinished).toBe(false);
      expect(harness.db.select().from(jobs).all()).toHaveLength(0);
      expect(harness.db.select().from(usageEvents).all()).toHaveLength(0);
      expect(harness.db.select().from(documentRevisions).all()).toHaveLength(revisionsBefore);
    } finally {
      await harness.cleanup();
    }
  });

  it.each([
    { terminal: "done", status: "completed", usageCount: 1, providerFactory: undefined },
    {
      terminal: "error",
      status: "failed",
      usageCount: 0,
      providerFactory: failingStreamProviderFactory,
    },
  ])(
    "preserves the original $status job when its $terminal frame drain times out",
    async (testCase) => {
      const harness = await openProposalStreamHarness(testCase.providerFactory);
      try {
        const { response, revisionsBefore } = await timeOutProposalResponse(
          harness,
          `Terminal ${testCase.terminal} backpressure timeout`,
          (chunk) => chunk.includes(`"type":"${testCase.terminal}"`),
        );
        expect(response.destroyed).toBe(true);
        expect(response.chunks.at(-1)).toContain(`"type":"${testCase.terminal}"`);
        expect(response.chunks.filter((chunk) => chunk.includes('"type":"error"'))).toHaveLength(
          testCase.terminal === "error" ? 1 : 0,
        );
        const jobRows = harness.db.select().from(jobs).all();
        expect(jobRows).toHaveLength(1);
        expect(jobRows[0]?.status).toBe(testCase.status);
        expect(harness.db.select().from(usageEvents).all()).toHaveLength(testCase.usageCount);
        expect(harness.db.select().from(documentRevisions).all()).toHaveLength(revisionsBefore);
      } finally {
        await harness.cleanup();
      }
    },
  );
});
