import { fireEvent, getByRole, getByText } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { LANGUAGE_STORAGE_KEY } from "@/app/i18n/language";
import type { LoreExtractCandidate } from "@/app/types/lore";
import type { DocumentSummary, StudioJob } from "@/app/types/studio";
import { createMountHarness, flushEffects } from "@/test/harness";

import { StudioLorebookWizardPanel } from "./StudioLorebookWizardPanel";

vi.mock("@/app/api", () => ({
  api: {
    extractLore: vi.fn(),
    createDocument: vi.fn(),
    saveDocumentAliases: vi.fn(),
    document: vi.fn(),
  },
}));

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.clearAllMocks();
  window.localStorage.clear();
});

function loreJob(candidates: LoreExtractCandidate[]): StudioJob {
  return {
    id: "job-1",
    project_id: "project-1",
    document_id: null,
    kind: "lore-extract",
    operation: "extract",
    status: "completed",
    provider: "mock",
    model: "scripted-model",
    request: {},
    result: { candidates },
    error: null,
    retry_of_job_id: null,
    events: [],
    created_at: "2026-09-14T00:00:00.000Z",
    updated_at: "2026-09-14T00:00:00.000Z",
  };
}

function documentSummary(
  id: string,
  kind: DocumentSummary["kind"],
  title: string,
): DocumentSummary {
  return {
    id,
    project_id: "project-1",
    kind,
    title,
    position: 0,
    volume_id: null,
    beat_ref: null,
    lore_status: kind === "character" || kind === "world" ? "draft" : null,
    current_revision_id: `revision-${id}`,
    revision_source: "author",
    word_count: 0,
    created_at: "2026-09-14T00:00:00.000Z",
    updated_at: "2026-09-14T00:00:00.000Z",
  };
}

function renderPanel(provider: string, documents: DocumentSummary[] = []): HTMLDivElement {
  return harness.mount(
    <StudioLorebookWizardPanel documents={documents} projectId="project-1" provider={provider} />,
  ).container;
}

async function runExtraction(
  container: HTMLDivElement,
  candidates: LoreExtractCandidate[],
): Promise<void> {
  vi.mocked(api.extractLore).mockResolvedValueOnce(loreJob(candidates));
  fireEvent.change(getByRole(container, "textbox", { name: "Paste a draft segment" }), {
    target: { value: "text" },
  });
  fireEvent.submit(getByRole(container, "form", { name: "Paste a draft segment" }));
  await flushEffects();
}

