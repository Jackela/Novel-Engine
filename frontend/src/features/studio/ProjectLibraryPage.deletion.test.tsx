import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Session } from "@/app/types/studio";
import { project } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { ProjectLibraryPage } from "./ProjectLibraryPage";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      deleteProject: vi.fn<typeof actual.api.deleteProject>(),
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

function renderLibrary() {
  return harness.mount(
    <MemoryRouter initialEntries={["/projects"]}>
      <Routes>
        <Route path="/" element={<p>Entry route</p>} />
        <Route path="/projects" element={<ProjectLibraryPage />} />
        <Route path="/projects/:projectId/manuscript" element={<p>Studio route</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function renderOneProject() {
  vi.mocked(api.session).mockResolvedValue(ownerSession);
  vi.mocked(api.projects).mockResolvedValue({
    projects: [project({ id: "project-1", title: "First novel" })],
    next_cursor: null,
  });
  const mounted = renderLibrary();
  await flushEffects();
  return mounted;
}

function rowTitles(container: HTMLElement): (string | null)[] {
  return [...container.querySelectorAll(".library__project-row strong")].map(
    (title) => title.textContent,
  );
}

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

describe("ProjectLibraryPage project deletion", () => {
  it("asks for confirmation and names the removed surface before deleting", async () => {
    const { container } = await renderOneProject();

    act(() => {
      getByRole(container, "button", { name: "Delete First novel" }).click();
    });

    const confirmation = getByRole(container, "group", {
      name: "Delete First novel confirmation",
    });
    expect(confirmation.textContent).toContain("Permanently delete First novel?");
    expect(confirmation.textContent).toContain("documents, revisions, exports, and snapshots");
    expect(confirmation.textContent).toContain("Backups are not touched.");
    expect(api.deleteProject).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(
      getByRole(container, "button", { name: "Confirm delete First novel" }),
    );
  });

  it("cancels the confirmation without calling the API or dropping the row", async () => {
    const { container } = await renderOneProject();

    act(() => {
      getByRole(container, "button", { name: "Delete First novel" }).click();
    });
    act(() => {
      getByRole(container, "button", { name: "Cancel delete First novel" }).click();
    });

    expect(container.querySelector(".library__project-confirm")).toBeNull();
    expect(api.deleteProject).not.toHaveBeenCalled();
    expect(rowTitles(container)).toEqual(["First novel"]);
    expect(document.activeElement).toBe(
      getByRole(container, "button", { name: "Delete First novel" }),
    );

    // Escape is the confirmation's second cancellation path.
    act(() => {
      getByRole(container, "button", { name: "Delete First novel" }).click();
    });
    act(() => {
      fireEvent.keyDown(getByRole(container, "button", { name: "Confirm delete First novel" }), {
        key: "Escape",
      });
    });

    expect(container.querySelector(".library__project-confirm")).toBeNull();
    expect(api.deleteProject).not.toHaveBeenCalled();
    expect(rowTitles(container)).toEqual(["First novel"]);
  });

  it("deletes the confirmed project once and refreshes the catalog", async () => {
    const first = project({ id: "project-1", title: "First novel" });
    const second = project({ id: "project-2", title: "Second novel" });
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects)
      .mockResolvedValueOnce({ projects: [first, second], next_cursor: null })
      .mockResolvedValueOnce({ projects: [second], next_cursor: null });
    const deletion = deferred<void>();
    vi.mocked(api.deleteProject).mockReturnValue(deletion.promise);

    const { container } = renderLibrary();
    await flushEffects();
    act(() => {
      getByRole(container, "button", { name: "Delete First novel" }).click();
    });
    const confirm = getByRole(container, "button", { name: "Confirm delete First novel" });
    act(() => {
      confirm.click();
      confirm.click();
    });

    expect(api.deleteProject).toHaveBeenCalledTimes(1);
    expect(api.deleteProject).toHaveBeenCalledWith("project-1");
    expect(confirm).toHaveAttribute("aria-busy", "true");
    expect(confirm).toBeDisabled();

    await act(async () => {
      deletion.resolve();
      await deletion.promise;
    });
    await flushEffects();

    expect(api.session).toHaveBeenCalledTimes(2);
    expect(api.projects).toHaveBeenCalledTimes(2);
    expect(rowTitles(container)).toEqual(["Second novel"]);
    expect(container.querySelector(".library__project-confirm")).toBeNull();
    expect(document.activeElement).toBe(getByRole(container, "heading", { name: "Projects" }));
  });

  it("keeps a failed deletion on its row and does not refresh the catalog", async () => {
    const { container } = await renderOneProject();
    vi.mocked(api.deleteProject).mockRejectedValue(
      new HttpError("Project deletion unavailable.", 503),
    );

    act(() => {
      getByRole(container, "button", { name: "Delete First novel" }).click();
    });
    await act(async () => {
      getByRole(container, "button", { name: "Confirm delete First novel" }).click();
    });
    await flushEffects();

    expect(api.deleteProject).toHaveBeenCalledTimes(1);
    expect(api.projects).toHaveBeenCalledTimes(1);
    expect(getByRole(container, "alert").textContent).toContain("Project deletion unavailable.");
    expect(container.querySelector(".library__project-confirm")).not.toBeNull();
    expect(rowTitles(container)).toEqual(["First novel"]);
  });
});
