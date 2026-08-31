import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { UserConfig } from "vite";
import { describe, expect, it } from "vitest";

import buildConfig, { injectProductIdentityHtml } from "../../vite.config";

const productManifest = JSON.parse(
  readFileSync(resolve(process.cwd(), "../server/package.json"), "utf8"),
) as { productName: string; version: string };

describe("production product identity injection", () => {
  it("projects the server manifest identity through one compile-time value", () => {
    const config = buildConfig as UserConfig;

    expect(config.define).toEqual({
      __PRODUCT_IDENTITY__: JSON.stringify({
        name: productManifest.productName,
        version: productManifest.version,
      }),
    });
  });

  it("binds the production HTML title and description to the same identity", () => {
    const template =
      '<title>__PRODUCT_NAME__</title><meta name="description" content="__PRODUCT_NAME__ writes">';

    expect(injectProductIdentityHtml(template, productManifest.productName)).toBe(
      `<title>${productManifest.productName}</title><meta name="description" content="${productManifest.productName} writes">`,
    );
    expect(() =>
      injectProductIdentityHtml("<title>Independent literal</title>", "Novel Engine"),
    ).toThrow("product-name token");
  });
});
