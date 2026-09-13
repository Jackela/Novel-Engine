import { existsSync } from "node:fs";
import { join } from "node:path";

import { listRepoFiles, readTextLines, repoRoot, reportFailures } from "./common.mjs";

/**
 * Link drift gate for the root llms.txt. Every link must point at
 * https://raw.githubusercontent.com/Jackela/Novel-Engine/main/<path> and the
 * referenced path must exist in the current tracked or untracked candidate,
 * so local validation observes the same files an agent is about to deliver.
 */

const EXPECTED_PREFIX = "https://raw.githubusercontent.com/Jackela/Novel-Engine/main/";
const MARKDOWN_LINK = /\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;

function extractTargets(lines) {
  const targets = [];
  for (const line of lines) {
    for (const match of line.matchAll(MARKDOWN_LINK)) {
      const url = match[1];
      if (!url.startsWith(EXPECTED_PREFIX)) {
        targets.push({ url, path: null });
        continue;
      }
      targets.push({ url, path: url.slice(EXPECTED_PREFIX.length) });
    }
  }
  return targets;
}

function pathExistsInCandidate(root, candidateFiles, relativePath) {
  return candidateFiles.has(relativePath) && existsSync(join(root, relativePath));
}

const root = repoRoot();
const lines = readTextLines(`${root}/llms.txt`);
const targets = extractTargets(lines);
const candidateFiles = new Set(listRepoFiles(root));
const failures = [];

if (targets.length === 0) {
  failures.push("llms.txt contains no markdown links; the drift gate found nothing to check");
}

for (const { url, path } of targets) {
  if (path === null) {
    failures.push(`llms.txt link must start with ${EXPECTED_PREFIX}, got ${url}`);
  } else if (!pathExistsInCandidate(root, candidateFiles, path)) {
    failures.push(
      `llms.txt link target missing from the current candidate: ${url} (path: ${path})`,
    );
  }
}

if (reportFailures("llms-txt", failures)) {
  console.log(
    `[llms-txt] clean: ${targets.length} link targets verified against the current candidate`,
  );
}
