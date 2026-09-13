import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { createMountHarness } from "@/test/harness";

import { EntryPage } from "./EntryPage";
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

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function neverSettles<T>(): Promise<T> {
  return new Promise(() => undefined);
}

describe("Studio product brand", () => {
  it("renders the injected product name on entry and project-library surfaces", () => {
    vi.mocked(api.session).mockReturnValue(neverSettles());
    vi.mocked(api.projects).mockReturnValue(neverSettles());

    const entry = harness.mount(
      <MemoryRouter>
        <EntryPage />
      </MemoryRouter>,
    ).container;
    const library = harness.mount(
      <MemoryRouter>
        <ProjectLibraryPage />
      </MemoryRouter>,
    ).container;

    expect(entry.querySelector(".entry__brand")?.textContent).toContain("Test Engine");
    expect(entry.querySelector("footer")?.textContent).toBe("Test Engine test");
    expect(library.querySelector(".ui-brand")?.textContent).toContain("Test Engine");
  });
});
