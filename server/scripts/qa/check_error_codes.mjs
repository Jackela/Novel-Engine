import { join } from "node:path";

import { readTextLines, repoRoot, reportFailures } from "./common.mjs";

/**
 * Lockstep gate for the error-code catalog. docs/agents/error-codes.md is the
 * agent-facing view of ERROR_CODES (server/src/shared/domain/error_codes.ts)
 * and its HTTP status mapping ERROR_HTTP_STATUS
 * (server/src/shared/interface/http/error_envelope.ts). The code side is
 * compile-locked via `satisfies`; the markdown side had no enforcement, so
 * this gate compares all three surfaces for exact set and status equality in
 * both directions. TS sources are parsed as text (same precedent as
 * check_ssot.mjs) with strict line matching: an unparsable entry fails closed,
 * as does a duplicated catalog row.
 */

const CATALOG_DOC = "docs/agents/error-codes.md";
const CODES_SOURCE = "server/src/shared/domain/error_codes.ts";
const STATUS_SOURCE = "server/src/shared/interface/http/error_envelope.ts";

const ERROR_CODES_DECLARATION = "export const ERROR_CODES = {";
const ERROR_STATUS_DECLARATION = "export const ERROR_HTTP_STATUS = {";
const CODE_ENTRY = /^ {2}([A-Z][A-Z0-9_]*): "([A-Z][A-Z0-9_]*)",$/;
const STATUS_ENTRY = /^ {2}([A-Z][A-Z0-9_]*): (\d{3}),$/;
const CATALOG_ROW = /^\| `([A-Z][A-Z0-9_]*)` \| (\d{3}) \|/;

function declarationBlock(lines, declaration, sourcePath, failures) {
  const start = lines.indexOf(declaration);
  if (start === -1) {
    failures.push(`${sourcePath} must declare \`${declaration}\``);
    return null;
  }
  const body = [];
  for (let index = start + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.startsWith("}")) {
      return body;
    }
    body.push(line);
  }
  failures.push(`${sourcePath} must close the \`${declaration}\` block before end of file`);
  return null;
}

function parseCodes(lines, failures) {
  const body = declarationBlock(lines, ERROR_CODES_DECLARATION, CODES_SOURCE, failures);
  if (body === null) {
    return null;
  }
  const codes = new Set();
  for (const line of body) {
    if (line.trim() === "") {
      continue;
    }
    const match = CODE_ENTRY.exec(line);
    if (match === null) {
      failures.push(
        `${CODES_SOURCE} contains an entry inside ERROR_CODES that the lockstep gate cannot parse: "${line.trim()}"`,
      );
      continue;
    }
    codes.add(match[2]);
  }
  if (codes.size === 0) {
    failures.push(`${CODES_SOURCE} declares no codes; the drift gate found nothing to check`);
    return null;
  }
  return codes;
}

function parseStatuses(lines, failures) {
  const body = declarationBlock(lines, ERROR_STATUS_DECLARATION, STATUS_SOURCE, failures);
  if (body === null) {
    return null;
  }
  const statuses = new Map();
  for (const line of body) {
    if (line.trim() === "") {
      continue;
    }
    const match = STATUS_ENTRY.exec(line);
    if (match === null) {
      failures.push(
        `${STATUS_SOURCE} contains an entry inside ERROR_HTTP_STATUS that the lockstep gate cannot parse: "${line.trim()}"`,
      );
      continue;
    }
    statuses.set(match[1], Number(match[2]));
  }
  if (statuses.size === 0) {
    failures.push(
      `${STATUS_SOURCE} declares no HTTP statuses; the drift gate found nothing to check`,
    );
    return null;
  }
  return statuses;
}

function parseCatalog(lines, failures) {
  const catalog = new Map();
  for (const line of lines) {
    const match = CATALOG_ROW.exec(line);
    if (match === null) {
      continue;
    }
    if (catalog.has(match[1])) {
      failures.push(`${CATALOG_DOC} contains a duplicate catalog row for \`${match[1]}\``);
      continue;
    }
    catalog.set(match[1], Number(match[2]));
  }
  if (catalog.size === 0) {
    failures.push(
      `${CATALOG_DOC} contains no catalog table rows; the drift gate found nothing to check`,
    );
    return null;
  }
  return catalog;
}

function comparisonFailures(codes, statuses, catalog) {
  const failures = [];
  for (const code of codes) {
    if (!statuses.has(code)) {
      failures.push(
        `${STATUS_SOURCE} ERROR_HTTP_STATUS has no HTTP status for code \`${code}\` declared by ERROR_CODES`,
      );
      continue;
    }
    if (!catalog.has(code)) {
      failures.push(`${CATALOG_DOC} is missing code \`${code}\` declared by ERROR_CODES`);
      continue;
    }
    if (catalog.get(code) !== statuses.get(code)) {
      failures.push(
        `${CATALOG_DOC} maps \`${code}\` to HTTP ${catalog.get(code)}, but ERROR_HTTP_STATUS declares ${statuses.get(code)}`,
      );
    }
  }
  for (const code of statuses.keys()) {
    if (!codes.has(code)) {
      failures.push(
        `ERROR_HTTP_STATUS declares \`${code}\`, which ERROR_CODES in ${CODES_SOURCE} does not define`,
      );
    }
  }
  for (const code of catalog.keys()) {
    if (!codes.has(code) && !statuses.has(code)) {
      failures.push(
        `${CATALOG_DOC} lists code \`${code}\`, which is absent from both ERROR_CODES and ERROR_HTTP_STATUS`,
      );
    }
  }
  return failures;
}

const root = repoRoot();
const failures = [];
const codes = parseCodes(readTextLines(join(root, CODES_SOURCE)), failures);
const statuses = parseStatuses(readTextLines(join(root, STATUS_SOURCE)), failures);
const catalog = parseCatalog(readTextLines(join(root, CATALOG_DOC)), failures);

if (codes !== null && statuses !== null && catalog !== null && failures.length === 0) {
  failures.push(...comparisonFailures(codes, statuses, catalog));
}

if (reportFailures("error-codes", failures)) {
  console.log(
    `[error-codes] clean: ${codes.size} codes verified in lockstep across ${CATALOG_DOC}, ERROR_CODES, and ERROR_HTTP_STATUS`,
  );
}
