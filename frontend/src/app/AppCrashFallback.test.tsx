import { getByRole, getByText, queryByText } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { setActiveLanguage } from "@/app/i18n/language";
import { createMountHarness } from "@/test/harness";

import { AppCrashFallback } from "./AppCrashFallback";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

describe("AppCrashFallback (DR-046)", () => {
  it("shows the readable crash copy with the raw detail kept visible", () => {
    const { container } = harness.mount(<AppCrashFallback detail="boom" />);

    expect(getByRole(container, "heading")).toHaveTextContent("Something went wrong");
    expect(container).toHaveTextContent(
      "The application encountered an unexpected error. Please refresh the page to try again.",
    );
    expect(getByText(container, "boom")).toBeInTheDocument();
  });

  it("hides the detail row when the boundary has no message", () => {
    const { container } = harness.mount(<AppCrashFallback detail={null} />);

    expect(getByRole(container, "heading")).toBeInTheDocument();
    expect(queryByText(container, "boom")).toBeNull();
  });

  it("re-renders the copy in the switched language", () => {
    const { container } = harness.mount(<AppCrashFallback detail={null} />);

    act(() => {
      setActiveLanguage("zh");
    });

    expect(getByRole(container, "heading")).toHaveTextContent("出了点问题");
    expect(container).toHaveTextContent("应用遇到了意外错误，请刷新页面重试。");
  });
});
