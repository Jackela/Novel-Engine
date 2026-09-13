import { describe, expect, it } from "vitest";

import { productIdentity, productLabel } from "./productIdentity";

describe("product identity", () => {
  it("exposes the build-injected product name and version as one immutable value", () => {
    expect(productIdentity).toEqual({ name: "Test Engine", version: "test" });
    expect(productLabel).toBe("Test Engine test");
    expect(Object.isFrozen(productIdentity)).toBe(true);
  });
});
