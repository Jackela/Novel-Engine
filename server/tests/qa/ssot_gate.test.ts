import { spawnSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it } from "vitest";

const CHECK_SSOT = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "../../scripts/qa/check_ssot.mjs",
);
const fixtures: string[] = [];

async function writeFixtureFile(root: string, path: string, value: string): Promise<void> {
  const target = join(root, path);
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, value, "utf8");
}

async function createFixture(version = "1.2.3"): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "novel-engine-ssot-"));
  fixtures.push(root);
  const files: Record<string, string> = {
    "package.json": JSON.stringify({ name: "novel-engine-tooling", private: true }),
    "frontend/package.json": JSON.stringify({ name: "novel-engine-studio", private: true }),
    "tools/api-types/package.json": JSON.stringify({
      name: "@novel-engine/api-types-toolchain",
      private: true,
    }),
    "server/package.json": JSON.stringify({
      name: "novel-engine-server",
      productName: "Novel Engine",
      version,
      private: true,
    }),
    "README.md": `# Novel Engine\n\nNovel Engine \`${version}\` is self-hosted.\n`,
    "CHANGELOG.md": `# Changelog\n\n## ${version}\n`,
    "AGENTS.md": "# Novel Engine\n\nNovel Engine is a self-hosted writing studio.\n",
    "openwiki/quickstart.md": "# Novel Engine quickstart\n\nNovel Engine is self-hosted.\n",
    "frontend/src/brand.ts": 'export const visibleBrand = "Novel Engine";\n',
    "server/qa-baselines/openapi.current.json": JSON.stringify({
      info: { title: "Novel Engine API", version },
    }),
    "openspec/specs/novel-engine/spec.md": "### Requirement: Product authority\n",
    ".agents/skills/openspec-change/SKILL.md": "Canonical: openspec/specs/novel-engine/spec.md\n",
  };
  await Promise.all(
    Object.entries(files).map(([path, value]) => writeFixtureFile(root, path, value)),
  );
  const init = spawnSync("git", ["init", "--quiet"], { cwd: root, encoding: "utf8" });
  if (init.status !== 0) throw new Error(init.stderr);
  const add = spawnSync("git", ["add", "."], { cwd: root, encoding: "utf8" });
  if (add.status !== 0) throw new Error(add.stderr);
  return root;
}

function runGate(root: string) {
  return spawnSync(process.execPath, [CHECK_SSOT, root], { cwd: root, encoding: "utf8" });
}

afterEach(async () => {
  await Promise.all(fixtures.splice(0).map((root) => rm(root, { recursive: true, force: true })));
});

describe("product identity SSOT gate", () => {
  it("rejects adversarial prerelease identifiers without unbounded backtracking", async () => {
    const root = await createFixture(`0.0.0-0.${"--.".repeat(1000)}!`);
    const result = spawnSync(process.execPath, [CHECK_SSOT, root], {
      cwd: root,
      encoding: "utf8",
      timeout: 2000,
    });
    expect(result.error).toBeUndefined();
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("valid SemVer");
  });

  it.each(["7.8.9-rc.1+build.4", "1.2.3-0.01a.--+build.007"])(
    "accepts aligned SemVer %s without a release literal in the gate",
    async (version) => {
      const root = await createFixture(version);

      const result = runGate(root);

      expect(result.status, result.stderr).toBe(0);
      expect(result.stdout).toContain(`Novel Engine ${version} is aligned`);
    },
  );

  it.each(["", "1.2", "v1.2.3", "01.2.3", "1.2.3-01", " 1.2.3 "])(
    "rejects malformed manifest version %j",
    async (version) => {
      const root = await createFixture(version);

      const result = runGate(root);

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("valid SemVer");
    },
  );

  it("rejects a blank product name", async () => {
    const root = await createFixture();
    await writeFixtureFile(
      root,
      "server/package.json",
      JSON.stringify({ name: "novel-engine-server", productName: "  ", version: "1.2.3" }),
    );

    const result = runGate(root);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("non-blank productName");
  });

  it("rejects surrounding product-name whitespace", async () => {
    const root = await createFixture();
    await writeFixtureFile(
      root,
      "server/package.json",
      JSON.stringify({
        name: "novel-engine-server",
        productName: " Novel Engine ",
        version: "1.2.3",
      }),
    );

    const result = runGate(root);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("productName must not contain surrounding whitespace");
  });

  it.each(["package.json", "frontend/package.json", "tools/api-types/package.json"])(
    "rejects a duplicate version authority in %s",
    async (path) => {
      const root = await createFixture();
      const target = join(root, path);
      const original = JSON.parse(await readFile(target, "utf8"));
      await writeFixtureFile(root, path, JSON.stringify({ ...original, version: "1.2.3" }));

      const result = runGate(root);

      expect(result.status).toBe(1);
      expect(result.stderr).toContain(`${path} must not define version or productName`);
    },
  );

  it.each([
    ["README.md", "# Novel Engine\n\nNovel Engine `9.9.9` is self-hosted.\n", "README.md"],
    ["CHANGELOG.md", "# Changelog\n\n## 9.9.9\n", "CHANGELOG.md"],
    [
      "server/qa-baselines/openapi.current.json",
      JSON.stringify({ info: { title: "Novel Engine API", version: "9.9.9" } }),
      "OpenAPI",
    ],
  ])("rejects stale current projection in %s", async (path, value, expected) => {
    const root = await createFixture();
    await writeFixtureFile(root, path, value);

    const result = runGate(root);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain(expected);
  });

  it("rejects retired visible and capability identities", async () => {
    const root = await createFixture();
    await writeFixtureFile(root, "frontend/src/brand.ts", 'export const brand = "Novel Studio";\n');
    await writeFixtureFile(
      root,
      ".agents/skills/openspec-change/SKILL.md",
      "Canonical: openspec/specs/novel-studio/spec.md\n",
    );

    const result = runGate(root);

    expect(result.status).toBe(1);
    expect(result.stderr).toContain("retired product identity");
    expect(result.stderr).toContain("retired OpenSpec capability reference");
  });

  it.each(["AGENTS.md", "openwiki/quickstart.md"])(
    "rejects a release number in the current declaration of %s",
    async (path) => {
      const root = await createFixture();
      await writeFixtureFile(
        root,
        path,
        `# Novel Engine\n\nNovel Engine 0.4.0 is a self-hosted writing studio.\n`,
      );

      const result = runGate(root);

      expect(result.status).toBe(1);
      expect(result.stderr).toContain("current product declaration must be versionless");
    },
  );
});
