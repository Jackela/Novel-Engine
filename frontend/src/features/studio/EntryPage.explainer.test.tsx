import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Session } from "@/app/types/studio";
import { createMountHarness, deferred } from "@/test/harness";

import { EntryPage } from "./EntryPage";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      session: vi.fn<typeof actual.api.session>(),
      setupStatus: vi.fn<typeof actual.api.setupStatus>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

// The first-run explainer: the entry panel tells first-time authors what the
// instance is (local-first), how generation starts without a key, and where
// to connect a real provider later.
describe("EntryPage first-run explainer", () => {
  it("offers a conditional trial hint and names Settings as the provider escape hatch", () => {
    vi.mocked(api.session).mockReturnValue(deferred<Session>().promise);

    const { container } = harness.mount(
      <MemoryRouter>
        <EntryPage />
      </MemoryRouter>,
    );
    const panel = container.querySelector(".entry__panel")?.textContent ?? "";

    expect(panel).toContain("stay in this self-hosted instance");
    expect(panel).toContain("No API key?");
    expect(panel).toContain("built-in trial provider");
    expect(panel).toContain("a project's Settings");
  });
});
