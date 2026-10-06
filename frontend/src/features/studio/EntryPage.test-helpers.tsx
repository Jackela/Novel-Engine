import { fireEvent } from "@testing-library/dom";
import { act } from "react";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useNavigationType,
} from "react-router-dom";
import { vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Session } from "@/app/types/studio";
import { createMountHarness } from "@/test/harness";

import { EntryPage } from "./EntryPage";

/** Entry-page fixtures and mounts shared by its lifecycle/session test files. */
export const entryHarness = createMountHarness();

export const ownerSession: Session = {
  session_id: "session-1",
  kind: "owner",
  owner_id: "owner-1",
  expires_at: "2026-10-01T00:00:00Z",
};

export const PRESERVED_ROUTE = "/projects/project-9/manuscript?inspector=history#revision-4";

function LocationWitness() {
  const location = useLocation();
  return (
    <output data-navigation={useNavigationType()} data-testid="location">
      {`${location.pathname}${location.search}${location.hash}`}
    </output>
  );
}

function AwayControl() {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate("/away")} type="button">
      Leave entry
    </button>
  );
}

export function renderEntry() {
  return entryHarness.mount(
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

/** Entry surface of an instance with no session left; the form, not a redirect. */
export function mockSignedOutInstance() {
  vi.mocked(api.session).mockRejectedValue(new HttpError("Sign in required.", 401));
  vi.mocked(api.setupStatus).mockResolvedValue({
    owner_configured: true,
    name: "Test Engine",
    version: "test",
  });
}

/**
 * Entry surface reached by a 401 forced return (DR-020): the router state the
 * protected routes write when they send the author back to sign in again.
 */
export function renderReturnedEntry(from: string = PRESERVED_ROUTE) {
  return entryHarness.mount(
    <MemoryRouter initialEntries={[{ pathname: "/", state: { from, reason: "session-expired" } }]}>
      <Routes>
        <Route path="/" element={<EntryPage />} />
        <Route path="/projects" element={<p>Project library</p>} />
        <Route path="/projects/:projectId/:section?" element={<p>Studio route</p>} />
        <Route path="/away" element={<p>Away route</p>} />
      </Routes>
      <LocationWitness />
    </MemoryRouter>,
  );
}

/** Complete the sign-in form and let the post-login navigation land. */
export async function submitSignIn(container: HTMLElement) {
  vi.mocked(api.login).mockResolvedValue(ownerSession);
  const form = container.querySelector("form");
  const password = container.querySelector<HTMLInputElement>('input[type="password"]');
  if (form === null || password === null) throw new Error("Expected the sign-in form.");
  act(() => {
    fireEvent.change(password, { target: { value: "long-password" } });
  });
  await act(async () => {
    fireEvent.submit(form);
    await Promise.resolve();
    await Promise.resolve();
  });
}
