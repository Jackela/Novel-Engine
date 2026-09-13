import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Session } from "@/app/types/studio";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { EntryPage } from "./EntryPage";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      login: vi.fn<typeof actual.api.login>(),
      session: vi.fn<typeof actual.api.session>(),
      setupOwner: vi.fn<typeof actual.api.setupOwner>(),
      setupStatus: vi.fn<typeof actual.api.setupStatus>(),
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

function LocationWitness() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}

function AwayControl() {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate("/away")} type="button">
      Leave entry
    </button>
  );
}

function renderEntry() {
  return harness.mount(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<EntryPage />} />
        <Route path="/projects" element={<p>Project library</p>} />
        <Route path="/away" element={<p>Away route</p>} />
      </Routes>
      <AwayControl />
      <LocationWitness />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(api.setupStatus).mockReturnValue(
    deferred<{ owner_configured: boolean; name: string; version: string }>().promise,
  );
});

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
  delete document.documentElement.dataset.theme;
});

// Unmount and stale-response guards: in-flight entry requests must abort on
// unmount, and resolved responses must never act after the route was left.
describe("EntryPage unmount and stale-response guards", () => {
  it("aborts the session probe when the entry surface unmounts", () => {
    vi.mocked(api.session).mockReturnValue(deferred<Session>().promise);

    const mounted = renderEntry();
    const signal = vi.mocked(api.session).mock.calls[0]?.[0]?.signal;
    expect(signal).toBeInstanceOf(AbortSignal);

    harness.unmount(mounted.container);

    expect(signal?.aborted).toBe(true);
  });

  it("does not navigate when a stale session probe completes after route exit", async () => {
    const session = deferred<Session>();
    vi.mocked(api.session).mockReturnValue(session.promise);

    const { container } = renderEntry();
    act(() => {
      getByRole(container, "button", { name: "Leave entry" }).click();
    });

    await act(async () => {
      session.resolve(ownerSession);
      await session.promise;
    });

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/away");
  });

  it("aborts the setup-status read when the entry surface unmounts", async () => {
    vi.mocked(api.session).mockRejectedValue(new HttpError("Sign in required.", 401));
    vi.mocked(api.setupStatus).mockReturnValue(
      deferred<{ owner_configured: boolean; name: string; version: string }>().promise,
    );

    const mounted = renderEntry();
    await flushEffects();
    const signal = vi.mocked(api.setupStatus).mock.calls[0]?.[0]?.signal;
    expect(signal).toBeInstanceOf(AbortSignal);

    harness.unmount(mounted.container);

    expect(signal?.aborted).toBe(true);
  });

  it("does not publish a setup-status result after route exit", async () => {
    vi.mocked(api.session).mockRejectedValue(new HttpError("Sign in required.", 401));
    const setup = deferred<{ owner_configured: boolean; name: string; version: string }>();
    vi.mocked(api.setupStatus).mockReturnValue(setup.promise);

    const { container } = renderEntry();
    await flushEffects();
    act(() => {
      getByRole(container, "button", { name: "Leave entry" }).click();
    });

    await act(async () => {
      setup.resolve({ owner_configured: true, name: "Test Engine", version: "test" });
      await setup.promise;
    });

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/away");
    expect(container.querySelector("form")).toBeNull();
  });

  it("does not navigate when login completes after the entry route was left", async () => {
    vi.mocked(api.session).mockRejectedValue(new HttpError("Sign in required.", 401));
    vi.mocked(api.setupStatus).mockResolvedValue({
      owner_configured: true,
      name: "Test Engine",
      version: "test",
    });
    const login = deferred<Session>();
    vi.mocked(api.login).mockReturnValue(login.promise);

    const { container } = renderEntry();
    await flushEffects();
    const form = container.querySelector("form");
    const password = container.querySelector<HTMLInputElement>('input[type="password"]');
    if (form === null || password === null) throw new Error("Expected the login form.");
    act(() => {
      fireEvent.change(password, { target: { value: "long-password" } });
      fireEvent.submit(form);
      getByRole(container, "button", { name: "Leave entry" }).click();
    });

    await act(async () => {
      login.resolve(ownerSession);
      await login.promise;
    });

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/away");
  });
});
