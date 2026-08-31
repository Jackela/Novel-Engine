import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { readProductIdentity } from "../../src/shared/infrastructure/workspace_manifest.js";

const temporaryDirectories: string[] = [];

function manifestPath(manifest: unknown): string {
  const directory = mkdtempSync(join(tmpdir(), "novel-engine-product-identity-"));
  temporaryDirectories.push(directory);
  const path = join(directory, "package.json");
  writeFileSync(path, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  return path;
}

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true });
  }
});

describe("workspace product identity", () => {
  it("reads the product name and a SemVer release from one manifest", () => {
    const path = manifestPath({
      name: "novel-engine-server",
      productName: "Novel Engine",
      version: "1.2.3-beta.1+build.7",
    });

    expect(readProductIdentity(path)).toEqual({
      name: "Novel Engine",
      version: "1.2.3-beta.1+build.7",
    });
  });

  it.each([
    {
      label: "wrong package",
      manifest: { name: "other-server", productName: "Novel Engine", version: "1.2.3" },
      message: /must be named novel-engine-server/,
    },
    {
      label: "missing product name",
      manifest: { name: "novel-engine-server", version: "1.2.3" },
      message: /product name/,
    },
    {
      label: "blank product name",
      manifest: { name: "novel-engine-server", productName: "   ", version: "1.2.3" },
      message: /product name/,
    },
    {
      label: "missing release version",
      manifest: { name: "novel-engine-server", productName: "Novel Engine" },
      message: /release version/,
    },
    {
      label: "blank release version",
      manifest: { name: "novel-engine-server", productName: "Novel Engine", version: "   " },
      message: /release version/,
    },
    {
      label: "non-SemVer release",
      manifest: {
        name: "novel-engine-server",
        productName: "Novel Engine",
        version: "01.2.3",
      },
      message: /valid SemVer/,
    },
    {
      label: "numeric prerelease identifier with a leading zero",
      manifest: {
        name: "novel-engine-server",
        productName: "Novel Engine",
        version: "1.2.3-01",
      },
      message: /valid SemVer/,
    },
  ])("fails closed for a $label", ({ manifest, message }) => {
    expect(() => readProductIdentity(manifestPath(manifest))).toThrow(message);
  });
});
