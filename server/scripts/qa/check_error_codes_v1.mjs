/**
 * Lockstep gate for the rebuilt error contract.
 *
 * The legacy gate (`check_error_codes.mjs`) still guards the old three surfaces
 * because the old code is still the one serving requests. This gate guards the
 * new pair: `server/src/contracts/errors.ts` and its agent-facing table
 * `docs/agents/error-codes-v1.md`.
 *
 * It compares four columns — code set, status, retry, remedy — in both
 * directions. The message is deliberately excluded: messages are allowed to
 * change, codes and statuses are not.
 *
 * TS is parsed as text with strict line matching, same precedent as the legacy
 * gate: an unparsable entry fails closed rather than being skipped, because a
 * gate that silently ignores what it cannot read is worse than no gate.
 */

import { createHash } from "node:crypto";
import { join } from "node:path";

import { readTextLines, repoRoot, reportFailures } from "./common.mjs";

const CATALOG_SOURCE = "server/src/contracts/errors.ts";
const CATALOG_DOC = "docs/agents/error-codes-v1.md";

const CATALOG_DECLARATION = "export const ERROR_CATALOG = {";
const CATALOG_END = "} as const satisfies Record<string, ErrorDefinition>;";
const ENTRY_START = /^ {2}([A-Z][A-Z0-9_]*): \{$/;
const ENTRY_END = /^ {2}\},$/;
const STATUS_LINE = /^ {4}status: (\d{3}),$/;
const RETRY_LINE = /^ {4}retry: "([a-z-]+)",$/;
const REMEDY_LINE = /^ {4}remedy: "([a-z-]+)",$/;
const MESSAGE_LINE = /^ {4}defaultMessage: "(.*)",$/;
const FINGERPRINT_DOC = /文案指纹：`([a-f0-9]{12})`/;
const DOC_ROW = /^\| `([A-Z][A-Z0-9_]*)` \| (\d{3}) \| `([a-z-]+)` \| `([a-z-]+)` \|/;

function catalogBlock(lines, failures) {
  const start = lines.indexOf(CATALOG_DECLARATION);
  if (start === -1) {
    failures.push(`${CATALOG_SOURCE} must declare \`${CATALOG_DECLARATION}\``);
    return null;
  }
  const end = lines.indexOf(CATALOG_END, start);
  if (end === -1) {
    failures.push(`${CATALOG_SOURCE} must close ERROR_CATALOG with \`${CATALOG_END}\``);
    return null;
  }
  return lines.slice(start + 1, end);
}

function parseCatalog(lines, failures) {
  const body = catalogBlock(lines, failures);
  if (body === null) return null;
  const entries = new Map();
  for (let index = 0; index < body.length; index += 1) {
    const startMatch = ENTRY_START.exec(body[index]);
    if (startMatch === null) continue;
    const code = startMatch[1];
    const entry = { status: null, retry: null, remedy: null, defaultMessage: null };
    let cursor = index + 1;
    for (; cursor < body.length; cursor += 1) {
      const line = body[cursor];
      if (ENTRY_END.test(line)) break;
      const status = STATUS_LINE.exec(line);
      if (status !== null) entry.status = Number(status[1]);
      const retry = RETRY_LINE.exec(line);
      if (retry !== null) entry.retry = retry[1];
      const remedy = REMEDY_LINE.exec(line);
      if (remedy !== null) entry.remedy = remedy[1];
      const message = MESSAGE_LINE.exec(line);
      if (message !== null) entry.defaultMessage = message[1];
    }
    if (cursor >= body.length) {
      failures.push(`${CATALOG_SOURCE} entry \`${code}\` is not closed with "  },"`);
      continue;
    }
    if (entry.status === null || entry.retry === null || entry.remedy === null) {
      failures.push(
        `${CATALOG_SOURCE} entry \`${code}\` is missing status, retry, or remedy; the gate fails closed`,
      );
      continue;
    }
    if (entries.has(code)) {
      failures.push(`${CATALOG_SOURCE} declares \`${code}\` twice`);
      continue;
    }
    entries.set(code, entry);
    index = cursor;
  }
  if (entries.size === 0) {
    failures.push(`${CATALOG_SOURCE} declares no catalog entries`);
    return null;
  }
  return entries;
}

