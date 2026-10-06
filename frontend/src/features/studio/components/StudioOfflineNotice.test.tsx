import { getByRole, queryByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { setActiveLanguage } from "@/app/i18n/language";
import { createMountHarness } from "@/test/harness";

import { StudioOfflineNotice } from "./StudioOfflineNotice";

const harness = createMountHarness();

function setConnectivity(online: boolean): void {
  Object.defineProperty(window.navigator, "onLine", { configurable: true, value: online });
  act(() => {
    window.dispatchEvent(new Event(online ? "online" : "offline"));
  });
}

afterEach(() => {
  setConnectivity(true);
  harness.cleanup();
});

describe("StudioOfflineNotice (DR-046)", () => {
  it("renders no notice while the browser reports online", () => {
    setConnectivity(true);
    const { container } = harness.mount(<StudioOfflineNotice />);

    expect(container).toBeEmptyDOMElement();
  });

  it("shows the offline notice on the offline event and clears it on recovery", () => {
    setConnectivity(true);
    const { container } = harness.mount(<StudioOfflineNotice />);

    setConnectivity(false);
    expect(getByRole(container, "status")).toHaveTextContent(
      "You are offline. Changes will not be saved until the connection returns.",
    );

    setConnectivity(true);
    expect(queryByRole(container, "status")).toBeNull();
  });

  it("renders the notice in Chinese under the zh language", () => {
    setActiveLanguage("zh");
    setConnectivity(false);
    const { container } = harness.mount(<StudioOfflineNotice />);

    expect(getByRole(container, "status")).toHaveTextContent(
      "当前处于离线状态。连接恢复前，更改不会被保存。",
    );
  });
});
