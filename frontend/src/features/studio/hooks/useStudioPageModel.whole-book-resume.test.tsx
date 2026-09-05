import { fireEvent, getByRole, getByText } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { streamProposal } from "@/app/proposalStream";
import type { Project, RevisionSource, StudioDocument, StudioJob } from "@/app/types/studio";
import { chapter, job, projectWith, volume } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";
import { StudioNavigator } from "../StudioNavigator";
import { resolveStudioRoute } from "../studioRouteState";
import { summarizeDocument } from "./projectState";
import { useStudioPageModel } from "./useStudioPageModel";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn<typeof actual.api.project>(),
      document: vi.fn<typeof actual.api.document>(),
      providers: vi.fn<typeof actual.api.providers>(),
      jobs: vi.fn<typeof actual.api.jobs>(),
      revisions: vi.fn<typeof actual.api.revisions>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
      acceptProposal: vi.fn<typeof actual.api.acceptProposal>(),
    },
  };
});

vi.mock("@/app/proposalStream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/proposalStream")>();
  return { ...actual, streamProposal: vi.fn<typeof actual.streamProposal>() };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

interface ChapterSpec {
  readonly id: string;
  readonly title: string;
  readonly position: number;
  readonly volumeId: string;
  readonly source: RevisionSource;
}

const volumes = [volume("volume-one", 0), volume("volume-two", 1)];

/**
 * Five chapters across two volumes with mixed closed revision sources. The
 * shell deliberately lists them OUT of reading order so the plan proves the
 * volume-rank-then-position sort instead of echoing array order.
 */
const chapterSpecs: readonly ChapterSpec[] = [
  {
    id: "accepted-leader",
    title: "Accepted Leader",
    position: 0,
    volumeId: "volume-one",
    source: "ai-accepted",
  },
  {
    id: "author-one",
    title: "Author One",
    position: 1,
    volumeId: "volume-one",
    source: "author",
  },
  {
    id: "restore-one",
    title: "Restored One",
    position: 2,
    volumeId: "volume-one",
    source: "restore",
  },
  {
    id: "accepted-two",
    title: "Accepted Two",
    position: 0,
    volumeId: "volume-two",
    source: "ai-accepted",
  },
  {
    id: "author-two",
    title: "Author Two",
    position: 1,
    volumeId: "volume-two",
    source: "author",
  },
];

/** Shell row order differs from reading order; documents[0] stays the editor's. */
const shellOrder: readonly string[] = [
  "accepted-leader",
  "author-two",
  "accepted-two",
  "restore-one",
  "author-one",
];

function jobFor(documentId: string): StudioJob {
  return job({
    id: `job-${documentId}`,
    document_id: documentId,
    operation: "generate",
    result: { proposal_markdown: `Generated prose for ${documentId}.` },
  });
}

