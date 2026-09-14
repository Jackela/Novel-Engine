import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import { LANGUAGE_STORAGE_KEY } from "@/app/i18n/language";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

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
  window.localStorage.clear();
});

/** Entry surface of an already-configured instance (form state, no redirect). */
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

async function renderConfiguredEntry() {
  vi.mocked(api.session).mockRejectedValue(new HttpError("Unauthorized", 401));
  vi.mocked(api.setupStatus).mockResolvedValue({
    owner_configured: true,
    name: "Test Engine",
    version: "test",
  });
  const { container } = renderEntry();
  await flushEffects();
  return container;
}

describe("EntryPage bilingual rendering", () => {
  it("renders the English surface by default under an en-US browser", async () => {
    const container = await renderConfiguredEntry();

    expect(getByRole(container, "heading", { name: "Open your writing studio" })).toBeVisible();
    expect(container.textContent).toContain("No API key?");
    expect(getByRole(container, "button", { name: "Sign in" })).toBeEnabled();
    expect(getByRole(container, "radio", { name: "English" })).toBeChecked();
  });

  it("renders the zh surface when a stored zh choice exists", async () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");

    const container = await renderConfiguredEntry();

    expect(getByRole(container, "heading", { name: "打开你的写作工作室" })).toBeVisible();
    expect(container.textContent).toContain("没有 API key？");
    expect(getByRole(container, "button", { name: "登录" })).toBeEnabled();
    expect(getByRole(container, "radio", { name: "中文" })).toBeChecked();
  });

  it("switches the live surface to zh and persists the choice", async () => {
    const container = await renderConfiguredEntry();

    act(() => {
      fireEvent.click(getByRole(container, "radio", { name: "中文" }));
    });

    expect(getByRole(container, "heading", { name: "打开你的写作工作室" })).toBeVisible();
    expect(getByRole(container, "button", { name: "登录" })).toBeEnabled();
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("zh");

    act(() => {
      fireEvent.click(getByRole(container, "radio", { name: "English" }));
    });

    expect(getByRole(container, "heading", { name: "Open your writing studio" })).toBeVisible();
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe("en");
  });

  it("localizes the transient states", async () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");
    vi.mocked(api.session).mockReturnValue(deferred<never>().promise);

    const { container } = renderEntry();

    expect(container.querySelector('.entry__state[role="status"]')?.textContent).toContain(
      "正在检查你的会话",
    );
  });
});
