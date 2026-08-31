import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project, Review, StudioJob } from "@/app/types/studio";
import type { InspectorTab } from "@/features/studio/studioConstants";
import { chapter, job, projectWith, review } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioActions } from "./useStudioActions";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      createDocument: vi.fn<typeof actual.api.createDocument>(),
      reorderDocuments: vi.fn<typeof actual.api.reorderDocuments>(),
      createReview: vi.fn<typeof actual.api.createReview>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
      updateProject: vi.fn<typeof actual.api.updateProject>(),
      retryJob: vi.fn<typeof actual.api.retryJob>(),
      saveLoreStatus: vi.fn<typeof actual.api.saveLoreStatus>(),
    },
  };
});

interface HarnessSnapshot {
  readonly actions: ReturnType<typeof useStudioActions>;
  readonly project: Project | null;
  readonly reviews: Review[];
  readonly error: string | null;
  readonly activeId: string | null;
  readonly inspector: InspectorTab;
}

const chapterOne = chapter("chapter-1", {
  title: "Chapter One",
  current_revision_id: "revision-1",
  content_markdown: "# Chapter 1\n\n",
  revision_source: "manual",
  word_count: 2,
});
const note = {
  ...chapterOne,
  id: "note-1",
  kind: "note" as const,
  title: "Note One",
  position: 1,
  content_markdown: "",
};
const projectFixture = projectWith([chapterOne, note], {
  description: "Old description",
  settings: { provider: "mock", temperature: 0.5 },
});
const character = chapter("character-1", {
  kind: "character",
  title: "Mara",
  volume_id: null,
  lore_status: "draft",
});
const world = chapter("world-1", {
  kind: "world",
  title: "Harbor",
  volume_id: null,
  lore_status: "stable",
});
const loreProjectFixture = projectWith([character, world], {
  description: "Lore project",
  settings: { provider: "mock" },
});
const reviewFixture = review({ project_id: projectFixture.id });
const reviewJob = job({
  id: "job-review-1",
  project_id: projectFixture.id,
  document_id: null,
  kind: "review" as const,
  operation: "review" as const,
  result: { review_id: "review-1" },
  events: [
    {
      id: "event-1",
      status: "completed" as const,
      details: { review_id: "review-1" },
      created_at: "2026-08-27T00:01:00Z",
    },
  ],
});
const retriedJob = job({
  project_id: projectFixture.id,
  document_id: chapterOne.id,
  status: "pending" as const,
  retry_of_job_id: "failed-job-1",
});
const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderActions(
  loadJobs: ReturnType<typeof vi.fn<() => Promise<void>>> = vi
    .fn<() => Promise<void>>()
    .mockResolvedValue(undefined),
  initialProject: Project = projectFixture,
): {
  readonly result: () => HarnessSnapshot;
  readonly loadJobs: ReturnType<typeof vi.fn<() => Promise<void>>>;
  readonly submitSettings: () => void;
} {
  let current: HarnessSnapshot | undefined;

  function Wrapper() {
    const [project, setProject] = useState<Project | null>(initialProject);
    const [reviews, setReviews] = useState<Review[]>([]);
    const [error, setError] = useState<string | null>("previous error");
    const [activeId, setActiveId] = useState<string | null>(null);
    const [inspector, setInspector] = useState<InspectorTab>("history");
    const actions = useStudioActions({
      project,
      projectId: initialProject.id,
      setProject,
      setReviews,
      setError,
      setActiveId,
      setInspector,
      settingsForm: {
        title: "Updated Harbor",
        description: "Updated description",
        provider: "dashscope",
      },
      loadJobs,
    });
    current = { actions, project, reviews, error, activeId, inspector };
    return <form onSubmit={actions.updateProjectSettings} />;
  }

  const { container } = harness.mount(<Wrapper />);
  const form = container.querySelector("form");
  if (form === null) {
    throw new Error("Expected settings form after render.");
  }

  return {
    result: () => {
      if (current === undefined) {
        throw new Error("Expected actions hook result after render.");
      }
      return current;
    },
    loadJobs,
    submitSettings: () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    },
  };
}

