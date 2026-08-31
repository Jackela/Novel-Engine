import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const MANIFEST_NAME = "package.json";
const SERVER_PACKAGE_NAME = "novel-engine-server";
const SEARCH_DEPTH = 8;
const SEMVER_PATTERN =
  /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/;

export interface ProductIdentity {
  readonly name: string;
  readonly version: string;
}

/**
 * The server package manifest is the single release-version authority since
 * the cutover retired the Python tree: the SSOT gate pins the version there
 * and forbids declaring one in the frontend package, so every derived surface
 * (including the OpenAPI info block) reads it from this file.
 */
export function readProductIdentity(manifestPath = locateWorkspaceManifest()): ProductIdentity {
  const manifest: unknown = JSON.parse(readFileSync(manifestPath, "utf8"));
  if (manifest === null || typeof manifest !== "object" || Array.isArray(manifest)) {
    throw new Error(`workspace manifest ${manifestPath} must decode to an object`);
  }
  const record = manifest as Record<string, unknown>;
  if (record.name !== SERVER_PACKAGE_NAME) {
    throw new Error(`workspace manifest ${manifestPath} must be named ${SERVER_PACKAGE_NAME}`);
  }
  if (
    typeof record.productName !== "string" ||
    record.productName.trim().length === 0 ||
    record.productName !== record.productName.trim()
  ) {
    throw new Error(`workspace manifest ${manifestPath} does not declare a product name`);
  }
  if (typeof record.version !== "string" || record.version.trim().length === 0) {
    throw new Error(`workspace manifest ${manifestPath} does not declare a release version`);
  }
  if (!SEMVER_PATTERN.test(record.version)) {
    throw new Error(`workspace manifest ${manifestPath} must declare a valid SemVer release`);
  }
  return { name: record.productName, version: record.version };
}

/** Compatibility projection for callers that only render the release version. */
export function readWorkspaceVersion(): string {
  return readProductIdentity().version;
}

function locateWorkspaceManifest(): string {
  let directory = dirname(fileURLToPath(import.meta.url));
  for (let depth = 0; depth < SEARCH_DEPTH; depth += 1) {
    const candidate = join(directory, MANIFEST_NAME);
    if (existsSync(candidate)) {
      let name: unknown;
      try {
        name = JSON.parse(readFileSync(candidate, "utf8")).name;
      } catch {
        name = undefined;
      }
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
