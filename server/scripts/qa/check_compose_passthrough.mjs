import { join } from "node:path";

import { readTextLines, repoRoot, reportFailures } from "./common.mjs";

/**
 * Compose passthrough drift gate (#626): compose.yaml promises that its
 * `environment:` block mirrors every provider variable the server config
 * loaders read, so a key placed in `.env` still reaches the container. This
 * gate extracts the env-variable names from the loader sources (the code is
 * the single source of truth — a second hand-maintained list would drift
 * exactly like the passthrough did), parses the compose service environment
 * keys, and asserts compose coverage ⊇ provider read set. It fails when the
 * extraction rotts (no keys, or an anchor tripwire disappears) or when
 * compose drops a provider variable.
 */

const PROVIDER_CONFIG = "server/src/shared/infrastructure/config/provider_config.ts";
const SERVER_CONFIG = "server/src/shared/infrastructure/config/server_config.ts";
const COMPOSE_FILE = "compose.yaml";

// Parser tripwires: these variables must always surface from the source
// extraction. If one vanishes, the regex extraction rotted (or a loader
// stopped reading real variables) and the gate must fail loudly instead of
// silently passing on a partial set.
const PROVIDER_ANCHORS = ["LLM_PROVIDER", "DASHSCOPE_API_KEY", "OPENAI_API_KEY"];
const SERVER_ANCHORS = ["DB_URL", "APP_ENVIRONMENT", "SECURITY_SECRET_KEY"];

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
 * Environment keys of every service in compose.yaml, from the map-style
 * (`KEY: value`) and list-style (`- KEY=value`) entries; comments are
 * skipped, and a sibling key at the block's indent closes the block.
 */
function composeEnvironmentKeys(root) {
  const keys = new Set();
  let inServices = false;
  let inEnvironment = false;
  let environmentIndent = 0;
  for (const line of readTextLines(join(root, COMPOSE_FILE))) {
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
const composeKeys = composeEnvironmentKeys(root);
const failures = [];

for (const [label, keys, anchors] of [
  ["provider_config.ts", providerKeys, PROVIDER_ANCHORS],
  ["server_config.ts", serverKeys, SERVER_ANCHORS],
]) {
  if (keys.size === 0) {
    failures.push(`env-key extraction found no variables in ${label}; the gate is blind`);
  }
  for (const anchor of anchors) {
    if (!keys.has(anchor)) {
      failures.push(
        `env-key extraction missed anchor ${anchor} in ${label}; the extraction rotted`,
      );
    }
  }
}
if (composeKeys.size === 0) {
  failures.push(
    `${COMPOSE_FILE} exposes no service environment keys; passthrough cannot be verified`,
  );
}
for (const key of providerKeys) {
  if (!composeKeys.has(key)) {
    failures.push(
      `${COMPOSE_FILE} environment is missing provider variable ${key} read by provider_config.ts`,
    );
  }
}

if (reportFailures("compose-passthrough", failures)) {
  console.log(
    `[compose-passthrough] clean: ${COMPOSE_FILE} covers all ${providerKeys.size} provider variables ` +
      `read by the config loaders (${serverKeys.size} server-side variables extracted in total)`,
  );
}
