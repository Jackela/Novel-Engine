import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const MANIFEST_NAME = "package.json";
const SERVER_PACKAGE_NAME = "novel-engine-server";
const SEARCH_DEPTH = 8;

/**
 * The server package manifest is the single release-version authority since
 * the cutover retired the Python tree: the SSOT gate pins the version there
 * and forbids declaring one in the frontend package, so every derived surface
 * (including the OpenAPI info block) reads it from this file.
 */
export function readWorkspaceVersion(): string {
  const manifestPath = locateWorkspaceManifest();
  const version = JSON.parse(readFileSync(manifestPath, "utf8")).version;
  if (typeof version !== "string" || version.length === 0) {
    throw new Error(`workspace manifest ${manifestPath} does not declare a release version`);
  }
  return version;
}

function locateWorkspaceManifest(): string {
  let directory = dirname(fileURLToPath(import.meta.url));
  for (let depth = 0; depth < SEARCH_DEPTH; depth += 1) {
    const candidate = join(directory, MANIFEST_NAME);
    if (existsSync(candidate)) {
      const name = JSON.parse(readFileSync(candidate, "utf8")).name;
      if (name === SERVER_PACKAGE_NAME) {
        return candidate;
      }
    }
    const parent = dirname(directory);
    if (parent === directory) {
      break;
    }
    directory = parent;
  }
  throw new Error(
    "server package manifest not found above server/src — run the server from the workspace checkout",
  );
}
