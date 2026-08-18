import { spawnSync } from "node:child_process";
import { describe, expect, it } from "vitest";

const scriptPath = new URL("../../scripts/qa/python_freeze_check.mjs", import.meta.url).pathname;

function runScript(args: string[]) {
  return spawnSync("node", [scriptPath, ...args], { encoding: "utf8" });
}

describe("python_freeze_check --paths mode", () => {
  it("flags the frozen Python trees and manifests", () => {
    const result = runScript([
      "--paths",
      "src/apps/api/main.py",
      "tests/test_api.py",
      "alembic/versions/0001.py",
      "scripts/qa/check_ssot.py",
      "pyproject.toml",
      "uv.lock",
    ]);
    expect(result.status).toBe(1);
    const output = `${result.stdout}\n${result.stderr}`;
    for (const frozenPath of [
      "src/apps/api/main.py",
      "tests/test_api.py",
      "alembic/versions/0001.py",
      "scripts/qa/check_ssot.py",
      "pyproject.toml",
      "uv.lock",
    ]) {
      expect(output).toContain(frozenPath);
    }
  });

  it("passes TypeScript workspace and documentation paths", () => {
    const result = runScript([
      "--paths",
      "server/src/apps/api/app.ts",
      "server/scripts/qa/check_ssot.mjs",
      "docs/agents/ci-gates.md",
      ".github/workflows/ci.yml",
      "pnpm-workspace.yaml",
      "pnpm-lock.yaml",
      "frontend/src/app/api.ts",
    ]);
    expect(result.status).toBe(0);
    expect(result.stdout).toContain("[python-freeze] clean");
  });
});

describe("python_freeze_check argument modes", () => {
  it("accepts --base-ref and --head-ref mode against real git refs", () => {
    const result = runScript(["--base-ref", "HEAD", "--head-ref", "HEAD"]);
    expect(result.status).toBe(0);
    expect(result.stdout).toContain("[python-freeze] clean");
  });

  it("rejects a missing mode", () => {
    const result = runScript([]);
    expect(result.status).not.toBe(0);
    expect(result.stderr).toContain("pass either --base-ref and --head-ref, or --paths");
  });
});
