import { afterEach, describe, expect, it, vi } from "vitest";

import { flushEffects } from "@/test/harness";

import {
  entryHarness,
  mockSignedOutInstance,
  PRESERVED_ROUTE,
  renderEntry,
  renderReturnedEntry,
  submitSignIn,
} from "./EntryPage.test-helpers";

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

afterEach(() => {
  entryHarness.cleanup();
  vi.resetAllMocks();
});

describe("EntryPage session-expired return (DR-020)", () => {
  it("explains the forced return when a 401 sent the author back to entry", async () => {
    mockSignedOutInstance();

    const { container } = renderReturnedEntry();
    await flushEffects();

    const notice = container.querySelector(".entry__notice");
    expect(notice?.textContent).toContain("Your session expired");
    expect(notice?.getAttribute("role")).toBe("status");
  });

  it("keeps a voluntary visit to entry free of the session-expired notice", async () => {
    mockSignedOutInstance();

    const { container } = renderEntry();
    await flushEffects();

    expect(container.querySelector(".entry__notice")).toBeNull();
    expect(container.textContent).not.toContain("session expired");
  });

  it("returns to the preserved route with a replace after signing in again", async () => {
    mockSignedOutInstance();

    const { container } = renderReturnedEntry();
    await flushEffects();
    await submitSignIn(container);

    const witness = container.querySelector('[data-testid="location"]');
    expect(witness?.textContent).toBe(PRESERVED_ROUTE);
    expect(witness?.getAttribute("data-navigation")).toBe("REPLACE");
  });

  it("falls back to the project library when no source route was preserved", async () => {
    mockSignedOutInstance();

    const { container } = renderEntry();
    await flushEffects();
    await submitSignIn(container);

    const witness = container.querySelector('[data-testid="location"]');
    expect(witness?.textContent).toBe("/projects");
    expect(witness?.getAttribute("data-navigation")).toBe("REPLACE");
  });

  it("ignores a preserved source that is not an internal route", async () => {
    mockSignedOutInstance();

    const { container } = renderReturnedEntry("//operator.example/session");
    await flushEffects();
    await submitSignIn(container);

    expect(container.querySelector('[data-testid="location"]')?.textContent).toBe("/projects");
  });
});