describe("Studio page whole-book resume planning (#464)", () => {
  it("resumes in reading order from the shell summaries without reading any sibling body", {
    timeout: 20_000,
  }, async () => {
    // Server-side state: full bodies plus the shell they project onto.
    const serverDocuments = new Map<string, StudioDocument>(
      chapterSpecs.map((spec) => [
        spec.id,
        chapter(spec.id, {
          title: spec.title,
          position: spec.position,
          volume_id: spec.volumeId,
          revision_source: spec.source,
          content_markdown: `Persisted body for ${spec.id}.`,
          word_count: 3,
        }),
      ]),
    );
    const serverDocument = (documentId: string): StudioDocument => {
      const document = serverDocuments.get(documentId);
      if (document === undefined) {
        throw new Error(`Missing server fixture for ${documentId}.`);
      }
      return document;
    };
    const serverShell = (): Project =>
      projectWith(
        shellOrder.map((documentId) => summarizeDocument(serverDocument(documentId))),
        { volumes },
      );

    // Request ledgers: the whole-book flow must never add sibling reads.
    const documentReads: string[] = [];
    const drafted: string[] = [];
    const acceptedDocuments: string[] = [];
    const heldSecondDraft = deferred<StudioJob>();
    const heldResumeDraft = deferred<StudioJob>();
    const heldFinalDraft = deferred<StudioJob>();

    vi.mocked(api.project).mockImplementation(async () => serverShell());
    vi.mocked(api.document).mockImplementation(async (_projectId, documentId) => {
      documentReads.push(documentId);
      return serverDocument(documentId);
    });
    vi.mocked(api.providers).mockResolvedValue({ providers: [] });
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
    vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [] });
    vi.mocked(api.acceptProposal).mockImplementation(async (_projectId, jobId) => {
      const documentId = jobId.slice("job-".length);
      const current = serverDocuments.get(documentId);
      if (current === undefined) throw new Error(`Unexpected acceptance target ${jobId}.`);
      serverDocuments.set(documentId, {
        ...current,
        current_revision_id: `revision-${documentId}-accepted`,
        revision_source: "ai-accepted",
        content_markdown: `AI-accepted prose for ${documentId}.`,
        word_count: current.word_count + 1,
      });
      acceptedDocuments.push(documentId);
      return jobFor(documentId);
    });
    vi.mocked(streamProposal)
      .mockImplementationOnce(async ({ documentId }) => {
        drafted.push(documentId);
        return jobFor(documentId);
      })
      .mockImplementationOnce(async ({ documentId }) => {
        drafted.push(documentId);
        return heldSecondDraft.promise;
      })
      .mockImplementationOnce(async ({ documentId }) => {
        drafted.push(documentId);
        return heldResumeDraft.promise;
      })
      .mockImplementationOnce(async ({ documentId }) => {
        drafted.push(documentId);
        return heldFinalDraft.promise;
      })
      .mockImplementation(async ({ documentId }) => {
        drafted.push(documentId);
        return jobFor(documentId);
      });

    const route = resolveStudioRoute("project-1", "manuscript", "");
    let current: ReturnType<typeof useStudioPageModel> | undefined;
    function Probe() {
      current = useStudioPageModel("project-1", route, useNavigate());
      const navigator = current.viewProps?.navigator;
      return navigator ? <StudioNavigator {...navigator} /> : null;
    }
    const { container } = harness.mount(
      <MemoryRouter initialEntries={[route.canonicalPath]}>
        <Probe />
      </MemoryRouter>,
    );
    const startButton = () =>
      getByRole(container, "button", { name: "Generate whole book" }) as HTMLButtonElement;
    const stopButton = () =>
      getByRole(container, "button", { name: "Stop generating" }) as HTMLButtonElement;
    const wholeBook = () => {
      const model = current?.viewProps?.navigator.wholeBook;
      if (!model) throw new Error("Expected a loaded whole-book navigator model.");
      return model;
    };
    // `vi.waitFor` starves the awaited act continuations here, so polling
    // uses real timers inside `act` instead.
    const settle = async (): Promise<void> => {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
      });
    };
    const waitForText = async (text: string): Promise<void> => {
      await act(async () => {
        const deadline = Date.now() + 5_000;
        for (;;) {
          try {
            getByText(container, text);
            return;
          } catch (reason) {
            if (Date.now() > deadline) throw reason;
            await new Promise((resolve) => setTimeout(resolve, 10));
          }
        }
      });
    };

    // Page load: the shell plus exactly one route-active editor body. The
    // plan is already derived from summary revision sources — with zero
    // chapter-body reads and both ai-accepted chapters skipped.
    await settle();
    expect(startButton().disabled).toBe(false);
    expect(wholeBook().remaining).toBe(3);
    expect(wholeBook().phase).toEqual({ kind: "idle" });
    expect(vi.mocked(api.project)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(api.document)).toHaveBeenCalledTimes(1);
    expect(documentReads).toEqual(["accepted-leader"]);

    // Run 1 drafts in reading order: author-one (volume one, position 1)
    // first even though the shell lists author-two earlier.
    await act(async () => {
      fireEvent.click(startButton());
    });
    await waitForText("Generating chapter 2 of 3…");
    expect(drafted).toEqual(["author-one", "restore-one"]);
    expect(acceptedDocuments).toEqual(["author-one"]);
    expect(vi.mocked(api.acceptProposal)).toHaveBeenLastCalledWith("project-1", "job-author-one");
    // Only the generated chapter's body was read; its siblings in the plan
    // and both skipped chapters stayed unfetched.
    expect(documentReads).toEqual(["accepted-leader", "author-one"]);
    expect(vi.mocked(api.project)).toHaveBeenCalledTimes(2);

    // Stop lands while the second chapter's draft is still in flight.
    await act(async () => {
      fireEvent.click(stopButton());
      expect(vi.mocked(streamProposal).mock.calls[1]?.[0].signal?.aborted).toBe(true);
      heldSecondDraft.resolve(jobFor("restore-one"));
    });
    await waitForText("Stopped — 1 chapter accepted this run.");
    expect(wholeBook().phase).toEqual({ kind: "done", generated: 1, stoppedEarly: true });
    // The abandoned chapter was never accepted and no body was read for it.
    expect(drafted).toEqual(["author-one", "restore-one"]);
    expect(acceptedDocuments).toEqual(["author-one"]);
    expect(documentReads).toEqual(["accepted-leader", "author-one"]);
    expect(vi.mocked(api.project)).toHaveBeenCalledTimes(2);
    // Resume recomputes the plan from the refreshed summaries: only the two
    // unaccepted chapters remain.
    expect(wholeBook().remaining).toBe(2);

    // Resume: the second run recomputes a two-chapter plan from the shell
    // summaries and starts at the first unaccepted chapter. Constructing
    // that plan issued no body or shell read of its own.
    expect(startButton().disabled).toBe(false);
    await act(async () => {
      fireEvent.click(startButton());
    });
    await waitForText("Generating chapter 1 of 2…");
    expect(drafted).toEqual(["author-one", "restore-one", "restore-one"]);
    expect(documentReads).toEqual(["accepted-leader", "author-one"]);
    expect(vi.mocked(api.project)).toHaveBeenCalledTimes(2);

    await act(async () => {
      heldResumeDraft.resolve(jobFor("restore-one"));
    });
    // The resumed run blocks on the final chapter's draft, so restore-one's
    // acceptance has flushed into the local shell: the plan shrank again.
    await waitForText("Generating chapter 2 of 2…");
    expect(drafted).toEqual(["author-one", "restore-one", "restore-one", "author-two"]);
    expect(documentReads).toEqual(["accepted-leader", "author-one", "restore-one"]);
    expect(vi.mocked(api.project)).toHaveBeenCalledTimes(3);
    expect(wholeBook().remaining).toBe(1);

    await act(async () => {
      heldFinalDraft.resolve(jobFor("author-two"));
    });
    await waitForText("Completed — 2 chapters accepted.");
    expect(wholeBook().phase).toEqual({ kind: "done", generated: 2, stoppedEarly: false });

    // Reading-order plan across volumes with ai-accepted chapters skipped.
    expect(drafted).toEqual(["author-one", "restore-one", "restore-one", "author-two"]);
    expect(vi.mocked(api.acceptProposal).mock.calls.map(([, jobId]) => jobId)).toEqual([
      "job-author-one",
      "job-restore-one",
      "job-author-two",
    ]);
    // Every whole-book body read targeted the chapter being generated, one
    // read per committed acceptance; no sibling body was ever requested.
    const loopBodyReads = documentReads.slice(1);
    expect(loopBodyReads).toEqual(["author-one", "restore-one", "author-two"]);
    expect(loopBodyReads).not.toContain("accepted-leader");
    expect(loopBodyReads).not.toContain("accepted-two");
    expect(vi.mocked(api.document)).toHaveBeenCalledTimes(4);
    // Shell convergence: the initial load plus exactly one refresh per
    // committed acceptance — start, stop, and resume planning added no
    // shell or body reads of their own. (The terminal acceptance's local
    // shell merge is ownership-guarded at flush time and is not observable
    // under act, which flushes it after the run ends; the server commit is
    // proven by the accept and refresh ledgers above.)
    expect(vi.mocked(api.project)).toHaveBeenCalledTimes(4);
    expect(vi.mocked(api.jobs)).toHaveBeenCalledTimes(3);
  });
});
