import { getByRole, queryByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { ProjectCatalogItem, Session } from "@/app/types/studio";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { ProjectLibraryPage } from "./ProjectLibraryPage";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      projects: vi.fn<typeof actual.api.projects>(),
      session: vi.fn<typeof actual.api.session>(),
    },
  };
});

const harness = createMountHarness();
const ownerSession: Session = {
  session_id: "session-1",
  kind: "owner",
  owner_id: "owner-1",
  expires_at: "2026-10-01T00:00:00Z",
};

function catalogRow(id: string, title: string): ProjectCatalogItem {
  return {
    id,
    title,
    description: `Premise of ${title}`,
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-05T00:00:00Z",
  };
}

function LocationWitness() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}

function AwayControl() {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate("/away")} type="button">
      Leave library
    </button>
  );
}

function renderLibrary() {
  return harness.mount(
    <MemoryRouter initialEntries={["/projects"]}>
      <Routes>
        <Route path="/projects" element={<ProjectLibraryPage />} />
        <Route path="/away" element={<p>Away route</p>} />
      </Routes>
      <AwayControl />
      <LocationWitness />
    </MemoryRouter>,
  );
}

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

describe("ProjectLibraryPage bounded catalog traversal", () => {
  it("loads one first page and appends unique older rows after explicit activation", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects)
      .mockResolvedValueOnce({
        projects: [catalogRow("newer", "Newer draft")],
        next_cursor: "cursor-1",
      })
      .mockResolvedValueOnce({
        projects: [catalogRow("older", "Older draft"), catalogRow("newer", "Duplicate row")],
        next_cursor: null,
      });

    const { container } = renderLibrary();
    await flushEffects();

    expect(api.projects).toHaveBeenCalledTimes(1);
    expect(vi.mocked(api.projects).mock.calls[0]?.[0]).not.toHaveProperty("cursor");
    expect(getByRole(container, "button", { name: /Newer draft/ })).toBeDefined();

    const loadOlder = getByRole(container, "button", { name: "Load older projects" });
    await act(async () => {
      loadOlder.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(api.projects).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.projects).mock.calls[1]?.[0]?.cursor).toBe("cursor-1");
    expect(container.querySelectorAll(".library__project-row")).toHaveLength(2);
    expect(getByRole(container, "button", { name: /Older draft/ })).toBeDefined();
    expect(queryByRole(container, "button", { name: "Load older projects" })).toBeNull();
  });

  it("preserves committed rows and the cursor when an older page fails", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects)
      .mockResolvedValueOnce({
        projects: [catalogRow("kept", "Kept draft")],
        next_cursor: "cursor-1",
      })
      .mockRejectedValueOnce(new HttpError("Older projects unavailable.", 503))
      .mockResolvedValueOnce({
        projects: [catalogRow("recovered", "Recovered draft")],
        next_cursor: null,
      });

    const { container } = renderLibrary();
    await flushEffects();

    const loadOlder = getByRole(container, "button", { name: "Load older projects" });
    loadOlder.focus();
    await act(async () => {
      loadOlder.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(getByRole(container, "alert").textContent).toContain("Older projects unavailable.");
    expect(getByRole(container, "button", { name: /Kept draft/ })).toBeEnabled();
    const retryOlder = getByRole(container, "button", { name: "Load older projects" });
    expect(retryOlder).toBeEnabled();
    expect(document.activeElement).toBe(retryOlder);

    await act(async () => {
      retryOlder.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(getByRole(container, "button", { name: /Recovered draft/ })).toBeDefined();
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("moves terminal focus to the heading after the last older page", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects)
      .mockResolvedValueOnce({
        projects: [catalogRow("only", "Only draft")],
        next_cursor: "cursor-1",
      })
      .mockResolvedValueOnce({ projects: [], next_cursor: null });

    const { container } = renderLibrary();
    await flushEffects();

    const loadOlder = getByRole(container, "button", { name: "Load older projects" });
    loadOlder.focus();
    await act(async () => {
      loadOlder.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(document.activeElement).toBe(getByRole(container, "heading", { name: "Projects" }));
  });

  it("exposes a busy state and ignores duplicate older activations", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    const olderPage = deferred<Awaited<ReturnType<typeof api.projects>>>();
    vi.mocked(api.projects)
      .mockResolvedValueOnce({
        projects: [catalogRow("page-one", "Page one")],
        next_cursor: "cursor-1",
      })
      .mockReturnValueOnce(olderPage.promise);

    const { container } = renderLibrary();
    await flushEffects();

    const loadOlder = getByRole(container, "button", { name: "Load older projects" });
    act(() => {
      loadOlder.click();
    });
    const busy = getByRole(container, "button", { name: "Loading older projects..." });
    expect(busy).toBeDisabled();
    expect(busy).toHaveAttribute("aria-busy", "true");
    expect(getByRole(container, "button", { name: /Page one/ })).toBeDisabled();

    act(() => {
      busy.click();
    });
    expect(api.projects).toHaveBeenCalledTimes(2);

    await act(async () => {
      olderPage.resolve({ projects: [catalogRow("older", "Older draft")], next_cursor: null });
      await olderPage.promise;
    });
    expect(getByRole(container, "button", { name: /Older draft/ })).toBeEnabled();
  });

  it("does not publish a stale older page after leaving the library", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    const olderPage = deferred<Awaited<ReturnType<typeof api.projects>>>();
    vi.mocked(api.projects)
      .mockResolvedValueOnce({
        projects: [catalogRow("visible", "Visible draft")],
        next_cursor: "cursor-1",
      })
      .mockReturnValueOnce(olderPage.promise);

    const { container } = renderLibrary();
    await flushEffects();

    const loadOlder = getByRole(container, "button", { name: "Load older projects" });
    act(() => {
      loadOlder.click();
      getByRole(container, "button", { name: "Leave library" }).click();
    });

    await act(async () => {
      olderPage.resolve({ projects: [catalogRow("stale", "Stale draft")], next_cursor: null });
      await olderPage.promise;
    });

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/away");
    expect(container.textContent).not.toContain("Stale draft");
  });
});
