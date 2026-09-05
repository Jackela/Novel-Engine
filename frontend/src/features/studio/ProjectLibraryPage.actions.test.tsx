import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Project, Session } from "@/app/types/studio";
import { project } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { ProjectLibraryPage } from "./ProjectLibraryPage";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      createProject: vi.fn<typeof actual.api.createProject>(),
      logout: vi.fn<typeof actual.api.logout>(),
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

function rejectableDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
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
        <Route path="/" element={<p>Entry route</p>} />
        <Route path="/projects" element={<ProjectLibraryPage />} />
        <Route path="/projects/:projectId/manuscript" element={<p>Studio route</p>} />
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

describe("ProjectLibraryPage command ownership", () => {
  it("keeps Retry exclusive with logout and exposes both independent failures", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects).mockRejectedValue(new HttpError("Projects unavailable.", 503));
    const logout = rejectableDeferred<void>();
    vi.mocked(api.logout).mockReturnValue(logout.promise);

    const { container } = renderLibrary();
    await flushEffects();
    const signOut = getByRole(container, "button", { name: "Sign out" });
    const retry = getByRole(container, "button", { name: "Try again" });

    act(() => {
      signOut.click();
      retry.click();
    });

    expect(api.logout).toHaveBeenCalledTimes(1);
    expect(api.session).toHaveBeenCalledTimes(1);
    expect(retry).toBeDisabled();
    expect(retry).not.toHaveAttribute("aria-busy");

    await act(async () => {
      logout.reject(new HttpError("Unable to sign out now.", 503));
      await logout.promise.catch(() => undefined);
    });

    const alerts = Array.from(container.querySelectorAll('[role="alert"]')).map(
      (alert) => alert.textContent,
    );
    expect(alerts).toEqual(["Unable to sign out now.", "Projects unavailable."]);
    expect(retry).toBeEnabled();
  });

  it("keeps logout from starting in the same batch after Retry", async () => {
    const retrySession = deferred<Session>();
    vi.mocked(api.session)
      .mockResolvedValueOnce(ownerSession)
      .mockReturnValueOnce(retrySession.promise);
    vi.mocked(api.projects)
      .mockRejectedValueOnce(new HttpError("Projects unavailable.", 503))
      .mockResolvedValueOnce({ projects: [] });

    const { container } = renderLibrary();
    await flushEffects();
    const signOut = getByRole(container, "button", { name: "Sign out" });
    const retry = getByRole(container, "button", { name: "Try again" });

    act(() => {
      retry.click();
      signOut.click();
    });

    expect(api.session).toHaveBeenCalledTimes(2);
    expect(api.logout).not.toHaveBeenCalled();

    await act(async () => {
      retrySession.resolve(ownerSession);
      await retrySession.promise;
      await Promise.resolve();
    });
    expect(api.projects).toHaveBeenCalledTimes(2);
  });

  it("guards project creation against duplicate submission", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects).mockResolvedValue({ projects: [] });
    const created = deferred<Project>();
    vi.mocked(api.createProject).mockReturnValue(created.promise);

    const { container } = renderLibrary();
    await flushEffects();
    const form = container.querySelector("form");
    if (form === null) throw new Error("Expected the create-project form.");

    act(() => {
      fireEvent.submit(form);
      fireEvent.submit(form);
    });

    const submit = getByRole(container, "button", { name: "Creating project..." });
    expect(api.createProject).toHaveBeenCalledTimes(1);
    expect(submit).toBeDisabled();
    expect(submit).toHaveAttribute("aria-busy", "true");

    await act(async () => {
      created.resolve(project());
      await created.promise;
    });
    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe(
      "/projects/project-1/manuscript",
    );
  });

  it("does not navigate when project creation completes after route exit", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects).mockResolvedValue({ projects: [] });
    const created = deferred<Project>();
    vi.mocked(api.createProject).mockReturnValue(created.promise);

    const { container } = renderLibrary();
    await flushEffects();
    const form = container.querySelector("form");
    if (form === null) throw new Error("Expected the create-project form.");
    act(() => {
      fireEvent.submit(form);
      getByRole(container, "button", { name: "Leave library" }).click();
    });

    await act(async () => {
      created.resolve(project());
      await created.promise;
    });

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/away");
  });

  it("guards logout against duplicate activation", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects).mockResolvedValue({ projects: [] });
    const logout = deferred<void>();
    vi.mocked(api.logout).mockReturnValue(logout.promise);

    const { container } = renderLibrary();
    await flushEffects();
    const command = getByRole(container, "button", { name: "Sign out" });

    act(() => {
      command.click();
      command.click();
    });

    expect(api.logout).toHaveBeenCalledTimes(1);
    expect(command).toBeDisabled();
    expect(command).toHaveAttribute("aria-busy", "true");

    await act(async () => {
      logout.resolve();
      await logout.promise;
    });
    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/");
  });
});