describe("StudioLorebookWizardPanel", () => {
  it("surfaces the empty-lorebook guidance and the trial-mode label for a trial-provider project", () => {
    const container = renderPanel("mock");

    expect(getByRole(container, "heading", { name: "Lorebook wizard" })).toBeVisible();
    expect(
      getByText(
        container,
        "This project has no lore entries yet. Feed it a draft and confirm the suggestions to build your lorebook.",
      ),
    ).toBeVisible();
    expect(
      getByText(
        container,
        "Extraction runs on the built-in trial provider — connect a real one in Settings for real extraction.",
      ),
    ).toBeVisible();
  });

  it("renders the persistent entry without the trial label for a configured provider", () => {
    const container = renderPanel("dashscope", [documentSummary("doc-1", "character", "Mira")]);

    expect(container.textContent).not.toContain("trial provider");
    expect(
      getByText(
        container,
        "Extract more suggestions from draft material; confirmed entries land as drafts like any new entry.",
      ),
    ).toBeVisible();
  });

  it("renders the zh surface when the zh language is stored", () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");
    const container = renderPanel("mock");

    expect(getByRole(container, "heading", { name: "设定集向导" })).toBeVisible();
    // Empty paste keeps the extract command disabled — the label is the point.
    expect(getByRole(container, "button", { name: "抽取该段" })).toBeDisabled();
    expect(
      getByText(container, "抽取运行在内置试用提供方上 — 在设置中连接真实提供方即可进行真实抽取。"),
    ).toBeVisible();
  });

  it("extracts a pasted segment and lists its merged suggestions for selection", async () => {
    const container = renderPanel("mock");

    await runExtraction(container, [
      { kind: "character", title: "Mira", aliases: ["The Clerk"], summary: "Keeps the ledger." },
    ]);

    expect(api.extractLore).toHaveBeenCalledWith("project-1", "text", "mock");
    expect(getByText(container, "Mira")).toBeVisible();
    expect(getByRole(container, "button", { name: "Add 1 selected to lorebook" })).toBeEnabled();
  });

  it("toggles a candidate out of the confirmation set", async () => {
    const container = renderPanel("mock");
    await runExtraction(container, [
      { kind: "character", title: "Mira", aliases: [], summary: "a" },
      { kind: "world", title: "Ridge", aliases: ["Pass"], summary: "b" },
    ]);

    fireEvent.click(getByRole(container, "checkbox", { name: "Mira" }));

    expect(getByRole(container, "button", { name: "Add 1 selected to lorebook" })).toBeEnabled();
  });

  it("confirms through the existing creation and alias write calls and reports partial success", async () => {
    const container = renderPanel("mock");
    await runExtraction(container, [
      { kind: "world", title: "Ridge", aliases: ["Pass"], summary: "A high pass." },
    ]);
    vi.mocked(api.createDocument).mockResolvedValueOnce({
      id: "doc-ridge",
    } as Awaited<ReturnType<typeof api.createDocument>>);
    vi.mocked(api.saveDocumentAliases).mockRejectedValueOnce(new Error("alias write failed"));

    await act(async () => {
      fireEvent.click(getByRole(container, "button", { name: "Add 1 selected to lorebook" }));
      await flushEffects();
    });

    expect(api.createDocument).toHaveBeenCalledWith("project-1", {
      kind: "world",
      title: "Ridge",
      content_markdown: "A high pass.",
    });
    expect(api.saveDocumentAliases).toHaveBeenCalledWith("project-1", "doc-ridge", ["Pass"]);
    expect(getByText(container, "Created — alias write failed")).toBeVisible();
    expect(getByText(container, "Aliases kept for retry: Pass")).toBeVisible();

    // The retry entry reruns only the alias write and settles the outcome.
    vi.mocked(api.saveDocumentAliases).mockResolvedValueOnce({
      aliases: ["Pass"],
    } as Awaited<ReturnType<typeof api.saveDocumentAliases>>);
    await act(async () => {
      fireEvent.click(getByRole(container, "button", { name: "Retry alias write" }));
      await flushEffects();
    });
    expect(api.saveDocumentAliases).toHaveBeenCalledTimes(2);
    expect(getByText(container, "Created as draft")).toBeVisible();
  });

  it("abandoning the session leaves nothing created", async () => {
    const container = renderPanel("mock");
    await runExtraction(container, [
      { kind: "character", title: "Mira", aliases: [], summary: "a" },
    ]);

    await act(async () => {
      fireEvent.click(getByRole(container, "button", { name: "Discard suggestions" }));
      await Promise.resolve();
    });

    expect(api.createDocument).not.toHaveBeenCalled();
    expect(container.textContent).not.toContain("Mira");
  });

  it.each([
    [
      "an alias over the write-side length limit",
      `The ${"Clerk".repeat(60)}`,
      "“Mira” has an alias longer than 240 characters. Shorten it before confirming.",
    ],
    [
      "more aliases than the write-side count limit",
      Array.from({ length: 65 }, (_, index) => `alias${index}`).join(","),
      "“Mira” has more than 64 aliases. Remove some before confirming.",
    ],
  ])(
    "pre-checks %s before confirming instead of waiting for the write's 422",
    async (_label, draft, expectedError) => {
      const container = renderPanel("mock");
      await runExtraction(container, [
        { kind: "character", title: "Mira", aliases: [], summary: "a" },
      ]);

      await act(async () => {
        fireEvent.change(
          getByRole(container, "textbox", { name: "Aliases (comma-separated) — Mira" }),
          { target: { value: draft } },
        );
        await Promise.resolve();
      });
      await act(async () => {
        fireEvent.click(getByRole(container, "button", { name: "Add 1 selected to lorebook" }));
        await flushEffects();
      });

      expect(getByRole(container, "alert")).toHaveTextContent(expectedError);
      expect(api.createDocument).not.toHaveBeenCalled();
      expect(api.saveDocumentAliases).not.toHaveBeenCalled();
    },
  );

  it("keeps the candidates reachable after a confirmation through Start over", async () => {
    const container = renderPanel("mock");
    await runExtraction(container, [
      { kind: "character", title: "Mira", aliases: [], summary: "a" },
    ]);
    vi.mocked(api.createDocument).mockResolvedValueOnce({
      id: "doc-mira",
    } as Awaited<ReturnType<typeof api.createDocument>>);
    vi.mocked(api.saveDocumentAliases).mockResolvedValueOnce({ aliases: [] } as Awaited<
      ReturnType<typeof api.saveDocumentAliases>
    >);

    await act(async () => {
      fireEvent.click(getByRole(container, "button", { name: "Add 1 selected to lorebook" }));
      await flushEffects();
    });
    expect(getByText(container, "Created as draft")).toBeVisible();

    await act(async () => {
      fireEvent.click(getByRole(container, "button", { name: "Start over" }));
      await Promise.resolve();
    });

    // The segments — and the merged candidates they fold into — survive the
    // cleared results, so the author can run another confirmation.
    expect(getByText(container, "Mira")).toBeVisible();
    expect(getByRole(container, "button", { name: "Add 1 selected to lorebook" })).toBeEnabled();
  });
});
