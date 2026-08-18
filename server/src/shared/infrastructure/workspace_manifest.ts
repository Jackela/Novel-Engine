import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const VERSION_PATTERN = /^\s*version\s*=\s*"([^"]+)"\s*$/;
const MANIFEST_NAME = "pyproject.toml";
const SEARCH_DEPTH = 8;

/**
 * The workspace manifest is the single release-version authority until the
 * rewrite cutover: the SSOT gate pins the version there and forbids declaring
 * one in server/package.json, so every derived surface (including the
 * OpenAPI info block) reads it from this file.
 */
export function readWorkspaceVersion(): string {
  const manifestPath = locateWorkspaceManifest();
  const lines = readFileSync(manifestPath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const match = line.match(VERSION_PATTERN);
    if (match?.[1]) {
      return match[1];
    }
  }
  throw new Error(`workspace manifest ${manifestPath} does not declare a release version`);
}

function locateWorkspaceManifest(): string {
  let directory = dirname(fileURLToPath(import.meta.url));
  for (let depth = 0; depth < SEARCH_DEPTH; depth += 1) {
    const candidate = join(directory, MANIFEST_NAME);
    if (existsSync(candidate)) {
      return candidate;
    }
    const parent = dirname(directory);
    if (parent === directory) {
      break;
    }
    directory = parent;
  }
  throw new Error(
    `${MANIFEST_NAME} not found above server/src — run the server from the workspace checkout`,
  );
}
