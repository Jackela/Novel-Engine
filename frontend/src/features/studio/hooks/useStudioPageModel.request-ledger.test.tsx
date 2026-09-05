import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";
import { chapter, projectWith, volume } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";
import { StudioInspectorTabs } from "../StudioInspectorTabs";
import { StudioNavigator } from "../StudioNavigator";
import { resolveStudioRoute } from "../studioRouteState";
import { summarizeDocument } from "./projectState";
import { resetRevisionCacheForTests } from "./useRevisionCache";
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
    },
  };
});

const harness = createMountHarness();

// Multi-volume, multi-document fixture (#465): two chapters in volume one,
// one chapter in volume two, and one character entry that stays an on-screen
// sibling throughout — its body must never be prefetched.
const bodies: StudioDocument[] = [
  chapter("chapter-one", {
    volume_id: "volume-one",
    position: 0,
    content_markdown: "Chapter one body.",
  }),
  chapter("chapter-two", {
    volume_id: "volume-one",
    position: 1,
    content_markdown: "Chapter two body.",
  }),
  chapter("chapter-three", {
    volume_id: "volume-two",
    position: 0,
    content_markdown: "Chapter three body.",
  }),
  chapter("sibling-character", {
    kind: "character",
    volume_id: null,
    content_markdown: "Character body.",
  }),
];
const bodyById = new Map(bodies.map((body) => [body.id, body]));
const shellFixture = projectWith(bodies.map(summarizeDocument), {
  volumes: [volume("volume-one", 0), volume("volume-two", 1)],
});

let current: ReturnType<typeof useStudioPageModel> | undefined;

/** Mirrors the StudioPage wiring: URL-derived route feeding the page model. */
function StudioPageModelProbe() {
  const { projectId = "", section } = useParams();
  const location = useLocation();
  const route = resolveStudioRoute(projectId, section, location.search);
  const model = useStudioPageModel(projectId, route, useNavigate());
  current = model;
  const viewProps = model.viewProps;
  if (viewProps) {
    return (
      <>
        <StudioNavigator {...viewProps.navigator} />
        <StudioInspectorTabs
          inspector={viewProps.inspector.inspector}
          tabId={(tab) => `ledger-tab-${tab}`}
          panelId={(tab) => `ledger-panel-${tab}`}
          setInspector={viewProps.inspector.setInspector}
        />
      </>
    );
  }
  if (model.loadError) {
    return (
      <main aria-labelledby="ledger-retry-heading">
        <div aria-live="assertive" role="alert">
          <h1 id="ledger-retry-heading">Unable to open this project</h1>
          <p>{model.loadError}</p>
        </div>
        <button onClick={() => void current?.retryLoad()} type="button">
          Try again
        </button>
      </main>
    );
  }
  return null;
}

/** Drop the captured model without narrowing its later reads. */
function resetCapturedModel(): void {
  current = undefined;
}

function mountStudioPage(path: string): HTMLDivElement {
  return harness.mount(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<StudioPageModelProbe />} path="/projects/:projectId/:section?" />
      </Routes>
    </MemoryRouter>,
  ).container;
}

interface PageRequestLedger {
  readonly project: number;
  readonly providers: number;
  readonly documents: string[];
  readonly revisions: string[];
  readonly reviews: number;
  readonly exports: number;
  readonly jobs: number;
}

/** One snapshot of every request the mounted page issued. */
function requestLedger(): PageRequestLedger {
  return {
    project: vi.mocked(api.project).mock.calls.length,
    providers: vi.mocked(api.providers).mock.calls.length,
    documents: vi.mocked(api.document).mock.calls.map((call) => call[1]),
    revisions: vi.mocked(api.revisions).mock.calls.map((call) => call[1]),
    reviews: vi.mocked(api.reviews).mock.calls.length,
    exports: vi.mocked(api.exports).mock.calls.length,
    jobs: vi.mocked(api.jobs).mock.calls.length,
  };
}

function seedApiMocks(): void {
  vi.mocked(api.project).mockReset().mockResolvedValue(shellFixture);
  vi.mocked(api.document)
    .mockReset()
    .mockImplementation(async (_projectId, documentId) => {
      const body = bodyById.get(documentId);
      if (!body) throw new Error(`Unexpected document body request for ${documentId}.`);
      return body;
    });
  vi.mocked(api.providers).mockReset().mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockReset().mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockReset().mockResolvedValue({ revisions: [], next_cursor: null });
  vi.mocked(api.reviews).mockReset().mockResolvedValue({ reviews: [] });
  vi.mocked(api.exports).mockReset().mockResolvedValue({ exports: [] });
}

async function settleUntil(description: string, ready: () => boolean): Promise<void> {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (ready()) return;
    await flushEffects();
  }
  throw new Error(`Timed out waiting for ${description}.`);
}

async function click(container: HTMLDivElement, role: string, name: string): Promise<void> {
  await act(async () => {
    fireEvent.click(getByRole(container, role, { name }));
  });
}

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