describe("useStudioActions", () => {
  it("creates a numbered chapter, appends it, and activates it", async () => {
    // Given
    const created = {
      ...chapterOne,
      id: "chapter-2",
      title: "Chapter 2",
      position: 2,
    };
    vi.mocked(api.createDocument).mockResolvedValue(created);
    const harness = renderActions();

    // When
    await act(async () => {
      await harness.result().actions.createDocument("chapter");
    });

    // Then
    expect(api.createDocument).toHaveBeenCalledWith(projectFixture.id, {
      kind: "chapter",
      title: "Chapter 2",
      content_markdown: "# Chapter 2\n\n",
    });
    expect(harness.result().project?.documents).toEqual([chapterOne, note, created]);
    expect(harness.result().activeId).toBe(created.id);
  });

  it("reorders documents and publishes the server ordering", async () => {
    // Given
    const reordered = [
      { ...note, position: 0 },
      { ...chapterOne, position: 1 },
    ];
    vi.mocked(api.reorderDocuments).mockResolvedValue({ documents: reordered });
    const harness = renderActions();

    // When
    await act(async () => {
      await harness.result().actions.moveDocument(note.id, -1);
    });

    // Then
    expect(api.reorderDocuments).toHaveBeenCalledWith(projectFixture.id, [note.id, chapterOne.id]);
    expect(harness.result().project?.documents).toEqual(reordered);
  });

  it("runs a review job and refreshes the assessment list", async () => {
    // Given
    vi.mocked(api.createReview).mockResolvedValue(reviewJob);
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [reviewFixture] });
    const harness = renderActions();

    // When
    await act(async () => {
      await harness.result().actions.runReview();
    });

    // Then
    expect(api.reviews).toHaveBeenCalledWith(projectFixture.id);
    expect(harness.result().reviews).toEqual([reviewFixture]);
    expect(harness.result().inspector).toBe("review");
  });

  it("reports a failed review job without switching inspector", async () => {
    // Given
    vi.mocked(api.createReview).mockResolvedValue({
      ...reviewJob,
      status: "failed",
      error: "Review could not be evaluated.",
    });
    const harness = renderActions();

    // When
    await act(async () => {
      await harness.result().actions.runReview();
    });

    // Then
    expect(api.reviews).not.toHaveBeenCalled();
    expect(harness.result().reviews).toEqual([]);
    expect(harness.result().error).toBe("Review could not be evaluated.");
  });

  it("updates settings while preserving unrelated project settings", async () => {
    // Given
    const updated = {
      ...projectFixture,
      title: "Updated Harbor",
      description: "Updated description",
      settings: { provider: "dashscope", temperature: 0.5 },
    };
    vi.mocked(api.updateProject).mockResolvedValue(updated);
    const harness = renderActions();

    // When
    await act(async () => {
      harness.submitSettings();
    });

    // Then
    expect(api.updateProject).toHaveBeenCalledWith(projectFixture.id, {
      title: "Updated Harbor",
      description: "Updated description",
      settings: { provider: "dashscope", temperature: 0.5 },
    });
    expect(harness.result().project).toEqual(updated);
    expect(harness.result().error).toBeNull();
  });

  it("reloads jobs after retrying a failed job", async () => {
    // Given
    let resolveLoadJobs: (() => void) | undefined;
    const loadJobs = vi.fn<() => Promise<void>>().mockReturnValue(
      new Promise<void>((resolve) => {
        resolveLoadJobs = resolve;
      }),
    );
    let resolveRetry: ((job: StudioJob) => void) | undefined;
    vi.mocked(api.retryJob).mockReturnValue(
      new Promise<StudioJob>((resolve) => {
        resolveRetry = resolve;
      }),
    );
    const harness = renderActions(loadJobs);

    // When
    const retryPromise = harness.result().actions.retryJob("job-1");
    await act(async () => {
      await Promise.resolve();
    });

    // Then
    expect(api.retryJob).toHaveBeenCalledWith(projectFixture.id, "job-1");
    expect(harness.result().actions.retryingJobId).toBe("job-1");

    await act(async () => {
      resolveRetry?.(retriedJob);
      await Promise.resolve();
    });

    expect(harness.loadJobs).toHaveBeenCalledTimes(1);
    expect(harness.result().actions.retryingJobId).toBe("job-1");

    await act(async () => {
      resolveLoadJobs?.();
      await retryPromise;
    });

    expect(harness.result().actions.retryingJobId).toBeNull();
  });

  it("keeps Lore status pending until the target document is patched", async () => {
    const response = deferred<{ lore_status: "stable" }>();
    vi.mocked(api.saveLoreStatus).mockReturnValue(response.promise);
    const actionsHarness = renderActions(undefined, loreProjectFixture);
    let savePromise!: Promise<void>;

    act(() => {
      savePromise = actionsHarness.result().actions.changeLoreStatus(character.id, "stable");
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(api.saveLoreStatus).toHaveBeenCalledWith(loreProjectFixture.id, character.id, "stable");
    expect(actionsHarness.result().actions.isChangingLoreStatus).toBe(true);
    expect(actionsHarness.result().project?.documents).toEqual([character, world]);

    await act(async () => {
      response.resolve({ lore_status: "stable" });
      await savePromise;
    });

    expect(actionsHarness.result().actions.isChangingLoreStatus).toBe(false);
    expect(actionsHarness.result().project?.documents).toEqual([
      { ...character, lore_status: "stable" },
      world,
    ]);
    expect(actionsHarness.result().error).toBeNull();
  });

  it("retains the saved Lore status and publishes an error when the update fails", async () => {
    vi.mocked(api.saveLoreStatus).mockRejectedValue(new Error("Lore status was rejected."));
    const actionsHarness = renderActions(undefined, loreProjectFixture);

    await act(async () => {
      await actionsHarness.result().actions.changeLoreStatus(character.id, "deprecated");
    });

    expect(actionsHarness.result().project?.documents).toEqual([character, world]);
    expect(actionsHarness.result().actions.isChangingLoreStatus).toBe(false);
    expect(actionsHarness.result().error).toBe("Lore status was rejected.");
  });
});
