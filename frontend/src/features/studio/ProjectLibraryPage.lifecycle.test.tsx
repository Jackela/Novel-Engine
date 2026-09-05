import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { ProjectsPage } from "@/app/projectShellContract";
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

describe("ProjectLibraryPage request lifecycle", () => {
  it("keeps an operational project-list failure on the library with Retry", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects).mockRejectedValue(new HttpError("Projects unavailable.", 503));

    const { container } = renderLibrary();
    await flushEffects();

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/projects");
    expect(getByRole(container, "alert").textContent).toContain("Projects unavailable.");
    expect(getByRole(container, "button", { name: "Try again" })).toBeEnabled();
  });

  it("does not request projects when the session probe is unauthenticated", async () => {
    vi.mocked(api.session).mockRejectedValue(new HttpError("Sign in required.", 401));

    const { container } = renderLibrary();
    await flushEffects();

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/");
    expect(api.projects).not.toHaveBeenCalled();
  });

  it("retries one complete bootstrap and replaces the stale error", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects)
      .mockRejectedValueOnce(new HttpError("Projects unavailable.", 503))
      .mockResolvedValueOnce({
        projects: [project({ title: "Recovered draft" })],
        next_cursor: null,
      });

    const { container } = renderLibrary();
    await flushEffects();
    const retry = getByRole(container, "button", { name: "Try again" });
    retry.focus();

    await act(async () => {
      retry.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(api.session).toHaveBeenCalledTimes(2);
    expect(api.projects).toHaveBeenCalledTimes(2);
    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(getByRole(container, "button", { name: /Recovered draft/ })).toBeEnabled();
    expect(document.activeElement).toBe(getByRole(container, "heading", { name: "Projects" }));
  });

  it("reuses one in-flight Retry request across duplicate activation", async () => {
    const retrySession = deferred<Session>();
    vi.mocked(api.session)
      .mockResolvedValueOnce(ownerSession)
      .mockReturnValueOnce(retrySession.promise);
    vi.mocked(api.projects)
      .mockRejectedValueOnce(new HttpError("Projects unavailable.", 503))
      .mockResolvedValueOnce({ projects: [], next_cursor: null });

    const { container } = renderLibrary();
    await flushEffects();
    const retry = getByRole(container, "button", { name: "Try again" });

    act(() => {
      retry.click();
      retry.click();
    });

    expect(api.session).toHaveBeenCalledTimes(2);
    await act(async () => {
      retrySession.resolve(ownerSession);
      await retrySession.promise;
      await Promise.resolve();
    });
    expect(api.projects).toHaveBeenCalledTimes(2);
  });

  it("restores Retry focus after failure but preserves deliberate focus movement", async () => {
    const retryFailure = rejectableDeferred<ProjectsPage>();
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects)
      .mockRejectedValueOnce(new HttpError("Projects unavailable.", 503))
      .mockReturnValueOnce(retryFailure.promise)
      .mockRejectedValueOnce(new HttpError("Still unavailable.", 503));

    const { container } = renderLibrary();
    await flushEffects();
    const retry = getByRole(container, "button", { name: "Try again" });
    retry.focus();
    act(() => retry.click());

    await act(async () => {
      retryFailure.reject(new HttpError("Still unavailable.", 503));
      await retryFailure.promise.catch(() => undefined);
    });
    expect(document.activeElement).toBe(retry);

    const secondRetry = getByRole(container, "button", { name: "Try again" });
    const away = getByRole(container, "button", { name: "Leave library" });
    secondRetry.focus();
    await act(async () => {
      secondRetry.click();
      away.focus();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(document.activeElement).toBe(away);
  });

  it("aborts a project-list read when the library unmounts", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    vi.mocked(api.projects).mockReturnValue(deferred<ProjectsPage>().promise);

    const mounted = renderLibrary();
    await flushEffects();
    const signal = vi.mocked(api.projects).mock.calls[0]?.[0]?.signal;
    expect(signal).toBeInstanceOf(AbortSignal);

    harness.unmount(mounted.container);

    expect(signal?.aborted).toBe(true);
  });

  it("does not publish a stale project list after route exit", async () => {
    vi.mocked(api.session).mockResolvedValue(ownerSession);
    const projects = deferred<ProjectsPage>();
    vi.mocked(api.projects).mockReturnValue(projects.promise);

    const { container } = renderLibrary();
    await flushEffects();
    act(() => {
      getByRole(container, "button", { name: "Leave library" }).click();
    });

    await act(async () => {
      projects.resolve({ projects: [project({ title: "Stale draft" })], next_cursor: null });
      await projects.promise;
    });

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/away");
    expect(container.textContent).not.toContain("Stale draft");
  });

  it("does not navigate when a late session failure arrives after route exit", async () => {
    const session = rejectableDeferred<Session>();
    vi.mocked(api.session).mockReturnValue(session.promise);

    const { container } = renderLibrary();
    act(() => {
      getByRole(container, "button", { name: "Leave library" }).click();
    });

    await act(async () => {
      session.reject(new HttpError("Sign in required.", 401));
      await session.promise.catch(() => undefined);
    });

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/away");
  });
});