describe("Studio page request ledger", () => {
  it("reads one shell plus one route-compatible active Document and keeps every other resource lazy", async () => {
    seedApiMocks();
    const container = mountStudioPage("/projects/project-1/manuscript");
    await settleUntil(
      "the bootstrap active Document",
      () => current?.viewProps?.editor.activeDocument?.id === "chapter-one",
    );

    // Bootstrap: the whole page cost is one bounded shell read, one body read
    // for the route-default active Document, and its own history page. Every
    // sibling row and volume header is on screen, yet no sibling body, no
    // Review history, no Export history, and no Jobs page is ever requested.
    expect(getByRole(container, "button", { name: "Titled sibling-character" })).toBeTruthy();
    expect(container.textContent).toContain("volume-one");
    expect(container.textContent).toContain("volume-two");
    expect(vi.mocked(api.project).mock.calls[0]?.[0]).toBe("project-1");
    expect(current?.viewProps?.editor.activeDocument).toBe(bodyById.get("chapter-one"));
    expect(requestLedger()).toEqual({
      project: 1,
      providers: 1,
      documents: ["chapter-one"],
      revisions: ["chapter-one"],
      reviews: 0,
      exports: 0,
      jobs: 0,
    });

    // Selecting the Review inspector reads exactly its own history once and
    // nothing else: no shell reread, no active-body reread.
    await click(container, "tab", "Review");
    await settleUntil(
      "the first Review history read",
      () => vi.mocked(api.reviews).mock.calls.length >= 1,
    );
    expect(requestLedger()).toEqual({
      project: 1,
      providers: 1,
      documents: ["chapter-one"],
      revisions: ["chapter-one"],
      reviews: 1,
      exports: 0,
      jobs: 0,
    });

    // Switching to Export reads only the Export history; Review stays cached.
    await click(container, "tab", "Export");
    await settleUntil(
      "the first Export history read",
      () => vi.mocked(api.exports).mock.calls.length >= 1,
    );
    expect(requestLedger()).toEqual({
      project: 1,
      providers: 1,
      documents: ["chapter-one"],
      revisions: ["chapter-one"],
      reviews: 1,
      exports: 1,
      jobs: 0,
    });

    // Switching to another chapter in the same volume costs exactly one new
    // body read (plus its own history page) — never a shell reread.
    await click(container, "button", "Titled chapter-two");
    await settleUntil(
      "the chapter-two body",
      () => current?.viewProps?.editor.activeDocument?.id === "chapter-two",
    );
    expect(current?.viewProps?.editor.activeDocument).toBe(bodyById.get("chapter-two"));
    expect(requestLedger()).toEqual({
      project: 1,
      providers: 1,
      documents: ["chapter-one", "chapter-two"],
      revisions: ["chapter-one", "chapter-two"],
      reviews: 1,
      exports: 1,
      jobs: 0,
    });

    // Switching across volumes costs exactly one new body read as well.
    await click(container, "button", "Titled chapter-three");
    await settleUntil(
      "the chapter-three body",
      () => current?.viewProps?.editor.activeDocument?.id === "chapter-three",
    );
    expect(requestLedger()).toEqual({
      project: 1,
      providers: 1,
      documents: ["chapter-one", "chapter-two", "chapter-three"],
      revisions: ["chapter-one", "chapter-two", "chapter-three"],
      reviews: 1,
      exports: 1,
      jobs: 0,
    });

    // Navigating to the Characters section activates the section-compatible
    // document with exactly one body read; chapters never leak into it.
    await click(container, "button", "Characters");
    await settleUntil(
      "the route-compatible character body",
      () => current?.viewProps?.editor.activeDocument?.id === "sibling-character",
    );
    expect(requestLedger()).toEqual({
      project: 1,
      providers: 1,
      documents: ["chapter-one", "chapter-two", "chapter-three", "sibling-character"],
      revisions: ["chapter-one", "chapter-two", "chapter-three", "sibling-character"],
      reviews: 1,
      exports: 1,
      jobs: 0,
    });

    // Shell failure and retry replay exactly the same ledger: one failed shell
    // read keeps every downstream resource untouched (useStudioProject retry
    // semantics), and one retry republishes the shell plus its single active
    // Document while both inspector histories stay lazy.
    harness.cleanup();
    resetRevisionCacheForTests();
    seedApiMocks();
    vi.mocked(api.project)
      .mockReset()
      .mockRejectedValueOnce(new HttpError("Service unavailable.", 503))
      .mockResolvedValue(shellFixture);
    resetCapturedModel();

    const retryContainer = mountStudioPage("/projects/project-1/manuscript");
    await settleUntil("the failed shell surface", () => typeof current?.loadError === "string");
    expect(current?.project).toBeNull();
    expect(current?.viewProps).toBeNull();
    expect(current?.loadError).toBe("Service unavailable.");
    expect(getByRole(retryContainer, "button", { name: "Try again" })).toBeTruthy();
    expect(requestLedger()).toEqual({
      project: 1,
      providers: 1,
      documents: [],
      revisions: [],
      reviews: 0,
      exports: 0,
      jobs: 0,
    });

    await click(retryContainer, "button", "Try again");
    await settleUntil(
      "the retried active Document",
      () => current?.viewProps?.editor.activeDocument?.id === "chapter-one",
    );
    expect(requestLedger()).toEqual({
      project: 2,
      providers: 1,
      documents: ["chapter-one"],
      revisions: ["chapter-one"],
      reviews: 0,
      exports: 0,
      jobs: 0,
    });
  });
});
