import { describe, expect, it } from "vitest";

import { setActiveLanguage } from "@/app/i18n/language";
import { productIdentity } from "@/app/productIdentity";

import { localServiceUnavailable } from "./networkError";

/**
 * DR-046: the shared browser-transport boundary resolves its copy through
 * the dictionaries at failure time, so the same failure reads differently
 * under each language. The EN value is byte-identical to the pre-i18n
 * literal (the api/proposalStream suites pin it through their assertions).
 */
describe("localServiceUnavailable (DR-046)", () => {
  it("names the product in the English default", () => {
    const error = localServiceUnavailable(new TypeError("fetch failed"));

    expect(error.message).toBe(
      `${productIdentity.name} is unavailable. Check the local service and retry.`,
    );
    expect(error.cause).toBeInstanceOf(TypeError);
  });

  it("follows the active language after a switch", () => {
    setActiveLanguage("zh");

    const error = localServiceUnavailable(new TypeError("fetch failed"));

    expect(error.message).toBe(`${productIdentity.name} 不可用。请检查本地服务后重试。`);
  });
});