function parseDoc(lines, failures) {
  const rows = new Map();
  for (const line of lines) {
    const match = DOC_ROW.exec(line);
    if (match === null) continue;
    const code = match[1];
    if (rows.has(code)) {
      failures.push(`${CATALOG_DOC} lists \`${code}\` twice`);
      continue;
    }
    rows.set(code, { status: Number(match[2]), retry: match[3], remedy: match[4] });
  }
  if (rows.size === 0) {
    failures.push(`${CATALOG_DOC} contains no catalog rows; the gate found nothing to check`);
    return null;
  }
  return rows;
}

function compare(catalog, doc) {
  const failures = [];
  for (const [code, entry] of catalog) {
    const row = doc.get(code);
    if (row === undefined) {
      failures.push(`${CATALOG_DOC} is missing \`${code}\``);
      continue;
    }
    if (row.status !== entry.status) {
      failures.push(`${code}: doc says ${row.status}, catalog says ${entry.status}`);
    }
    if (row.retry !== entry.retry) {
      failures.push(`${code}: doc retry "${row.retry}", catalog "${entry.retry}"`);
    }
    if (row.remedy !== entry.remedy) {
      failures.push(`${code}: doc remedy "${row.remedy}", catalog "${entry.remedy}"`);
    }
  }
  for (const code of doc.keys()) {
    if (!catalog.has(code)) {
      failures.push(`${CATALOG_DOC} lists \`${code}\`, which the catalog does not define`);
    }
  }
  return failures;
}

const root = repoRoot();
const failures = [];
const docLines = readTextLines(join(root, CATALOG_DOC));
const sourceLines = readTextLines(join(root, CATALOG_SOURCE));
const catalog = parseCatalog(sourceLines, failures);
const doc = parseDoc(docLines, failures);

if (catalog !== null && doc !== null && failures.length === 0) {
  failures.push(...compare(catalog, doc));
  checkFingerprint(docLines, catalog, failures);
  checkChannelDisjoint(sourceLines, catalog, failures);
  checkRequiredSet(docLines, sourceLines, failures);
}

/**
 * The required-message set, compared in both directions against the union type.
 *
 * A one-way check ("the doc line exists and parses") stays green forever: adding
 * or removing a member changes neither status, retry, remedy, nor defaultMessage,
 * so the four-column comparison and the message fingerprint both stay silent.
 * The source of truth is the type, never the doc — otherwise the check degrades
 * into the doc vouching for itself.
 *
 * Each difference is reported with its direction, because the two fixes are
 * opposite: a missing declaration means "add it to the doc", an extra one means
 * "the type no longer requires it, remove it".
 */
function checkRequiredSet(docLines, sourceLines, failures) {
  const start = sourceLines.findIndex((line) =>
    line.startsWith("export type ErrorCodeRequiringMessage ="),
  );
  if (start === -1) {
    failures.push(`${CATALOG_SOURCE} must declare \`ErrorCodeRequiringMessage\``);
    return;
  }
  const fromType = new Set();
  for (let index = start + 1; index < sourceLines.length; index += 1) {
    const match = /^ {2}\| "([A-Z][A-Z0-9_]*)";?$/.exec(sourceLines[index]);
    if (match !== null) {
      fromType.add(match[1]);
      continue;
    }
    if (sourceLines[index].trim() === "") continue;
    break;
  }
  if (fromType.size === 0) {
    failures.push(`${CATALOG_SOURCE} declares no required-message codes`);
    return;
  }

  const declared = docLines.map((line) => /^必填 message 码（(\d+)）：(.+)$/.exec(line)).find((m) => m !== null);
  if (declared === undefined) {
    failures.push(`${CATALOG_DOC} must declare a "必填 message 码（N）：..." line`);
    return;
  }
  const fromDoc = new Set([...declared[2].matchAll(/`([A-Z][A-Z0-9_]*)`/g)].map((m) => m[1]));
  const declaredCount = Number(declared[1]);
  if (declaredCount !== fromDoc.size) {
    failures.push(
      `${CATALOG_DOC} 声明数量为 ${String(declaredCount)}，实际列出 ${String(fromDoc.size)} 个码`,
    );
  }
  for (const code of fromType) {
    if (!fromDoc.has(code)) {
      failures.push(`${CATALOG_DOC} 漏声明必填码 \`${code}\`（类型要求 message 必填）：需要加进文档`);
    }
  }
  for (const code of fromDoc) {
    if (!fromType.has(code)) {
      failures.push(`${CATALOG_DOC} 多声明 \`${code}\`（类型已不要求必填）：需要从文档删除`);
    }
  }
}

