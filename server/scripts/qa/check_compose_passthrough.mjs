import { existsSync } from "node:fs";
import { join } from "node:path";

import { readTextLines, repoRoot, reportFailures } from "./common.mjs";

/**
 * Compose passthrough drift gate (#626): every compose file that runs the
 * server promises that its `environment:` block mirrors the provider
 * variables the server config loaders read, so a key placed in `.env`
 * still reaches the container. This gate extracts the env-variable names
 * from the loader sources (the code is the single source of truth — a
 * second hand-maintained list would drift exactly like the passthrough
 * did), parses each compose service environment keys, and asserts compose
 * coverage ⊇ provider read set.
 *
 * The anchor tripwires below name the complete current read set of each
 * loader: a refactoring that changes how a loader passes variable names
 * (e.g. an options object instead of a bare literal) makes the regex
 * extraction silently under-report, so any missing anchor fails the gate
 * and points at updating compose.yaml together with this gate instead of
 * letting the drift pass quietly (#626 review).
 */

const PROVIDER_CONFIG = "server/src/shared/infrastructure/config/provider_config.ts";
const SERVER_CONFIG = "server/src/shared/infrastructure/config/server_config.ts";
// Both compose files that run the server: the repository root (builds from
// source) and the deploy copy (runs the published image); #631 keeps their
// passthrough blocks isomorphic, and each must cover the provider read set.
const COMPOSE_FILES = ["compose.yaml", "deploy/compose.yaml"];

// Complete current provider read set of provider_config.ts; every entry
// must surface from the extraction or the gate fails loudly.
const PROVIDER_ANCHORS = [
  "LLM_PROVIDER",
  "LLM_MODEL",
  "DASHSCOPE_MODEL",
  "DASHSCOPE_REVIEW_MODEL",
  "OPENAI_COMPATIBLE_MODEL",
  "DASHSCOPE_API_KEY",
  "DASHSCOPE_API_BASE",
  "DASHSCOPE_TRANSPORT_MODE",
  "LLM_API_KEY",
  "OPENAI_API_KEY",
  "LLM_API_BASE",
  "OPENAI_API_BASE",
  "LLM_TIMEOUT",
  "LLM_RETRY_ATTEMPTS",
  "LLM_RETRY_DELAY",
  "LLM_STREAM_FIRST_BYTE_TIMEOUT_MS",
  "LLM_STREAM_IDLE_TIMEOUT_MS",
  "LLM_LOREBOOK_BUDGET_CHARACTERS",
];

// Complete current read set of server_config.ts outside the delegated LLM
// block; same tripwire semantics as PROVIDER_ANCHORS.
const SERVER_ANCHORS = [
  "APP_ENVIRONMENT",
  "DB_URL",
  "SECURITY_SECRET_KEY",
  "API_HOST",
  "API_PORT",
  "SECURITY_CORS_ORIGINS",
  "SECURITY_TRUSTED_PROXIES",
  "SECURITY_RATE_LIMIT",
  "API_MAX_ACTIVE_WORKFLOWS",
  "API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT",
];

// Matches `helper(env, "KEY")` across line breaks — the only shape in which
// the config loaders pass a variable name. Helper definitions (`function
// stringFrom(env: …)`) do not match: their `env` is followed by a type
// annotation, not a comma and a quoted key.
const SINGLE_KEY_CALL = /\w+\(\s*env\s*,\s*"([A-Z][A-Z0-9_]*)"/g;
// Matches alias arrays: `firstNonBlankStringFrom(env, ["LLM_API_KEY", …])`.
const ALIAS_ARRAY_CALL = /\w+\(\s*env\s*,\s*\[([^\]]*)\]/g;
const KEY_LITERAL = /"([A-Z][A-Z0-9_]*)"/g;

/** Every env variable a config loader source names, keyed by literal. */
function extractEnvKeys(root, relativePath) {
  const source = readTextLines(join(root, relativePath)).join("\n");
  const keys = new Set();
  for (const match of source.matchAll(SINGLE_KEY_CALL)) {
    keys.add(match[1]);
  }
  for (const match of source.matchAll(ALIAS_ARRAY_CALL)) {
    for (const literal of match[1].matchAll(KEY_LITERAL)) {
      keys.add(literal[1]);
    }
  }
  return keys;
}

/**
 * Environment keys of every service in a compose file, from the map-style
 * (`KEY: value`) and list-style (`- KEY=value`) entries; comments are
 * skipped, and a sibling key at the block's indent closes the block.
 */
function composeEnvironmentKeys(root, relativePath) {
  const keys = new Set();
  let inServices = false;
  let inEnvironment = false;
  let environmentIndent = 0;
  for (const line of readTextLines(join(root, relativePath))) {
    const content = line.trim();
    if (content === "" || content.startsWith("#")) continue;
    const indent = line.length - line.trimStart().length;
    if (indent === 0) {
      inServices = content === "services:";
      inEnvironment = false;
      continue;
    }
    if (!inServices) continue;
    if (inEnvironment && indent > environmentIndent) {
      const mapKey = content.match(/^([A-Za-z_][A-Za-z0-9_]*):(?:\s|$)/);
      if (mapKey !== null) {
        keys.add(mapKey[1]);
        continue;
      }
      const listKey = content.match(/^-\s*([A-Za-z_][A-Za-z0-9_]*)=/);
      if (listKey !== null) keys.add(listKey[1]);
      continue;
    }
    inEnvironment = content === "environment:";
    environmentIndent = inEnvironment ? indent : 0;
  }
  return keys;
}

const root = repoRoot();
const providerKeys = extractEnvKeys(root, PROVIDER_CONFIG);
const serverKeys = extractEnvKeys(root, SERVER_CONFIG);
const failures = [];

for (const [relativePath, keys, anchors] of [
  [PROVIDER_CONFIG, providerKeys, PROVIDER_ANCHORS],
  [SERVER_CONFIG, serverKeys, SERVER_ANCHORS],
]) {
  if (keys.size === 0) {
    failures.push(`env-key extraction found no variables in ${relativePath}; the gate is blind`);
  }
  for (const anchor of anchors) {
    if (!keys.has(anchor)) {
      failures.push(
        `env-key extraction missed anchor ${anchor} in ${relativePath}; the extraction rotted — ` +
          `update compose.yaml entries and this gate's anchor list together`,
      );
    }
  }
}

for (const composeFile of COMPOSE_FILES) {
  if (!existsSync(join(root, composeFile))) {
    failures.push(
      `required compose file is missing: ${composeFile} — the passthrough contract is ` +
        `fail-closed; restore the file or update COMPOSE_FILES in this gate`,
    );
    continue;
  }
  const composeKeys = composeEnvironmentKeys(root, composeFile);
  if (composeKeys.size === 0) {
    failures.push(
      `${composeFile} exposes no service environment keys; passthrough cannot be verified`,
    );
  }
  for (const key of providerKeys) {
    if (!composeKeys.has(key)) {
      failures.push(
        `${composeFile} environment is missing provider variable ${key} read by provider_config.ts`,
      );
    }
  }
}

if (reportFailures("compose-passthrough", failures)) {
  console.log(
    `[compose-passthrough] clean: all ${providerKeys.size} provider variables read by the config ` +
      `loaders are covered in ${COMPOSE_FILES.join(" and ")} ` +
      `(${serverKeys.size} server-side variables extracted in total)`,
  );
}
