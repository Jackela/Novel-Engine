import { fireEvent, getByLabelText, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
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

function renderEntry() {
  return harness.mount(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<EntryPage />} />
        <Route path="/projects" element={<p>Project library</p>} />
      </Routes>
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
});

// DR-019 owner-creation safeguards: the single-account install has no email
// recovery, so a typo must be caught client-side (mismatch gate) and the
// DR-008 first-boot token must be sendable from the browser instead of curl.
describe("EntryPage owner-creation safeguards", () => {
  async function renderFirstRun() {
    vi.mocked(api.session).mockRejectedValue(new HttpError("Sign in required.", 401));
    vi.mocked(api.setupStatus).mockResolvedValue({
      owner_configured: false,
      name: "Test Engine",
      version: "test",
    });
    const { container } = renderEntry();
    await flushEffects();
    const form = container.querySelector("form");
    if (form === null) throw new Error("Expected the first-run form.");
    const confirmation = getByLabelText<HTMLInputElement>(container, "Confirm password");
    act(() => {
      fireEvent.change(getByLabelText<HTMLInputElement>(container, "Password"), {
        target: { value: "long-password" },
      });
      fireEvent.change(confirmation, { target: { value: "long-password" } });
    });
    return { container, form, confirmation };
  }

  it("blocks first-run owner creation while the two password entries differ", async () => {
    const { container, form, confirmation } = await renderFirstRun();

    act(() => {
      fireEvent.change(confirmation, { target: { value: "long-password-typo" } });
    });
    await act(async () => {
      fireEvent.submit(form);
      await Promise.resolve();
    });

    expect(api.setupOwner).not.toHaveBeenCalled();
    expect(getByRole(container, "alert").textContent).toContain("Passwords do not match.");

    act(() => {
      fireEvent.change(confirmation, { target: { value: "long-password" } });
    });
    await act(async () => {
      fireEvent.submit(form);
      await Promise.resolve();
    });

    expect(api.setupOwner).toHaveBeenCalledTimes(1);
  });

  it("forwards the optional first-start setup token with the setup request", async () => {
    const { container, form } = await renderFirstRun();

    act(() => {
      fireEvent.change(getByLabelText<HTMLInputElement>(container, "First-start setup token"), {
        target: { value: "boot-token-123" },
      });
    });
    await act(async () => {
      fireEvent.submit(form);
      await Promise.resolve();
    });

    expect(api.setupOwner).toHaveBeenCalledWith("author", "long-password", "boot-token-123");
  });

  it("shows the no-recovery hint on both the setup and the first-login form", async () => {
    const { container } = await renderFirstRun();
    expect(container.textContent).toContain("no email recovery");
    expect(container.textContent).toContain("novel-engine owner reset");

    vi.mocked(api.session).mockRejectedValue(new HttpError("Sign in required.", 401));
    vi.mocked(api.setupStatus).mockResolvedValue({
      owner_configured: true,
      name: "Test Engine",
      version: "test",
    });
    const configured = renderEntry();
    await flushEffects();
    expect(configured.container.textContent).toContain("no email recovery");
    expect(configured.container.textContent).toContain("novel-engine owner reset");
  });

  it("replaces the first-boot setup-token refusal with the actionable hint", async () => {
    const { container, form } = await renderFirstRun();
    vi.mocked(api.setupOwner).mockRejectedValue(
      new HttpError(
        "Setup from a non-loopback address requires the one-time x-setup-token header. Read it " +
          'from the "first-start setup token" line in the server log (or the .setup-token file ' +
          "in the data directory); loopback setup needs no token.",
        403,
        undefined,
        "SETUP_TOKEN_INVALID",
      ),
    );

    await act(async () => {
      fireEvent.submit(form);
      await Promise.resolve();
    });

    const alert = getByRole(container, "alert");
    expect(alert.textContent).toContain("server log");
    expect(alert.textContent).toContain(".setup-token");
    expect(alert.textContent).not.toContain("requires the one-time");
  });
});