/**
 * Frame codes must never appear in the HTTP catalog. They answer on different
 * channels: an HTTP code implies a status that a committed SSE response cannot
 * send. Overlap means someone promoted a frame code into the envelope, which
 * would force a fabricated status.
 */
function checkChannelDisjoint(sourceLines, catalog, failures) {
  const start = sourceLines.findIndex((line) =>
    line.startsWith("export const FRAME_ERROR_CODES = {"),
  );
  if (start === -1) {
    failures.push(`${CATALOG_SOURCE} must declare \`FRAME_ERROR_CODES\``);
    return;
  }
  const frameKeys = [];
  for (let index = start + 1; index < sourceLines.length; index += 1) {
    const line = sourceLines[index];
    if (line.startsWith("}")) break;
    const match = ENTRY_START.exec(line);
    if (match !== null) frameKeys.push(match[1]);
  }
  if (frameKeys.length === 0) {
    failures.push(`${CATALOG_SOURCE} declares no frame error codes; the gate found nothing to check`);
    return;
  }
  for (const key of frameKeys) {
    if (catalog.has(key)) {
      failures.push(
        `\`${key}\` appears in both ERROR_CATALOG and FRAME_ERROR_CODES: a frame code has no HTTP status to send`,
      );
    }
  }
}

/**
 * Message fingerprint: a change detector, not a copy.
 *
 * Codes, statuses, retry, and remedy are compared value by value above. The
 * default message is not: it is prose, and the doc's §5 paraphrase is expected
 * to track it. A plain-text comparison would force the doc to duplicate every
 * sentence; a fingerprint only says "the corpora diverged, re-read §5".
 *
 * Corpus (must match the doc's stated recipe exactly): 22 entries in catalog
 * declaration order — no sort, because `Object.keys` already yields insertion
 * order and a stray `localeCompare` would reorder non-ASCII keys and produce a
 * false failure — each rendered `CODE|defaultMessage`, joined by "\n", no
 * trailing newline, **no Unicode normalization**, sha256 over UTF-8, first 12
 * hex chars.
 */
function messageFingerprint(entries) {
  const payload = [...entries]
    .map(([code, entry]) => `${code}|${entry.defaultMessage}`)
    .join("\n");
  return createHash("sha256").update(payload, "utf8").digest("hex").slice(0, 12);
}

function checkFingerprint(lines, catalog, failures) {
  const mentions = lines.filter((line) => line.includes("文案指纹"));
  const declared = mentions
    .map((line) => FINGERPRINT_DOC.exec(line))
    .find((match) => match !== null);
  const actual = messageFingerprint(catalog);

  if (mentions.length === 0) {
    console.log(
      `[error-codes-v1] note: 文档未声明文案指纹；当前语料指纹为 ${actual}，写入文档后本项转为强制`,
    );
    return;
  }
  // A mention the pattern cannot read must fail, not fall back to "absent".
  // Otherwise reformatting the line (bolding it, moving it into a list) turns
  // the check into decoration without anyone noticing — the same silent-decay
  // failure this gate exists to prevent.
  if (declared === undefined) {
    failures.push(
      `${CATALOG_DOC} 提到「文案指纹」但没有一行符合 \`文案指纹：\` + 12 位十六进制的格式；门禁拒绝在格式不可读时放行`,
    );
    return;
  }
  const inDoc = declared[1];
  if (inDoc !== actual) {
    failures.push(
      `${CATALOG_DOC} 的文案指纹 ${inDoc} 与契约重算值 ${actual} 不符：只改了 defaultMessage，请重读 §5 的文案对照并更新指纹`,
    );
  }
}

if (reportFailures("error-codes-v1", failures) && catalog !== null) {
  console.log(
    `[error-codes-v1] clean: ${catalog.size} codes match across ${CATALOG_SOURCE} and ${CATALOG_DOC}`,
  );
}
