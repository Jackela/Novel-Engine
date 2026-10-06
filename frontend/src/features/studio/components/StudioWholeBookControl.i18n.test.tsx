import { getByRole, getByText } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LANGUAGE_STORAGE_KEY } from "@/app/i18n/language";
import { createMountHarness } from "@/test/harness";
import type { WholeBookPhase } from "../hooks/useWholeBookLoop";

import { StudioWholeBookControl } from "./StudioWholeBookControl";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  window.localStorage.clear();
});

function render(phase: WholeBookPhase, remaining = 3): HTMLDivElement {
  return harness.mount(
    <StudioWholeBookControl
      phase={phase}
      remaining={remaining}
      onStart={vi.fn()}
      onStop={vi.fn()}
    />,
  ).container;
}

/**
 * Bilingual contract for the whole-book surface: the interpolated
 * templates (progress, outcomes, failure) must render natural sentences in
 * both languages — the EN forms double as the e2e locators, so their
 * substitution output stays byte-identical to the pre-i18n literals.
 */
describe("StudioWholeBookControl bilingual rendering", () => {
  it("renders EN progress and outcomes byte-identically", () => {
    const running = render({ kind: "running", current: 1, total: 2 });
    expect(running.querySelector('[role="status"]')?.textContent).toBe(
      "Generating chapter 1 of 2…",
    );
    expect(getByRole(running, "button", { name: "Stop generating" })).toBeVisible();

    const stopped = render({ kind: "done", generated: 1, stoppedEarly: true });
    expect(stopped.querySelector(".whole-book__outcome")?.textContent).toBe(
      "Stopped — 1 chapter accepted this run.",
    );

    const completed = render({ kind: "done", generated: 2, stoppedEarly: false });
    expect(completed.querySelector(".whole-book__outcome")?.textContent).toBe(
      "Completed — 2 chapters accepted.",
    );
  });

  it("renders the zh surface with localized interpolation when stored", () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");

    const running = render({ kind: "running", current: 1, total: 2 });
    expect(running.querySelector('[role="status"]')?.textContent).toBe("正在生成第 1 章，共 2 章…");
    expect(getByRole(running, "button", { name: "停止生成" })).toBeVisible();

    const completed = render({ kind: "done", generated: 2, stoppedEarly: false });
    expect(completed.querySelector(".whole-book__outcome")?.textContent).toBe(
      "已完成 — 接受了 2 章。",
    );

    const failed = render({
      kind: "failed",
      generated: 1,
      failedChapterTitle: "风暴夜",
      message: "provider 掉线",
    });
    expect(getByRole(failed, "alert").textContent).toBe(
      "在“风暴夜”上失败，此前已接受 1 章：provider 掉线",
    );
  });

  it("renders the zh replacement confirmation with natural counts", () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");
    const mounted = harness.mount(
      <StudioWholeBookControl
        occupiedChapters={[
          { id: "hand", title: "手写开篇", requiresConfirmation: true },
          { id: "imported", title: "导入章节", requiresConfirmation: true },
        ]}
        onConfirmReplace={vi.fn()}
        onStart={vi.fn()}
        onStop={vi.fn()}
        phase={{ kind: "idle" }}
        remaining={3}
        safeCount={1}
      />,
    );

    act(() => getByRole(mounted.container, "button", { name: "生成整本书" }).click());

    expect(
      getByText(
        mounted.container,
        "整本生成会自动接受生成的草稿。以下章节的现有正文不是已接受的 AI 修订：",
      ),
    ).toBeVisible();
    expect(getByRole(mounted.container, "list", { name: "将被替换的章节" }).textContent).toBe(
      "手写开篇导入章节",
    );
    expect(getByRole(mounted.container, "button", { name: "只生成 1 个空白章节" })).toBeVisible();
    expect(getByRole(mounted.container, "button", { name: "用 AI 草稿替换这 2 章" })).toBeVisible();
    expect(getByRole(mounted.container, "button", { name: "取消" })).toBeVisible();
  });
});
